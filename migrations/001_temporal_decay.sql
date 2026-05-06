-- Migration: Add temporal decay importance fields
-- Date: 2026-05-06
-- Description: Add initial_importance, access_count, last_accessed_at for temporal decay algorithm

-- Add new columns
ALTER TABLE memories
ADD COLUMN IF NOT EXISTS initial_importance FLOAT DEFAULT 0.5,
ADD COLUMN IF NOT EXISTS access_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_accessed_at TIMESTAMP WITH TIME ZONE;

-- Initialize existing records
UPDATE memories
SET
    initial_importance = importance,
    access_count = 0,
    last_accessed_at = updated_at
WHERE initial_importance IS NULL;

-- Create index for temporal queries
CREATE INDEX IF NOT EXISTS idx_memories_temporal
ON memories (importance DESC, last_accessed_at DESC)
WHERE deleted_at IS NULL;

-- Create index for access count queries
CREATE INDEX IF NOT EXISTS idx_memories_access
ON memories (access_count DESC, created_at DESC)
WHERE deleted_at IS NULL;

-- Add comment
COMMENT ON COLUMN memories.initial_importance IS 'Initial importance score (0-1) set at creation time';
COMMENT ON COLUMN memories.access_count IS 'Number of times this memory was retrieved';
COMMENT ON COLUMN memories.last_accessed_at IS 'Timestamp of last retrieval';
