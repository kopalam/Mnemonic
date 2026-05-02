"""FastAPI application for Mnemonic."""

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from mnemonic.config import config
from mnemonic.database import close_db, init_db
from mnemonic.schemas import (
    ExtractRequest,
    HealthResponse,
    MemoryCreate,
    MemoryListResponse,
    MemoryResponse,
    MemorySearch,
    MemorySearchResult,
    MemoryUpdate,
    Namespace,
)
from mnemonic.services import embedding_service, extraction_service, entity_service
from mnemonic.store import MemoryStore, EntityStore
from mnemonic.database import get_session
from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: init DB on startup, close on shutdown."""
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="Mnemonic",
    description="AI Agent Persistent Memory System",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependencies
def parse_namespace(x_namespace: Annotated[str, Header()]) -> Namespace:
    """Parse namespace from header."""
    try:
        return Namespace.from_header(x_namespace)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def get_store(session: AsyncSession = Depends(get_session)) -> MemoryStore:
    """Get memory store instance."""
    return MemoryStore(session)


# Routes
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.post("/memories", response_model=MemoryResponse, status_code=201)
async def create_memory(
    data: MemoryCreate,
    namespace: Namespace = Depends(parse_namespace),
    store: MemoryStore = Depends(get_store),
):
    """Create a new memory."""
    if not namespace.is_valid_for_write:
        raise HTTPException(
            status_code=400,
            detail=f"Wildcard namespace not allowed for write: {namespace.client_id}:{namespace.user_id}:{namespace.agent_id}"
        )
    # Generate embedding if not provided
    embedding = None
    if data.embedding is None:
        embedding = await embedding_service.embed(data.content)
    
    # Create memory with entity extraction
    memory = await store.create(namespace, data, embedding, entity_service=entity_service)
    return MemoryResponse.model_validate(memory)


@app.get("/memories", response_model=MemoryListResponse)
async def list_memories(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    memory_type: str | None = Query(None),
    min_importance: float | None = Query(None),
    namespace: Namespace = Depends(parse_namespace),
    store: MemoryStore = Depends(get_store),
):
    """List memories within namespace."""
    memories, total = await store.list(
        namespace,
        limit=limit,
        offset=offset,
        memory_type=memory_type,
        min_importance=min_importance,
    )
    return MemoryListResponse(
        memories=[MemoryResponse.model_validate(m) for m in memories],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/memories/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: str,
    namespace: Namespace = Depends(parse_namespace),
    store: MemoryStore = Depends(get_store),
):
    """Get a specific memory by ID."""
    from uuid import UUID
    
    try:
        mid = UUID(memory_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid memory ID")
    
    memory = await store.get(mid, namespace)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    return MemoryResponse.model_validate(memory)


@app.patch("/memories/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: str,
    data: MemoryUpdate,
    namespace: Namespace = Depends(parse_namespace),
    store: MemoryStore = Depends(get_store),
):
    """Update a memory."""
    if not namespace.is_valid_for_write:
        raise HTTPException(status_code=400, detail="Wildcard namespace not allowed for write")
    from uuid import UUID
    
    try:
        mid = UUID(memory_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid memory ID")
    
    # Re-embed if content changed
    embedding = None
    if data.content is not None:
        embedding = await embedding_service.embed(data.content)
    
    memory = await store.update(mid, namespace, data, embedding)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    return MemoryResponse.model_validate(memory)


@app.delete("/memories/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: str,
    namespace: Namespace = Depends(parse_namespace),
    store: MemoryStore = Depends(get_store),
):
    """Soft delete a memory."""
    if not namespace.is_valid_for_write:
        raise HTTPException(status_code=400, detail="Wildcard namespace not allowed for write")
    from uuid import UUID
    
    try:
        mid = UUID(memory_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid memory ID")
    
    deleted = await store.delete(mid, namespace)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")


@app.post("/memories/search", response_model=list[MemorySearchResult])
async def search_memories(
    data: MemorySearch,
    namespace: Namespace = Depends(parse_namespace),
    store: MemoryStore = Depends(get_store),
):
    """Search memories: vector / keyword / hybrid (default) with Entity Boost."""
    # Generate query embedding
    query_embedding = await embedding_service.embed(data.query)
    
    # Extract entities from query for Entity Boost (simple mode)
    query_entities = await entity_service.extract_simple(data.query)
    entity_store = EntityStore(store.session)
    entity_boost_map = await entity_store.get_boost_memory_ids(namespace, query_entities)
    
    if data.mode == "vector":
        results = await store.search_vector(
            namespace,
            query_embedding,
            limit=data.limit,
            min_importance=data.min_importance or 0.0,
        )
        return [
            MemorySearchResult(
                memory=MemoryResponse.model_validate(memory),
                similarity=similarity,
                rrf_score=None,
            )
            for memory, similarity in results
        ]
    
    elif data.mode == "keyword":
        # Use hybrid with vector_weight=0 to get Entity Boost support
        results = await store.search_hybrid(
            namespace,
            data.query,
            query_embedding,
            limit=data.limit,
            vector_weight=0.0,  # Disable vector search
            keyword_weight=1.0,
            entity_boost_map=entity_boost_map,
            min_importance=data.min_importance or 0.0,
        )
        return [
            MemorySearchResult(
                memory=MemoryResponse.model_validate(memory),
                similarity=similarity,
                rrf_score=rrf_score,
            )
            for memory, similarity, rrf_score in results
        ]
    
    else:  # hybrid (default)
        results = await store.search_hybrid(
            namespace,
            data.query,
            query_embedding,
            limit=data.limit,
            rrf_k=data.rrf_k,
            vector_weight=data.vector_weight,
            keyword_weight=data.keyword_weight,
            entity_boost_map=entity_boost_map,
            min_importance=data.min_importance or 0.0,
        )
        return [
            MemorySearchResult(
                memory=MemoryResponse.model_validate(memory),
                similarity=similarity,
                rrf_score=rrf_score,
            )
            for memory, similarity, rrf_score in results
        ]


@app.post("/memories/extract", response_model=list[MemoryResponse], status_code=201)
async def extract_and_store(
    request: ExtractRequest,
    namespace: Namespace = Depends(parse_namespace),
    store: MemoryStore = Depends(get_store),
):
    """Extract memories from conversation using mem0-style ADD/UPDATE/DELETE/NONE."""
    if not namespace.is_valid_for_write:
        raise HTTPException(status_code=400, detail="Wildcard namespace not allowed for write")
    
    # Phase 1: Extract raw facts from conversation
    extracted = await extraction_service.extract(request.conversation)
    
    if not extracted:
        return []
    
    # Collect extracted fact texts
    new_facts = [item.get("content", "") for item in extracted if item.get("content")]
    if not new_facts:
        return []
    
    # Phase 2: Fetch existing memories for conflict resolution
    existing_memories_raw = await store.list(namespace, limit=50)
    existing_memories = [
        {"id": str(m.id), "text": m.content}
        for m in existing_memories_raw[0]
    ]
    
    # Phase 3: LLM decides ADD/UPDATE/DELETE/NONE for each fact
    decisions = await extraction_service.decide_memory_action(existing_memories, new_facts)
    
    # Phase 4: Entity extraction from the original conversation (simple/regex mode)
    conv_entities = await entity_service.extract_simple(request.conversation)
    
    entity_store = EntityStore(store.session)
    
    results = []
    for decision in decisions:
        event = decision.get("event", "ADD").upper()
        fact_text = decision.get("text", "")
        memory_id = decision.get("id")
        
        if event == "NONE" or not fact_text:
            continue
        
        embedding = await embedding_service.embed(fact_text)
        
        if event == "ADD":
            create_data = MemoryCreate(
                content=fact_text,
                memory_type="fact",
                importance=0.5,
            )
            memory = await store.create(namespace, create_data, embedding)
            results.append(memory)
            
            # Link entities to this memory
            for ent in conv_entities:
                try:
                    await entity_store.upsert_entity(
                        namespace, ent["name"], ent.get("type", "UNKNOWN"), memory.id
                    )
                except Exception as e:
                    import logging
                    logging.getLogger("mnemonic").warning(f"Entity upsert failed: {e}")
        
        elif event == "UPDATE" and memory_id:
            from uuid import UUID
            try:
                mid = UUID(memory_id)
                update_data = MemoryUpdate(content=fact_text)
                updated = await store.update(mid, namespace, update_data, embedding)
                if updated:
                    results.append(updated)
            except (ValueError, Exception) as e:
                import logging
                logging.getLogger("mnemonic").warning(f"Memory update failed for {memory_id}: {e}, creating new")
                create_data = MemoryCreate(content=fact_text, memory_type="fact", importance=0.5)
                memory = await store.create(namespace, create_data, embedding)
                results.append(memory)
        
        elif event == "DELETE" and memory_id:
            from uuid import UUID
            try:
                mid = UUID(memory_id)
                await store.delete(mid, namespace)
                import logging
                logging.getLogger("mnemonic").info(f"Deleted memory {memory_id} per LLM decision")
            except (ValueError, Exception) as e:
                import logging
                logging.getLogger("mnemonic").warning(f"Memory delete failed for {memory_id}: {e}")
    
    return [MemoryResponse.model_validate(m) for m in results]
