"""Memory CRUD operations."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from mnemonic.models import Memory, MemoryAccessLog, Entity
from mnemonic.schemas import MemoryCreate, MemorySearch, MemoryUpdate, Namespace
from mnemonic.services import tokenize_for_search
import hashlib
import json


def _content_to_tsvector(content: str) -> str:
    """Convert content to tsvector using jieba tokens + PG's to_tsvector('simple')."""
    tokens = tokenize_for_search(content)
    if not tokens:
        return None
    return func.to_tsvector('simple', tokens)


class MemoryStore:
    """Memory storage operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        namespace: Namespace,
        data: MemoryCreate,
        embedding: Optional[list[float]] = None,
        entity_service = None,  # Injected by API layer
    ) -> Memory:
        """Create a new memory. Returns existing memory if content hash matches (dedup)."""
        content_hash = hashlib.md5(data.content.encode('utf-8')).hexdigest()
        
        # Hash去重：同命名空间下相同content_hash的记忆直接返回已有记录
        dedup_stmt = select(Memory).where(
            and_(
                Memory.content_hash == content_hash,
                Memory.deleted_at.is_(None),
                *self._namespace_filters(namespace),
            )
        )
        existing = await self.session.execute(dedup_stmt)
        existing_mem = existing.scalar_one_or_none()
        if existing_mem:
            return existing_mem
        
        tokens_str = tokenize_for_search(data.content)
        memory = Memory(
            **namespace.to_dict(),
            content=data.content,
            content_hash=content_hash,
            memory_type=data.memory_type,
            importance=data.importance,
            expires_at=data.expires_at,
            embedding=embedding or data.embedding,
        )
        self.session.add(memory)
        await self.session.flush()
        
        # Update content_tokens via SQL (TSVECTOR type needs PG-side conversion)
        if tokens_str:
            await self.session.execute(
                text("UPDATE memories SET content_tokens = to_tsvector('simple', :tokens) WHERE id = :mid"),
                {"tokens": tokens_str, "mid": memory.id}
            )
            await self.session.flush()
        
        # Extract and store entities
        if entity_service:
            try:
                entities = await entity_service.extract_simple(data.content)
                if entities:
                    from mnemonic.store import EntityStore
                    entity_store = EntityStore(self.session)
                    for ent in entities:
                        await entity_store.upsert_entity(
                            namespace, ent["name"], ent["type"], memory.id
                        )
            except Exception as e:
                # Log but don't fail memory creation
                import logging
                logging.warning(f"Entity extraction failed for memory {memory.id}: {e}")
        
        # Log access
        await self._log_access(memory.id, "write")
        
        return memory
    
    async def get(self, memory_id: UUID, namespace: Namespace) -> Optional[Memory]:
        """Get a memory by ID within namespace."""
        stmt = select(Memory).where(
            and_(
                Memory.id == memory_id,
                Memory.deleted_at.is_(None),
                *self._namespace_filters(namespace),
            )
        )
        result = await self.session.execute(stmt)
        memory = result.scalar_one_or_none()
        
        if memory:
            await self._log_access(memory.id, "read")
        
        return memory
    
    async def list(
        self,
        namespace: Namespace,
        limit: int = 50,
        offset: int = 0,
        memory_type: Optional[str] = None,
        min_importance: Optional[float] = None,
    ) -> tuple[list[Memory], int]:
        """List memories within namespace."""
        filters = [Memory.deleted_at.is_(None), *self._namespace_filters(namespace)]
        
        if memory_type:
            filters.append(Memory.memory_type == memory_type)
        if min_importance is not None:
            filters.append(Memory.importance >= min_importance)
        
        # Count total
        count_stmt = select(func.count()).select_from(Memory).where(and_(*filters))
        total = (await self.session.execute(count_stmt)).scalar()
        
        # Get results
        stmt = (
            select(Memory)
            .where(and_(*filters))
            .order_by(Memory.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        memories = list(result.scalars().all())
        
        return memories, total
    
    async def update(
        self,
        memory_id: UUID,
        namespace: Namespace,
        data: MemoryUpdate,
        embedding: Optional[list[float]] = None,
    ) -> Optional[Memory]:
        """Update a memory."""
        memory = await self.get(memory_id, namespace)
        if not memory:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        # Don't set embedding via ORM setattr — pgvector needs SQL update
        embedding_to_save = embedding
        update_data.pop("embedding", None)
        
        for key, value in update_data.items():
            setattr(memory, key, value)
        
        await self.session.flush()  # Persist scalar changes
        
        # Update embedding via SQL to avoid MissingGreenlet
        if embedding_to_save is not None:
            await self.session.execute(
                text("UPDATE memories SET embedding = :emb WHERE id = :mid"),
                {"emb": str(embedding_to_save), "mid": memory_id}
            )
            await self.session.flush()
            # Refresh to pick up the new embedding
            await self.session.refresh(memory)
        
        # Also update content_tokens if content changed
        if "content" in update_data:
            tokens_str = tokenize_for_search(update_data["content"])
            if tokens_str:
                await self.session.execute(
                    text("UPDATE memories SET content_tokens = to_tsvector('simple', :tokens) WHERE id = :mid"),
                    {"tokens": tokens_str, "mid": memory_id}
                )
                await self.session.flush()
        
        await self._log_access(memory_id, "write")
        return memory
    
    async def delete(self, memory_id: UUID, namespace: Namespace) -> bool:
        """Soft delete a memory."""
        memory = await self.get(memory_id, namespace)
        if not memory:
            return False
        
        memory.deleted_at = datetime.utcnow()
        await self._log_access(memory_id, "delete")
        return True
    
    async def search_vector(
        self,
        namespace: Namespace,
        query_embedding: list[float],
        limit: int = 10,
        min_similarity: float = 0.0,
        min_importance: float = 0.0,
    ) -> list[tuple[Memory, float]]:
        """Vector similarity search using pgvector."""
        filters = [
            Memory.deleted_at.is_(None),
            Memory.embedding.isnot(None),
            *self._namespace_filters(namespace),
        ]
        if min_importance > 0:
            filters.append(Memory.importance >= min_importance)
        
        # Cosine similarity: 1 - (embedding <=> query)
        stmt = (
            select(
                Memory,
                (1 - Memory.embedding.cosine_distance(query_embedding)).label("similarity"),
            )
            .where(and_(*filters))
            .order_by(Memory.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        rows = result.all()
        
        # Filter by min_similarity
        filtered = [(row[0], row[1]) for row in rows if row[1] >= min_similarity]
        
        # Update access count and calculate dynamic importance
        from mnemonic.temporal_decay import calculate_temporal_importance
        from datetime import datetime, timezone
        
        for memory, similarity in filtered:
            # Increment access count
            memory.access_count += 1
            memory.last_accessed_at = datetime.now(timezone.utc)
            
            # Calculate dynamic importance
            dynamic_importance = calculate_temporal_importance(
                initial_importance=memory.initial_importance,
                memory_type=memory.memory_type,
                created_at=memory.created_at,
                access_count=memory.access_count,
            )
            memory.importance = dynamic_importance
            
            await self._log_access(memory.id, "read")
        
        await self.session.flush()
        
        return filtered
    
    async def search_bm25(
        self,
        namespace: Namespace,
        query: str,
        limit: int = 10,
        min_importance: float = 0.0,
    ) -> list[tuple[Memory, float]]:
        """Keyword search using jieba tokenization + PG tsvector/tsquery.
        
        Python-side jieba segmentation feeds into PG's 'simple' text search
        configuration. GIN index on content_tokens column provides fast lookup.
        Score is ts_rank for relevancy ordering.
        """
        # Tokenize query with jieba
        query_tokens = tokenize_for_search(query)
        if not query_tokens:
            return []
        
        # Build tsquery: OR of all tokens for broad recall (will be reranked by BM25 + Entity Boost)
        tsquery_str = " | ".join(query_tokens.split())  # | = OR in tsquery
        
        # Build namespace filters dynamically (wildcard support)
        ns_conditions = ["m.deleted_at IS NULL"]
        params = {
            "tsq": tsquery_str,
            "lim": limit,
        }
        if min_importance > 0:
            ns_conditions.append("m.importance >= :min_imp")
            params["min_imp"] = min_importance
        if namespace.client_id != "*":
            ns_conditions.append("m.client_id = :cid")
            params["cid"] = namespace.client_id
        if namespace.user_id != "*":
            ns_conditions.append("m.user_id = :uid")
            params["uid"] = namespace.user_id
        if namespace.agent_id != "*":
            ns_conditions.append("m.agent_id = :aid")
            params["aid"] = namespace.agent_id
        if namespace.session_id and namespace.session_id != "*":
            ns_conditions.append("m.session_id = :sid")
            params["sid"] = namespace.session_id
        
        ns_where = " AND ".join(ns_conditions)
        
        sql = text(f"""
            SELECT m.id, ts_rank(m.content_tokens, to_tsquery('simple', :tsq)) AS rank_score
            FROM memories m
            WHERE {ns_where}
              AND m.content_tokens @@ to_tsquery('simple', :tsq)
            ORDER BY rank_score DESC
            LIMIT :lim
        """)
        
        result = await self.session.execute(sql, params)
        rows = result.fetchall()
        
        if not rows:
            return []
        
        mem_ids = [row[0] for row in rows]
        score_map = {row[0]: float(row[1]) for row in rows}
        
        stmt = select(Memory).where(Memory.id.in_(mem_ids))
        mem_result = await self.session.execute(stmt)
        mem_map = {m.id: m for m in mem_result.scalars().all()}
        
        memories = []
        for mid in mem_ids:
            if mid in mem_map:
                memories.append((mem_map[mid], score_map[mid]))
        
        # Update access count and calculate dynamic importance
        from mnemonic.temporal_decay import calculate_temporal_importance
        from datetime import datetime, timezone
        
        for mem, score in memories:
            # Increment access count
            mem.access_count += 1
            mem.last_accessed_at = datetime.now(timezone.utc)
            
            # Calculate dynamic importance
            dynamic_importance = calculate_temporal_importance(
                initial_importance=mem.initial_importance,
                memory_type=mem.memory_type,
                created_at=mem.created_at,
                access_count=mem.access_count,
            )
            mem.importance = dynamic_importance
            
            await self._log_access(mem.id, "read")
        
        await self.session.flush()
        
        return memories
    
    async def search_hybrid(
        self,
        namespace: Namespace,
        query: str,
        query_embedding: list[float],
        limit: int = 10,
        rrf_k: int = 60,
        vector_weight: float = 1.0,
        keyword_weight: float = 1.0,
        entity_boost_weight: float = 1.0,
        entity_boost_map: dict[str, float] | None = None,
        min_importance: float = 0.0,
    ) -> list[tuple[Memory, float, float]]:
        """Hybrid search: weighted RRF fusion of vector + keyword + entity boost.
        
        Based on mem0's weighted RRF approach:
        - vector_weight / keyword_weight control relative importance
        - entity_boost_weight controls how much entity matches boost scores
        - rrf_k controls rank sensitivity (lower = more sensitive to top ranks)
        - Fetch 5x candidates for better fusion quality
        """
        # Fetch more candidates for better fusion quality
        fetch_limit = min(limit * 5, 100)
        
        vector_results = await self.search_vector(
            namespace, query_embedding, limit=fetch_limit, min_importance=min_importance
        )
        bm25_results = await self.search_bm25(
            namespace, query, limit=fetch_limit, min_importance=min_importance
        )
        
        # Build rank maps
        vector_ranks = {}  # id -> rank (0-based)
        vector_sims = {}   # id -> similarity
        
        for rank, (mem, sim) in enumerate(vector_results):
            vector_ranks[mem.id] = rank
            vector_sims[mem.id] = sim
        
        bm25_ranks = {}
        for rank, (mem, score) in enumerate(bm25_results):
            bm25_ranks[mem.id] = rank
        
        # Union of all candidate IDs
        all_ids = set(vector_ranks.keys()) | set(bm25_ranks.keys())
        
        if not all_ids:
            return []
        
        # Calculate weighted RRF scores + Entity Boost
        rrf_scores = {}
        for mid in all_ids:
            score = 0.0
            if mid in vector_ranks:
                score += vector_weight / (rrf_k + vector_ranks[mid] + 1)
            if mid in bm25_ranks:
                score += keyword_weight / (rrf_k + bm25_ranks[mid] + 1)
            
            # Entity boost
            if entity_boost_map and str(mid) in entity_boost_map:
                score += entity_boost_weight * entity_boost_map[str(mid)]
            
            rrf_scores[mid] = score
        
        # Sort by RRF score descending
        sorted_ids = sorted(all_ids, key=lambda x: -rrf_scores[x])[:limit]
        
        # Batch fetch Memory objects
        stmt = select(Memory).where(Memory.id.in_(sorted_ids))
        result = await self.session.execute(stmt)
        mem_map = {m.id: m for m in result.scalars().all()}
        
        results = []
        for mid in sorted_ids:
            if mid in mem_map:
                results.append((
                    mem_map[mid],
                    vector_sims.get(mid, 0.0),
                    rrf_scores[mid],
                ))
        
        return results
    
    async def find_similar(
        self,
        namespace: Namespace,
        embedding: list[float],
        threshold: float = 0.7,
    ) -> Optional[Memory]:
        """Find most similar memory above threshold (for conflict detection)."""
        results = await self.search_vector(namespace, embedding, limit=1, min_similarity=threshold)
        return results[0][0] if results else None
    
    def _namespace_filters(self, namespace: Namespace) -> list:
        """Generate namespace filter conditions with wildcard support.
        
        * on any level means "don't filter by this level".
        This enables hierarchical search:
          hermes:boss:hnoe  → filter client+user+agent, cover all sessions
          hermes:boss:*     → filter client+user only, cover all agents
          hermes:*          → filter client only, cover all users
          *                 → no filter at all (global search)
        """
        filters = []
        if namespace.client_id != "*":
            filters.append(Memory.client_id == namespace.client_id)
        if namespace.user_id != "*":
            filters.append(Memory.user_id == namespace.user_id)
        if namespace.agent_id != "*":
            filters.append(Memory.agent_id == namespace.agent_id)
        if namespace.session_id and namespace.session_id != "*":
            filters.append(Memory.session_id == namespace.session_id)
        return filters
    
    async def _log_access(
        self,
        memory_id: UUID,
        access_type: str,
        query_text: Optional[str] = None,
        similarity_score: Optional[float] = None,
    ) -> None:
        """Log memory access for WRRF weight calculation."""
        log = MemoryAccessLog(
            memory_id=memory_id,
            access_type=access_type,
            query_text=query_text,
            similarity_score=similarity_score,
        )
        self.session.add(log)


class EntityStore:
    """Entity storage and boosting operations (mem0-style)."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def upsert_entity(
        self,
        namespace: Namespace,
        name: str,
        entity_type: str,
        memory_id: UUID,
    ) -> Entity:
        """Create or update an entity, linking it to a memory."""
        # Find existing entity by name+type in namespace
        stmt = select(Entity).where(
            and_(
                Entity.name == name,
                Entity.entity_type == entity_type,
                Entity.client_id == namespace.client_id,
                Entity.user_id == namespace.user_id,
                Entity.agent_id == namespace.agent_id,
            )
        )
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()
        
        if entity:
            # Add memory_id to linked_memory_ids if not already there
            linked = json.loads(entity.linked_memory_ids)
            mid_str = str(memory_id)
            if mid_str not in linked:
                linked.append(mid_str)
                entity.linked_memory_ids = json.dumps(linked)
                await self.session.flush()
            return entity
        else:
            entity = Entity(
                client_id=namespace.client_id,
                user_id=namespace.user_id,
                agent_id=namespace.agent_id,
                name=name,
                entity_type=entity_type,
                linked_memory_ids=json.dumps([str(memory_id)]),
            )
            self.session.add(entity)
            await self.session.flush()
            return entity
    
    async def get_boost_memory_ids(
        self,
        namespace: Namespace,
        query_entities: list[dict],
    ) -> dict[str, float]:
        """Get memory IDs boosted by query entities.
        
        Returns: {memory_id_str: boost_score}
        """
        if not query_entities:
            return {}
        
        # Collect all entity names from query
        entity_names = [e["name"] for e in query_entities]
        
        # Build namespace filters
        conditions = [Entity.name.in_(entity_names)]
        if namespace.client_id != "*":
            conditions.append(Entity.client_id == namespace.client_id)
        if namespace.user_id != "*":
            conditions.append(Entity.user_id == namespace.user_id)
        if namespace.agent_id != "*":
            conditions.append(Entity.agent_id == namespace.agent_id)
        
        stmt = select(Entity).where(and_(*conditions))
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        
        # Build boost map: memory_id -> number of entity hits
        boost_map: dict[str, float] = {}
        for entity in entities:
            linked = json.loads(entity.linked_memory_ids)
            for mid in linked:
                boost_map[mid] = boost_map.get(mid, 0) + 1.0
        
        return boost_map
