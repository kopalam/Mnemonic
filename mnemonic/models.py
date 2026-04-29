"""Database models and connection management."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Memory(Base):
    """Memory storage model with vector embedding."""
    
    __tablename__ = "memories"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # 四级命名空间隔离
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False)
    session_id: Mapped[Optional[str]] = mapped_column(String(255))
    
    # 记忆内容
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 元数据
    memory_type: Mapped[str] = mapped_column(String(50), default="fact")
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    
    # 向量嵌入 (4096 for Qwen3-Embedding-8B)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(4096))
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # 软删除
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    access_logs: Mapped[list["MemoryAccessLog"]] = relationship(back_populates="memory", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_memories_namespace", "client_id", "user_id", "agent_id", "session_id", postgresql_where=deleted_at.is_(None)),
        Index("idx_memories_created", created_at.desc(), postgresql_where=deleted_at.is_(None)),
    )
    
    def __repr__(self) -> str:
        return f"<Memory {self.id}: {self.content[:50]}...>"


class MemoryAccessLog(Base):
    """Memory access log for WRRF weight calculation."""
    
    __tablename__ = "memory_access_logs"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    memory_id: Mapped[UUID] = mapped_column(ForeignKey("memories.id", ondelete="CASCADE"), nullable=False)
    
    access_type: Mapped[str] = mapped_column(String(20), nullable=False)  # read/write/delete
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # 查询上下文
    query_text: Mapped[Optional[str]] = mapped_column(Text)
    similarity_score: Mapped[Optional[float]] = mapped_column(Float)
    
    # Relationship
    memory: Mapped["Memory"] = relationship(back_populates="access_logs")
    
    __table_args__ = (
        Index("idx_access_logs_memory", "memory_id", accessed_at.desc()),
    )
