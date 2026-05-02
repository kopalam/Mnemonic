#!/usr/bin/env python3
"""
从Hermes session历史和memory文件导入记忆到Mnemonic
"""
import json
import re
import os
from datetime import datetime
from pathlib import Path
import httpx

# Mnemonic API配置
MNEMONIC_API = os.getenv("MNEMONIC_API_URL", "http://localhost:8010")
CLIENT_ID = "hermes"
USER_ID = "boss"
AGENT_ID = "hnoe"

def parse_memory_md(md_path: Path) -> list[dict]:
    """解析MEMORY.md文件，提取记忆条目"""
    content = md_path.read_text()
    # 用§分隔
    entries = content.split("§")
    memories = []
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        # 每条记忆一行
        lines = [l.strip() for l in entry.split("\n") if l.strip()]
        if lines:
            memories.append({
                "content": lines[0],  # 第一行作为内容
                "metadata": {"source": "memory_md", "raw": entry}
            })
    return memories

def parse_session_jsonl(jsonl_path: Path) -> list[dict]:
    """解析session jsonl文件，提取用户消息作为记忆"""
    memories = []
    lines = jsonl_path.read_text().strip().split("\n")
    
    for line in lines:
        try:
            obj = json.loads(line.strip())
            if obj.get("role") == "user":
                content = obj.get("content", "").strip()
                if content and len(content) > 10:  # 过滤太短的
                    timestamp = obj.get("timestamp", "")
                    memories.append({
                        "content": content,
                        "metadata": {
                            "source": "session",
                            "file": jsonl_path.name,
                            "timestamp": timestamp
                        }
                    })
        except:
            continue
    
    return memories

def add_memory(content: str, metadata: dict) -> bool:
    """调用Mnemonic API添加记忆"""
    try:
        # X-Namespace格式: client_id:user_id:agent_id:session_id
        namespace = f"{CLIENT_ID}:{USER_ID}:{AGENT_ID}:session_import"
        resp = httpx.post(
            f"{MNEMONIC_API}/memories",
            json={
                "content": content,
                "memory_type": "fact",
                "importance": 0.5,
                "metadata": metadata
            },
            headers={"X-Namespace": namespace},
            timeout=30.0
        )
        return resp.status_code == 201
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    hermes_root = Path("/Users/kopa/.hermes")
    
    all_memories = []
    
    # 1. 解析MEMORY.md
    memory_md = hermes_root / "profiles/oper/memories/MEMORY.md"
    if memory_md.exists():
        mem_entries = parse_memory_md(memory_md)
        all_memories.extend(mem_entries)
        print(f"MEMORY.md: {len(mem_entries)} entries")
    
    # 2. 解析所有session jsonl
    sessions_dir = hermes_root / "sessions"
    if sessions_dir.exists():
        for jsonl_file in sessions_dir.glob("*.jsonl"):
            session_mems = parse_session_jsonl(jsonl_file)
            all_memories.extend(session_mems)
    
    print(f"Total memories to import: {len(all_memories)}")
    
    # 3. 批量导入
    success = 0
    failed = 0
    for i, mem in enumerate(all_memories):
        if add_memory(mem["content"], mem["metadata"]):
            success += 1
        else:
            failed += 1
        
        if (i + 1) % 50 == 0:
            print(f"Progress: {i+1}/{len(all_memories)}")
    
    print(f"\nDone: {success} success, {failed} failed")

if __name__ == "__main__":
    main()
