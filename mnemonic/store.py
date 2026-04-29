"""Memory CRUD operations."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemonic.models import Memory, MemoryAccessLog
from mnemonic.schemas import MemoryCreate, MemorySearch, MemoryUpdate, Namespace


class MemoryStore:
    """Memory storage operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        namespace: Namespace,
        data: MemoryCreate,
        embedding: Optional[list[float]] = None,
    ) -> Memory:
        """Create a new memory."""
        memory = Memory(
            **namespace.to_dict(),
            content=data.content,
            memory_type=data.memory_type,
            importance=data.importance,
            expires_at=data.expires_at,
            embedding=embedding or data.embedding,
        )
        self.session.add(memory)
        await self.session.flush()
        
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
        if embedding is not None:
            update_data["embedding"] = embedding
        
        for key, value in update_data.items():
            setattr(memory, key, value)
        
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
    ) -> list[tuple[Memory, float]]:
        """Vector similarity search using pgvector."""
        # Cosine similarity: 1 - (embedding <=> query)
        stmt = (
            select(
                Memory,
                (1 - Memory.embedding.cosine_distance(query_embedding)).label("similarity"),
            )
            .where(
                and_(
                    Memory.deleted_at.is_(None),
                    Memory.embedding.isnot(None),
                    *self._namespace_filters(namespace),
                )
            )
            .order_by(Memory.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        rows = result.all()
        
        # Filter by min_similarity
        filtered = [(row[0], row[1]) for row in rows if row[1] >= min_similarity]
        
        # Log access for returned memories
        for memory, _ in filtered:
            await self._log_access(memory.id, "read")
        
        return filtered
    
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
        """Generate namespace filter conditions."""
        filters = [
            Memory.client_id == namespace.client_id,
            Memory.user_id == namespace.user_id,
            Memory.agent_id == namespace.agent_id,
        ]
        if namespace.session_id:
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
