"""Pydantic schemas for API request/response."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Namespace(BaseModel):
    """四级命名空间隔离，支持搜索时的层级继承与通配符.
    
    写入: 必须提供完整3级(client:user:agent)，session可选。
    搜索: 支持*通配符和尾部省略，实现层级继承。
      - hermes:boss:hnoe:s1  → 精确4级
      - hermes:boss:hnoe     → 3级，覆盖所有session
      - hermes:boss:*        → 2级，覆盖boss下所有agent
      - hermes:*             → 1级，覆盖hermes下所有user
      - *                    → 全局搜索(慎用)
      - hermes               → 等同 hermes:*:*
    """
    
    client_id: str = Field(..., description="Client identifier, * for wildcard")
    user_id: str = Field(..., description="User identifier, * for wildcard")
    agent_id: str = Field(..., description="Agent identifier, * for wildcard")
    session_id: Optional[str] = Field(None, description="Session identifier, * for wildcard")
    
    @classmethod
    def from_header(cls, header: str) -> "Namespace":
        """Parse from X-Namespace header: client:user:agent[:session]
        
        Supports wildcard * and trailing omission:
          - "hermes:boss:hnoe:s1"  → (hermes, boss, hnoe, s1)
          - "hermes:boss:hnoe"     → (hermes, boss, hnoe, None)
          - "hermes:boss:*"        → (hermes, boss, *, None)
          - "hermes:*"             → (hermes, *, *, None)
          - "hermes"               → (hermes, *, *, None)
          - "*"                    → (*, *, *, None)
        """
        parts = header.split(":")
        
        if len(parts) == 1:
            # "hermes" or "*" → 1级
            return cls(
                client_id=parts[0],
                user_id="*",
                agent_id="*",
                session_id=None,
            )
        
        if len(parts) == 2:
            # "hermes:*" → 2级
            return cls(
                client_id=parts[0],
                user_id=parts[1],
                agent_id="*",
                session_id=None,
            )
        
        # 3级或4级
        session_id = parts[3] if len(parts) > 3 else None
        return cls(
            client_id=parts[0],
            user_id=parts[1],
            agent_id=parts[2],
            session_id=session_id,
        )
    
    @property
    def is_wildcard_search(self) -> bool:
        """Whether this namespace contains any wildcard."""
        return (
            self.client_id == "*"
            or self.user_id == "*"
            or self.agent_id == "*"
            or self.session_id == "*"
        )
    
    @property
    def is_valid_for_write(self) -> bool:
        """Whether this namespace is valid for write operations (no wildcards)."""
        return (
            self.client_id != "*"
            and self.user_id != "*"
            and self.agent_id != "*"
            and (self.session_id is None or self.session_id != "*")
        )
    
    def to_dict(self) -> dict:
        """Convert to dict for SQLAlchemy filter (only non-wildcard fields)."""
        d = {}
        if self.client_id != "*":
            d["client_id"] = self.client_id
        if self.user_id != "*":
            d["user_id"] = self.user_id
        if self.agent_id != "*":
            d["agent_id"] = self.agent_id
        if self.session_id and self.session_id != "*":
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
    mode: str = Field(default="hybrid", description="Search mode: vector/keyword/hybrid")
    
    # RRF params (mem0-style weighted RRF)
    rrf_k: int = Field(default=60, ge=1, le=200, description="RRF constant k (higher = smoother)")
    vector_weight: float = Field(default=1.0, ge=0.0, le=5.0, description="Weight for vector search")
    keyword_weight: float = Field(default=1.0, ge=0.0, le=5.0, description="Weight for keyword search")


class MemorySearchResult(BaseModel):
    """Search result with similarity score."""
    
    memory: MemoryResponse
    similarity: Optional[float] = Field(None, description="Vector similarity score (0-1)")
    rrf_score: Optional[float] = Field(None, description="RRF fusion score")


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
