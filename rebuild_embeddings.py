#!/usr/bin/env python3
"""Batch rebuild embeddings with Qwen3-Embedding-0.6B"""
import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("MNEMONIC_EMBEDDING_API_KEY")
EMBEDDING_URL = "https://api.siliconflow.cn/v1/embeddings"
MODEL = "Qwen/Qwen3-Embedding-0.6B"
DB_URL = f"postgresql://mnemonic:{os.getenv('MNEMONIC_DB_PASSWORD')}@localhost:5434/mnemonic"

import asyncpg
import asyncio

async def get_embedding(client: httpx.AsyncClient, text: str) -> list[float]:
    """Get embedding from SiliconFlow API"""
    resp = await client.post(
        EMBEDDING_URL,
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"model": MODEL, "input": text},
        timeout=30.0
    )
    resp.raise_for_status()
    data = resp.json()
    return data["data"][0]["embedding"]

async def main():
    conn = await asyncpg.connect(DB_URL)
    client = httpx.AsyncClient()
    
    # Get all active memories
    rows = await conn.fetch(
        "SELECT id, content FROM memories WHERE deleted_at IS NULL ORDER BY created_at"
    )
    print(f"共 {len(rows)} 条记忆需要重灌 embedding")
    
    updated = 0
    errors = 0
    
    for i, row in enumerate(rows):
        mem_id = row["id"]
        content = row["content"]
        
        try:
            embedding = await get_embedding(client, content)
            
            # Update embedding in DB (pgvector needs string format)
            embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
            await conn.execute(
                "UPDATE memories SET embedding = $1::vector, updated_at = NOW() WHERE id = $2",
                embedding_str,
                mem_id
            )
            updated += 1
            
            if (i + 1) % 20 == 0:
                print(f"进度: {i+1}/{len(rows)} ({updated} 成功, {errors} 失败)")
                
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"Error updating {mem_id}: {e}")
        
        # Rate limit
        await asyncio.sleep(0.1)
    
    await conn.close()
    await client.aclose()
    
    print(f"\n✅ 完成: {updated}/{len(rows)} 条记忆 embedding 已更新为 {MODEL}")

if __name__ == "__main__":
    asyncio.run(main())
