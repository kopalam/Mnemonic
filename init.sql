-- Mnemonic Schema v0.1
-- Phase 1: Core Tables + pgvector

-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable uuid-ossp for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 记忆表
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 四级命名空间隔离
    client_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255),
    
    -- 记忆内容
    content TEXT NOT NULL,
    
    -- 元数据
    memory_type VARCHAR(50) DEFAULT 'fact',  -- fact/preference/rule/context
    importance FLOAT DEFAULT 0.5,
    
    -- 向量嵌入 (4096 for Qwen3-Embedding-8B)
    embedding vector(4096),
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    
    -- 软删除
    deleted_at TIMESTAMPTZ
);

-- 命名空间索引 (复合索引)
CREATE INDEX idx_memories_namespace ON memories(client_id, user_id, agent_id, session_id) 
    WHERE deleted_at IS NULL;

-- 时间索引 (时序衰减查询)
CREATE INDEX idx_memories_created ON memories(created_at DESC) 
    WHERE deleted_at IS NULL;

-- 类型索引
CREATE INDEX idx_memories_type ON memories(memory_type) 
    WHERE deleted_at IS NULL;

-- 向量索引 (exact search for dim>2000, add HNSW after partial embedding projection in Phase 2)
-- CREATE INDEX idx_memories_embedding ON memories 
--     USING hnsw (embedding vector_cosine_ops)
--     WITH (m = 16, ef_construction = 64);

-- 记忆访问日志 (Phase 2: WRRF权重计算)
CREATE TABLE memory_access_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    
    access_type VARCHAR(20) NOT NULL,  -- read/write/delete
    accessed_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 查询上下文 (用于权重优化)
    query_text TEXT,
    similarity_score FLOAT
);

CREATE INDEX idx_access_logs_memory ON memory_access_logs(memory_id, accessed_at DESC);

-- 更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_memories_updated
    BEFORE UPDATE ON memories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- 查询统计视图 (Phase 2: 自适应权重)
CREATE VIEW memory_stats AS
SELECT 
    m.id,
    m.client_id,
    m.user_id,
    m.agent_id,
    m.memory_type,
    m.importance,
    COUNT(l.id) AS access_count,
    MAX(l.accessed_at) AS last_accessed,
    m.created_at
FROM memories m
LEFT JOIN memory_access_logs l ON m.id = l.memory_id
WHERE m.deleted_at IS NULL
GROUP BY m.id;
