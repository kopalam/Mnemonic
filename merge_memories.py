#!/usr/bin/env python3
"""Merge fragmented memories into complete semantic statements"""
import os
import json
import asyncio
import asyncpg
import httpx
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

DB_URL = f"postgresql://mnemonic:{os.getenv('MNEMONIC_DB_PASSWORD')}@localhost:5434/mnemonic"
LLM_URL = os.getenv("MNEMONIC_LLM_API_URL", "http://120.25.63.187:9119/v1/chat/completions")
LLM_KEY = os.getenv("MNEMONIC_LLM_API_KEY")
EMBEDDING_URL = "https://api.siliconflow.cn/v1/embeddings"
EMBEDDING_KEY = os.getenv("MNEMONIC_EMBEDDING_API_KEY")

async def get_embedding(client: httpx.AsyncClient, text: str) -> list[float]:
    """Get embedding from SiliconFlow"""
    resp = await client.post(
        EMBEDDING_URL,
        headers={"Authorization": f"Bearer {EMBEDDING_KEY}"},
        json={"model": "Qwen/Qwen3-Embedding-0.6B", "input": text},
        timeout=30.0
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]

async def merge_with_llm(client: httpx.AsyncClient, memories: list[dict]) -> str:
    """Use LLM to merge multiple memories into one complete statement"""
    fragments = "\n".join(f"- {m['content']}" for m in memories)
    
    prompt = f"""你是一个记忆合并助手。下面是关于同一主题的多条碎片化记忆，请将它们合并为一条完整、语义丰富的陈述。

要求：
1. 保留所有关键信息，不要遗漏
2. 合并重复内容，消除冗余
3. 生成一条 80-200 字的完整陈述
4. 使用客观、准确的语言

碎片记忆：
{fragments}

合并后的记忆（只输出合并结果，不要其他内容）："""

    resp = await client.post(
        LLM_URL,
        headers={"Authorization": f"Bearer {LLM_KEY}"},
        json={
            "model": "gemma-4",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 500
        },
        timeout=60.0
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()

async def identify_entities(client: httpx.AsyncClient, memories: list[dict]) -> dict[str, list[dict]]:
    """Identify entity groups from memories using keyword matching"""
    
    # Define entity keywords
    entity_keywords = {
        "zSunKoin": ["zSunKoin", "交易系统", "量化交易", "杠杆", "K线", "CCXT", "TimescaleDB", "WebSocket", 
                     "趋势跟随", "BTC Regime", "ATR", "SignalGen", "Agent", "Redis Streams", "SOL-USDT", "HYPE-USDT"],
        "Mnemonic": ["Mnemonic", "记忆系统", "pgvector", "embedding", "FastAPI", "LLM降级", "四维测试"],
        "coinAnalysis": ["coinAnalysis", "Telegram Bot", "Solana Token", "免责声明", "试用机会"],
        "Solana生态": ["Solana", "RPC", "Helius", "每日快报", "链上异动"],
        "飞书集成": ["飞书", "feishu", "Wiki权限", "webhook", "chatid"],
        "用户偏好": ["用户要求", "用户希望", "Dashboard", "回测", "实盘", "模拟盘", "Grafana"],
        "Tavily搜索": ["Tavily", "搜索API", "tvly-dev"],
    }
    
    groups = defaultdict(list)
    
    for mem in memories:
        content = mem["content"]
        matched = False
        
        for entity, keywords in entity_keywords.items():
            if any(kw in content for kw in keywords):
                groups[entity].append(mem)
                matched = True
                break
        
        if not matched:
            groups["其他"].append(mem)
    
    return dict(groups)

async def main():
    conn = await asyncpg.connect(DB_URL)
    client = httpx.AsyncClient(timeout=120.0)
    
    # Get all active memories
    rows = await conn.fetch(
        """SELECT id, content, memory_type, importance, client_id, user_id, agent_id, session_id 
           FROM memories WHERE deleted_at IS NULL AND client_id='hermes' ORDER BY created_at"""
    )
    memories = [dict(r) for r in rows]
    print(f"共 {len(memories)} 条记忆")
    
    # Identify entity groups
    print("\n识别实体分组...")
    groups = await identify_entities(client, memories)
    
    for entity, mems in sorted(groups.items(), key=lambda x: -len(x[1])):
        print(f"  {entity}: {len(mems)} 条")
    
    # Merge groups with 2+ memories
    merged_count = 0
    deleted_count = 0
    
    for entity, mems in groups.items():
        if len(mems) < 2:
            continue
        
        print(f"\n合并 {entity} ({len(mems)} 条)...")
        
        # Show fragments
        for m in mems[:3]:
            print(f"  - {m['content'][:60]}...")
        if len(mems) > 3:
            print(f"  ... 还有 {len(mems)-3} 条")
        
        try:
            # Merge with LLM
            merged_content = await merge_with_llm(client, mems)
            print(f"  → 合并结果: {merged_content[:80]}...")
            
            # Get embedding for merged content
            embedding = await get_embedding(client, merged_content)
            embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
            
            # Insert merged memory
            import uuid
            await conn.execute(
                """INSERT INTO memories 
                   (id, content, memory_type, importance, client_id, user_id, agent_id, session_id, embedding)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::vector)""",
                str(uuid.uuid4()),
                merged_content,
                "fact",
                max(m["importance"] for m in mems),
                mems[0]["client_id"],
                mems[0]["user_id"],
                mems[0]["agent_id"],
                f"{mems[0]['session_id']}_merged",
                embedding_str
            )
            merged_count += 1
            
            # Soft-delete original memories
            for m in mems:
                await conn.execute(
                    "UPDATE memories SET deleted_at = NOW() WHERE id = $1",
                    m["id"]
                )
            deleted_count += len(mems)
            
            print(f"  ✅ 已合并并删除 {len(mems)} 条原始记忆")
            
        except Exception as e:
            print(f"  ❌ 合并失败: {e}")
    
    await conn.close()
    await client.aclose()
    
    print(f"\n完成: 合并 {merged_count} 组，删除 {deleted_count} 条碎片记忆")

if __name__ == "__main__":
    asyncio.run(main())
