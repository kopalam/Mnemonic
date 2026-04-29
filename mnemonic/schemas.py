"""Pydantic schemas for API request/response."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Namespace(BaseModel):
    """四级命名空间隔离."""
    
    client_id: str = Field(..., description="Client identifier")
    user_id: str = Field(..., description="User identifier")
    agent_id: str = Field(..., description="Agent identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    
    @classmethod
    def from_header(cls, header: str) -> "Namespace":
        """Parse from X-Namespace header: client:user:agent:session"""
        parts = header.split(":")
        if len(parts) < 3:
            raise ValueError("Invalid namespace format. Expected: client:user:agent[:session]")
        
        return cls(
            client_id=parts[0],
            user_id=parts[1],
            agent_id=parts[2],
            session_id=parts[3] if len(parts) > 3 else None,
        )
    
    def to_dict(self) -> dict:
        """Convert to dict for SQLAlchemy filter."""
        d = {
            "client_id": self.client_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
        }
        if self.session_id:
            d["session_id"] = self.session_id
        return d


class MemoryCreate(BaseModel):
    """Request body for creating a memory."""
    
    content: str = Field(..., min_length=1, max_length=10000, description="Memory content")
    memory_type: str = Field(default="fact", description="Memory type: fact/preference/rule/context")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="Importance score")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    
    # Optional: pre-computed embedding
    embedding: Optional[list[float]] = Field(None, description="Pre-computed embedding vector")


class MemoryUpdate(BaseModel):
    """Request body for updating a memory."""
    
    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    memory_type: Optional[str] = Field(None)
    importance: Optional[float] = Field(None, ge=0.0, le=1.0)
    expires_at: Optional[datetime] = Field(None)


class MemoryResponse(BaseModel):
    """Response model for a single memory."""
    
    id: UUID
    content: str
    memory_type: str
    importance: float
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    
    # Namespace info
    client_id: str
    user_id: str
    agent_id: str
    session_id: Optional[str] = None
    
    class Config:
        from_attributes = True


class MemorySearch(BaseModel):
    """Request body for searching memories."""
    
    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(default=10, ge=1, le=100, description="Max results")
    memory_type: Optional[str] = Field(None, description="Filter by type")
    min_importance: Optional[float] = Field(None, ge=0.0, le=1.0, description="Min importance")
    
    # Search mode
    use_vector: bool = Field(default=True, description="Use vector similarity")
    use_keyword: bool = Field(default=False, description="Use keyword matching (Phase 2)")


class MemorySearchResult(BaseModel):
    """Search result with similarity score."""
    
    memory: MemoryResponse
    similarity: Optional[float] = Field(None, description="Similarity score (0-1)")


class MemoryListResponse(BaseModel):
    """Response for listing memories."""
    
    memories: list[MemoryResponse]
    total: int
    limit: int
    offset: int


class ExtractRequest(BaseModel):
    """Request body for memory extraction."""
    
    conversation: str = Field(..., min_length=1, description="Conversation text to extract memories from")
    auto_store: bool = Field(default=True, description="Automatically store extracted memories")


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = "ok"
    version: str = "0.1.0"
    database: str = "connected"
