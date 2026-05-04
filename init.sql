-- Mnemonic Schema v0.2
-- Auto-initialized by SQLAlchemy, this file is for reference only

-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable uuid-ossp for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 记忆表
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 四级命名空间隔离
    client_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255),
    
    -- 记忆内容
    content TEXT NOT NULL,
    content_hash VARCHAR(32) NOT NULL,  -- MD5去重
    
    -- 元数据
    memory_type VARCHAR(50) DEFAULT 'fact',
    importance FLOAT DEFAULT 0.5,
    
    -- 向量嵌入 (1024 for Qwen3-Embedding-0.6B)
    embedding vector(1024),
    
    -- jieba中文分词tokens (用于关键词搜索)
    content_tokens TSVECTOR,
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    
    -- 软删除
    deleted_at TIMESTAMPTZ
);

-- 命名空间索引 (复合索引)
CREATE INDEX IF NOT EXISTS idx_memories_namespace ON memories(client_id, user_id, agent_id, session_id) 
    WHERE deleted_at IS NULL;

-- 时间索引 (时序衰减查询)
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC) 
    WHERE deleted_at IS NULL;

-- 类型索引
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type) 
    WHERE deleted_at IS NULL;

-- 内容哈希索引 (去重)
CREATE INDEX IF NOT EXISTS idx_memories_content_hash ON memories(content_hash);

-- 记忆访问日志 (Phase 2: WRRF权重计算)
CREATE TABLE IF NOT EXISTS memory_access_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    
    access_type VARCHAR(20) NOT NULL,  -- read/write/delete
    accessed_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 查询上下文 (用于权重优化)
    query_text TEXT,
    similarity_score FLOAT
);

CREATE INDEX IF NOT EXISTS idx_access_logs_memory ON memory_access_logs(memory_id, accessed_at DESC);

-- 实体表 (Entity Boost)
CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 命名空间隔离
    client_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    
    -- 实体信息
    name VARCHAR(500) NOT NULL,
    entity_type VARCHAR(100) NOT NULL DEFAULT 'UNKNOWN',
    
    -- 关联的记忆ID列表（JSON数组）
    linked_memory_ids TEXT NOT NULL DEFAULT '[]',
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entities_namespace ON entities(client_id, user_id, agent_id);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name, entity_type);

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

CREATE TRIGGER trigger_entities_updated
    BEFORE UPDATE ON entities
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- 查询统计视图 (Phase 2: 自适应权重)
CREATE OR REPLACE VIEW memory_stats AS
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
