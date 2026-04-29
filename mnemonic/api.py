"""FastAPI application for Mnemonic."""

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from mnemonic.config import config
from mnemonic.database import close_db, init_db
from mnemonic.schemas import (
    HealthResponse,
    MemoryCreate,
    MemoryListResponse,
    MemoryResponse,
    MemorySearch,
    MemorySearchResult,
    MemoryUpdate,
    Namespace,
)
from mnemonic.services import embedding_service, extraction_service
from mnemonic.store import MemoryStore
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
    # Generate embedding if not provided
    embedding = None
    if data.embedding is None:
        embedding = await embedding_service.embed(data.content)
    
    memory = await store.create(namespace, data, embedding)
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
    """Search memories by vector similarity."""
    # Generate query embedding
    query_embedding = await embedding_service.embed(data.query)
    
    # Vector search
    results = await store.search_vector(
        namespace,
        query_embedding,
        limit=data.limit,
    )
    
    return [
        MemorySearchResult(
            memory=MemoryResponse.model_validate(memory),
            similarity=similarity,
        )
        for memory, similarity in results
    ]


@app.post("/memories/extract", response_model=list[MemoryResponse], status_code=201)
async def extract_and_store(
    conversation: str,
    namespace: Namespace = Depends(parse_namespace),
    store: MemoryStore = Depends(get_store),
):
    """Extract memories from conversation and store them."""
    # Extract facts using LLM
    extracted = await extraction_service.extract(conversation)
    
    if not extracted:
        return []
    
    memories = []
    for item in extracted:
        # Generate embedding
        embedding = await embedding_service.embed(item["content"])
        
        # Check for conflicts (Phase 1: simple vector similarity)
        existing = await store.find_similar(namespace, embedding, threshold=0.7)
        
        if existing:
            # Check with LLM if truly conflicting
            is_conflict = await extraction_service.check_conflict(
                existing.content, item["content"]
            )
            if is_conflict:
                # Update existing memory
                update_data = MemoryUpdate(
                    content=item["content"],
                    importance=item.get("importance", existing.importance),
                )
                updated = await store.update(existing.id, namespace, update_data, embedding)
                if updated:
                    memories.append(updated)
                continue
        
        # Create new memory
        create_data = MemoryCreate(
            content=item["content"],
            memory_type=item.get("type", "fact"),
            importance=item.get("importance", 0.5),
        )
        memory = await store.create(namespace, create_data, embedding)
        memories.append(memory)
    
    return [MemoryResponse.model_validate(m) for m in memories]
