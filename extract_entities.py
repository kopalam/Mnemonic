#!/usr/bin/env python3
"""从合并后的记忆提取实体并填充 entities 表"""

import asyncio
import httpx
import json

API_BASE = "http://localhost:8010"
NAMESPACE = "hermes:boss:hnoe:rebuild_merged"

async def main():
    client = httpx.AsyncClient(timeout=120.0)
    
    # 1. 获取所有合并后的记忆
    resp = await client.get(
        f"{API_BASE}/memories",
        headers={"X-Namespace": NAMESPACE},
        params={"limit": 50}
    )
    
    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code}")
        return
    
    memories = resp.json().get("memories", [])
    print(f"共 {len(memories)} 条记忆\n")
    
    # 2. 对每条记忆提取实体（通过 extract 端点）
    entity_data = []
    for mem in memories:
        content = mem["content"]
        mem_id = mem["id"]
        
        # 用 extract 端点的实体提取功能
        # 但 extract 会创建新记忆，所以直接调用 entity_service
        # 这里用简单方法：直接调用 /memories/extract 但只取实体
        
        print(f"处理记忆 {mem_id[:8]}...")
        print(f"  内容: {content[:60]}...")
        
        # 手动提取实体（简单规则）
        entities = extract_entities_simple(content)
        print(f"  实体: {entities}")
        
        entity_data.append({
            "memory_id": mem_id,
            "entities": entities
        })
    
    # 3. 写入 entities 表（通过 API 没有直接端点，用 SQL）
    print("\n写入 entities 表...")
    
    # 用 Docker exec 直接写
    import subprocess
    
    for item in entity_data:
        mem_id = item["memory_id"]
        for ent in item["entities"]:
            name = ent["name"]
            ent_type = ent["type"]
            
            # Upsert SQL
            sql = f"""
            INSERT INTO entities (id, client_id, user_id, agent_id, name, entity_type, linked_memory_ids, created_at, updated_at)
            SELECT gen_random_uuid(), 'hermes', 'boss', 'hnoe', '{name}', '{ent_type}', jsonb_build_array('{mem_id}'), NOW(), NOW()
            WHERE NOT EXISTS (
                SELECT 1 FROM entities WHERE name = '{name}' AND client_id = 'hermes' AND user_id = 'boss'
            )
            ON CONFLICT DO NOTHING;
            """
            
            # 如果已存在，追加 memory_id
            sql2 = f"""
            UPDATE entities 
            SET linked_memory_ids = linked_memory_ids || jsonb_build_array('{mem_id}')
            WHERE name = '{name}' AND client_id = 'hermes' AND user_id = 'boss' 
              AND NOT linked_memory_ids ? '{mem_id}';
            """
            
            subprocess.run([
                "docker", "exec", "mnemonic-postgres",
                "psql", "-U", "mnemonic", "-d", "mnemonic",
                "-c", sql
            ], capture_output=True)
            
            subprocess.run([
                "docker", "exec", "mnemonic-postgres",
                "psql", "-U", "mnemonic", "-d", "mnemonic",
                "-c", sql2
            ], capture_output=True)
    
    print("完成！")
    
    # 验证
    result = subprocess.run([
        "docker", "exec", "mnemonic-postgres",
        "psql", "-U", "mnemonic", "-d", "mnemonic",
        "-c", "SELECT COUNT(*) FROM entities WHERE client_id='hermes'"
    ], capture_output=True, text=True)
    
    print(result.stdout)


def extract_entities_simple(content: str) -> list[dict]:
    """简单实体提取规则"""
    entities = []
    
    # 项目名
    projects = ["zSunKoin", "Mnemonic", "coinAnalysis", "Hermes"]
    for p in projects:
        if p in content:
            entities.append({"name": p, "type": "PROJECT"})
    
    # 技术栈
    techs = ["FastAPI", "PostgreSQL", "TimescaleDB", "Redis", "CCXT", "WebSocket", "pgvector", "Docker", "Grafana", "Polars", "PyTorch"]
    for t in techs:
        if t in content:
            entities.append({"name": t, "type": "TECHNOLOGY"})
    
    # 模型
    models = ["Gemma-4", "Qwen3", "BGE-M3", "Gemma"]
    for m in models:
        if m in content:
            entities.append({"name": m, "type": "MODEL"})
    
    # API/配置
    configs = ["Tavily", "Helius", "tvly-dev", "59d0dfaf", "SiliconFlow", "8010", "5434"]
    for c in configs:
        if c in content:
            entities.append({"name": c, "type": "CONFIG"})
    
    # 业务概念
    concepts = ["趋势跟随", "杠杆", "止损", "止盈", "回测", "实盘", "DRY_RUN", "RPC", "MEV", "Jito"]
    for c in concepts:
        if c in content:
            entities.append({"name": c, "type": "CONCEPT"})
    
    # 平台
    platforms = ["飞书", "Telegram", "Binance", "Solana", "X"]
    for p in platforms:
        if p in content:
            entities.append({"name": p, "type": "PLATFORM"})
    
    # 周期
    periods = ["15分钟", "15m", "1h", "4h", "1小时", "4小时"]
    for p in periods:
        if p in content:
            entities.append({"name": p, "type": "PERIOD"})
    
    return entities


if __name__ == "__main__":
    asyncio.run(main())