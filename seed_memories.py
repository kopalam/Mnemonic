#!/usr/bin/env python3
"""Seed real memories from HNOE memory store."""

import asyncio
import httpx

API_BASE = "http://localhost:8010"
NAMESPACE = "hermes:boss:hnoe:memory_import"

# 真实记忆数据（中文）
MEMORIES = [
    # User Profile
    ("Boss是Web3资深运营专家，主攻Solana生态。使用中文沟通。项目coinAnalysis是Solana Token分析Telegram Bot。", "fact", 0.9),
    ("Boss明确纠正：你是运营，不是开发。HNOE角色定位是运营，战场是用户增长、社区维稳、内容分发、数据监控，不是改代码补测试。开发相关任务交给开发处理。", "rule", 0.95),
    ("Boss对文案的要求是去AI味，用Degen视角写，拒绝使用诸如众所周知、在这个快速发展的数字时代、总而言之等陈词滥调。", "preference", 0.8),
    ("Boss的运营重点是用户增长和社区维稳。", "fact", 0.7),
    ("Boss使用中文沟通。", "preference", 0.6),
    
    # Project: coinAnalysis
    ("coinAnalysis是Solana Token分析Telegram Bot。技术栈是Python+Redis。", "fact", 0.7),
    
    # Project: zSunKoin
    ("zSunKoin项目路径：/Users/kopa/Documents/zSunKoin。", "fact", 0.5),
    ("zSunKoin项目是加密货币量化交易系统。技术栈：Python + CCXT/WebSocket + Redis Streams + TimescaleDB + Polars + PyTorch + Gemma-4(LLM) + Grafana + Docker Compose。", "fact", 0.7),
    ("zSunKoin的交易周期是15分钟，标的SOL-USDT/HYPE-USDT永续合约，BTC-USDT作市场状态参考。", "fact", 0.6),
    ("zSunKoin杠杆设置3-10x自适应。", "fact", 0.6),
    ("zSunKoin核心策略是趋势跟随（不预测只跟随）+ BTC Regime过滤 + ATR动态止损。", "fact", 0.7),
    ("zSunKoin有6个Agent：Data/Analyst/BTCWatch/Sentiment/Risk/Strategy。", "fact", 0.5),
    ("zSunKoin当前Phase1 Task1.1进行中（项目结构初始化），其余0%。", "context", 0.4),
    
    # Config: Search
    ("搜索服务使用Tavily API (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)，endpoint: https://api.tavily.com/search。", "config", 0.6),
    ("Boss要求所有搜索任务主动使用Tavily API，不要用浏览器搜索引擎。", "rule", 0.7),
    
    # Issue: Feishu
    ("飞书应用(cli_a9607dd1d23a5cb5)缺少Wiki权限(wiki:wiki:readonly/wiki:node:read)，无法通过API读写Wiki页面。授权链接: https://open.feishu.cn/app/cli_a9607dd1d23a5cb5/auth?q=wiki:wiki:readonly,wiki:node:read。", "issue", 0.8),
    ("Koin运营小组飞书ChatID: oc_df42013932e936746786eed59f8dc74b。", "config", 0.5),
    
    # Project: Mnemonic
    ("Mnemonic项目路径：/Users/kopa/Documents/monic。技术栈：FastAPI+PostgreSQL+pgvector，API端口8010（宿主机），PG端口5434（Docker）。", "fact", 0.7),
    ("Mnemonic的LLM降级已实现：LLMClient类自动Gemma-4(120.25.63.187:9119)降级到Qwen3-8B(SiliconFlow)，5分钟回探。", "fact", 0.7),
    ("Mnemonic环境变量需要MNEMONIC_LLM_API_KEY + MNEMONIC_LLM_FALLBACK_API_KEY + MNEMONIC_EMBEDDING_API_KEY + MNEMONIC_DB_PASSWORD。", "config", 0.8),
    ("Mnemonic四维测试：D1 F1=0.374(FAIL), D2 80%(FAIL), D3 100%(PASS), D4 keyword L3=80%(FAIL)。", "context", 0.4),
    ("Mnemonic Docker部署需要.env文件设置：MNEMONIC_LLM_API_KEY(用于Gemma-4), MNEMONIC_LLM_FALLBACK_API_KEY(SiliconFlow Qwen3-8B), MNEMONIC_EMBEDDING_API_KEY(SiliconFlow embedding), MNEMONIC_DB_PASSWORD(默认mnemonic_dev)。", "config", 0.7),
    ("SiliconFlow embedding API key已于2026-04-30更新（Boss提供新key）。环境变量名必须是MNEMONIC_EMBEDDING_API_KEY不是EMBEDDING_API_KEY。", "fact", 0.8),
    ("Mnemonic四维测试关键点：1) extract端点X-Namespace不能用通配符*需LLM(SiliconFlow Qwen3-8B，耗时约89s需120s超时); 2) D2时效性测试必须用extract而非POST直接写入(POST不触发冲突检测); 3) D4搜索测试需清理eval专用namespace避免污染; 4) 服务进程启动需设MNEMONIC_LLM_API_KEY+MNEMONIC_EMBEDDING_API_KEY+MNEMONIC_DB_PASSWORD三个环境变量; 5) services.py的ExtractionService在模块加载时实例化，改config后需重启进程。", "context", 0.9),
    
    # Noise memories (low importance)
    ("今天天气真不错。", "context", 0.1),
    ("哈哈哈这个meme太好笑了。", "context", 0.1),
    ("中午吃什么呢？", "context", 0.1),
    ("手机快没电了，得充电。", "context", 0.1),
]

async def main():
    async with httpx.AsyncClient(timeout=120) as client:
        # Clean old
        resp = await client.get(
            f"{API_BASE}/memories",
            headers={"X-Namespace": NAMESPACE},
            params={"limit": 100}
        )
        if resp.status_code == 200:
            old = resp.json().get("memories", [])
            for m in old:
                await client.delete(
                    f"{API_BASE}/memories/{m['id']}",
                    headers={"X-Namespace": NAMESPACE}
                )
            print(f"Cleaned {len(old)} old memories")
        
        # Write new
        count = 0
        for content, mem_type, importance in MEMORIES:
            resp = await client.post(
                f"{API_BASE}/memories",
                headers={"X-Namespace": NAMESPACE},
                json={
                    "content": content,
                    "memory_type": mem_type,
                    "importance": importance,
                }
            )
            if resp.status_code == 201:
                count += 1
        
        print(f"Written {count}/{len(MEMORIES)} memories to {NAMESPACE}")

if __name__ == "__main__":
    asyncio.run(main())
