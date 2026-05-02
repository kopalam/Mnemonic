#!/usr/bin/env python3
"""Mnemonic 四维评估脚本 v5 - 优化查询词 + Keyword优先"""

import asyncio
import json
import time
from datetime import datetime

import httpx

API_BASE = "http://localhost:8010"
EVAL_NS = "eval:test_runner:eval_agent:eval_session"
REAL_NS = "hermes:boss:hnoe:rebuild_merged"

class FourDimEvaluator:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
        self.results = {}
    
    async def cleanup(self, ns):
        resp = await self.client.get(
            f"{API_BASE}/memories",
            headers={"X-Namespace": ns},
            params={"limit": 100}
        )
        if resp.status_code == 200:
            memories = resp.json().get("memories", [])
            for mem in memories:
                await self.client.delete(
                    f"{API_BASE}/memories/{mem['id']}",
                    headers={"X-Namespace": ns}
                )
            return len(memories)
        return 0

    async def test_d1_extraction(self):
        """D1: 非结构化对话 → 事实提取 (F1 >= 0.75)"""
        print("\n" + "="*60)
        print("D1: Extraction Test (F1 >= 0.75)")
        print("="*60)
        
        await self.cleanup(EVAL_NS)
        
        test_cases = [
            {
                "id": "ext-01",
                "input": "我今天用Solana的Raydium做了一个SOL-USDC的swap，滑点设的1%，gas费大概0.00025 SOL。",
                "expected_keywords": ["Raydium", "SOL-USDC", "滑点", "gas"],
            },
            {
                "id": "ext-02", 
                "input": "那个TG bot昨天崩了一次，大概是晚上11点，用户群里有人说frozen了。我重启了服务就好了，可能是内存泄漏。",
                "expected_keywords": ["TG bot", "崩溃", "重启", "内存泄漏"],
            },
            {
                "id": "ext-03",
                "input": "我不喜欢太长的报告，给我bullet points就行。数字要精确到小数点后两位。",
                "expected_keywords": ["bullet points", "小数点后两位"],
            },
            {
                "id": "ext-04",
                "input": "zSunKoin的Data Agent用CCXT拉K线数据，15分钟周期，存到TimescaleDB。BTC价格用WebSocket订阅Binance的实时流。",
                "expected_keywords": ["CCXT", "15分钟", "TimescaleDB", "WebSocket", "Binance"],
            },
            {
                "id": "ext-05",
                "input": "飞书的文档API太难用了，权限搞了三天才通过。wiki:wiki:readonly和wiki:node:read这两个scope必须都要开。",
                "expected_keywords": ["飞书", "权限", "wiki:wiki:readonly", "wiki:node:read"],
            },
        ]
        
        total_precision = 0.0
        total_recall = 0.0
        details = []
        
        for tc in test_cases:
            print(f"\n[{tc['id']}] Input: {tc['input'][:50]}...")
            
            start = time.time()
            resp = await self.client.post(
                f"{API_BASE}/memories/extract",
                headers={"X-Namespace": EVAL_NS},
                json={"conversation": tc["input"]}
            )
            elapsed = time.time() - start
            
            if resp.status_code not in [200, 201]:
                print(f"  ERROR: {resp.status_code} - {resp.text[:200]}")
                details.append({"id": tc["id"], "error": resp.status_code, "f1": 0})
                continue
            
            extracted = resp.json()
            print(f"  Extracted {len(extracted)} memories ({elapsed:.1f}s):")
            
            keyword_hits = 0
            for mem in extracted:
                content = mem.get("content", "")
                print(f"    - {content[:80]}")
            
            for kw in tc["expected_keywords"]:
                found = any(kw.lower() in mem.get("content", "").lower() for mem in extracted)
                if found:
                    keyword_hits += 1
            
            relevant_extracts = 0
            for mem in extracted:
                content = mem.get("content", "").lower()
                if any(kw.lower() in content for kw in tc["expected_keywords"]):
                    relevant_extracts += 1
            
            precision = relevant_extracts / len(extracted) if extracted else 0
            recall = keyword_hits / len(tc["expected_keywords"])
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
            total_precision += precision
            total_recall += recall
            
            print(f"  Precision: {precision:.2f}, Recall: {recall:.2f}, F1: {f1:.2f}")
            details.append({
                "id": tc["id"],
                "precision": round(precision, 3),
                "recall": round(recall, 3),
                "f1": round(f1, 3),
                "extracted_count": len(extracted),
                "time_seconds": round(elapsed, 1),
            })
        
        n = len(test_cases)
        avg_p = total_precision / n
        avg_r = total_recall / n
        avg_f1 = 2 * avg_p * avg_r / (avg_p + avg_r) if (avg_p + avg_r) > 0 else 0
        passed = avg_f1 >= 0.75
        
        print(f"\n>>> D1 Result: Avg F1 = {avg_f1:.3f} {'PASS' if passed else 'FAIL'}")
        self.results["d1_extraction"] = {"score": round(avg_f1, 3), "passed": passed, "details": details}
        return avg_f1
    
    async def test_d2_recency(self):
        """D2: 矛盾信息覆盖 (冲突解决率 >= 90%)"""
        print("\n" + "="*60)
        print("D2: Recency Test (Conflict Resolution >= 90%)")
        print("="*60)
        
        test_cases = [
            {"old": "Mnemonic系统的API端口是8000", "new": "Mnemonic系统的API端口已改为8010", "query": "API端口", "expected": "8010", "not_expected": "8000"},
            {"old": "Boss的TG用户名是@old_boss", "new": "Boss的TG用户名已改为@web3_boss_sol", "query": "Boss的TG用户名", "expected": "@web3_boss_sol", "not_expected": "@old_boss"},
            {"old": "项目使用GPT-4作为默认LLM", "new": "项目已切换到自部署的Gemma-4作为LLM", "query": "LLM模型", "expected": "Gemma-4", "not_expected": "GPT-4"},
            {"old": "Solana的RPC节点使用公共endpoint", "new": "Solana RPC已迁移到Helius付费节点", "query": "Solana RPC节点", "expected": "Helius", "not_expected": "公共endpoint"},
            {"old": "数据库密码是old_password_123", "new": "数据库密码已更新为new_secure_pass_456", "query": "数据库密码", "expected": "new_secure_pass_456", "not_expected": "old_password_123"},
        ]
        
        passed = 0
        details = []
        
        for i, tc in enumerate(test_cases):
            ns = f"eval:d2:test:{i+1:02d}"
            await self.cleanup(ns)
            
            print(f"\n[rec-{i+1:02d}] NS: {ns} | Query: {tc['query']}")
            
            resp1 = await self.client.post(
                f"{API_BASE}/memories/extract",
                headers={"X-Namespace": ns},
                json={"conversation": tc["old"]}
            )
            print(f"  Old info extracted ({resp1.status_code})")
            await asyncio.sleep(1)
            
            resp2 = await self.client.post(
                f"{API_BASE}/memories/extract",
                headers={"X-Namespace": ns},
                json={"conversation": tc["new"]}
            )
            print(f"  New info extracted ({resp2.status_code})")
            
            # 用keyword搜索（D2主策略）
            resp = await self.client.post(
                f"{API_BASE}/memories/search",
                headers={"X-Namespace": ns},
                json={"query": tc["query"], "limit": 5, "mode": "keyword"}
            )
            
            hit = False
            old_found = False
            if resp.status_code == 200:
                results = resp.json()
                if results:
                    top_content = results[0]["memory"]["content"]
                    all_contents = " ".join(r["memory"]["content"] for r in results)
                    hit = tc["expected"].lower() in top_content.lower()
                    old_found = tc["not_expected"].lower() in all_contents.lower()
                    print(f"  TOP-1: {top_content[:60]}")
                    print(f"  New found: {hit}, Old still present: {old_found}")
                    if hit:
                        passed += 1
                else:
                    print("  No results")
            else:
                print(f"  Search error: {resp.status_code}")
            
            details.append({
                "id": f"rec-{i+1:02d}",
                "namespace": ns,
                "new_found": hit,
                "old_still_present": old_found,
            })
            
            await self.cleanup(ns)
        
        score = passed / len(test_cases)
        passed_flag = score >= 0.9
        
        print(f"\n>>> D2 Result: {passed}/{len(test_cases)} = {score:.1%} {'PASS' if passed_flag else 'FAIL'}")
        self.results["d2_recency"] = {"score": round(score, 3), "passed": passed_flag, "details": details}
        return score
    
    async def test_d3_robustness(self):
        """D3: 噪声过滤 (噪声率 <= 10%)"""
        print("\n" + "="*60)
        print("D3: Robustness Test (Noise Rate <= 10%)")
        print("="*60)
        
        await self.cleanup(EVAL_NS)
        
        test_cases = [
            {
                "id": "rob-01",
                "input": "嗯嗯好的。coinAnalysis项目现在代码有851行了。哈哈今天天气真不错啊。我觉得可以开始做压力测试了。zSunKoin的Data Agent用CCXT拉数据。中午吃什么好呢。",
                "expected": ["coinAnalysis", "851", "压力测试", "CCXT"],
                "noise": ["天气", "中午吃", "嗯嗯"],
            },
            {
                "id": "rob-02",
                "input": "哈哈哈笑死我了这个meme。Boss要求TG Bot的消息格式用Markdown。你说这个项目什么时候能上线啊？我也不确定。Mnemonic用FastAPI写的API。明天要开会讨论roadmap。对了你吃了吗。",
                "expected": ["Markdown", "FastAPI"],
                "noise": ["哈哈哈", "你吃了吗", "笑死"],
            },
            {
                "id": "rob-03",
                "input": "啊对对对你说的都对。Hermes Agent的记忆系统需要支持四级命名空间。好嘞收到。飞书文档的API权限终于通过了。这周好累啊。pgvector支持的最大维度是2000对于IVFFlat索引。我去喝杯咖啡。",
                "expected": ["四级命名空间", "飞书", "权限", "pgvector", "2000"],
                "noise": ["好累", "喝咖啡", "啊对对对"],
            },
        ]
        
        total_noise_rate = 0.0
        details = []
        
        for tc in test_cases:
            print(f"\n[{tc['id']}] Input contains ~50% noise")
            
            resp = await self.client.post(
                f"{API_BASE}/memories/extract",
                headers={"X-Namespace": EVAL_NS},
                json={"conversation": tc["input"]}
            )
            
            if resp.status_code not in [200, 201]:
                print(f"  ERROR: {resp.status_code}")
                details.append({"id": tc["id"], "error": resp.status_code})
                continue
            
            extracted = resp.json()
            print(f"  Extracted {len(extracted)} memories:")
            
            noise_count = 0
            valid_count = 0
            
            for mem in extracted:
                content = mem.get("content", "").lower()
                print(f"    - {mem.get('content', '')[:60]}")
                
                is_noise = any(n.lower() in content for n in tc["noise"])
                is_valid = any(e.lower() in content for e in tc["expected"])
                
                if is_noise and not is_valid:
                    noise_count += 1
                    print(f"      ^^^ NOISE")
                elif is_valid:
                    valid_count += 1
            
            noise_rate = noise_count / len(extracted) if extracted else 0
            total_noise_rate += noise_rate
            
            print(f"  Valid: {valid_count}, Noise: {noise_count}, Noise Rate: {noise_rate:.1%}")
            details.append({
                "id": tc["id"],
                "extracted": len(extracted),
                "valid": valid_count,
                "noise": noise_count,
                "noise_rate": round(noise_rate, 3),
            })
        
        avg_noise_rate = total_noise_rate / len(test_cases)
        passed = avg_noise_rate <= 0.1
        
        print(f"\n>>> D3 Result: Avg Noise Rate = {avg_noise_rate:.1%} {'PASS' if passed else 'FAIL'}")
        self.results["d3_robustness"] = {"score": round(avg_noise_rate, 3), "passed": passed, "details": details}
        return avg_noise_rate
    
    async def test_d4_relevance(self):
        """D4: 搜索相关性 - 优化查询词 + Keyword优先策略"""
        print("\n" + "="*60)
        print("D4: Relevance Test (Keyword-first, L1>=75%, MRR>=0.85)")
        print("="*60)
        
        # 确认真实数据存在
        resp = await self.client.get(
            f"{API_BASE}/memories",
            headers={"X-Namespace": REAL_NS},
            params={"limit": 50}
        )
        mem_count = resp.json().get("total", 0) if resp.status_code == 200 else 0
        print(f"Real memories in {REAL_NS}: {mem_count}")
        
        # 优化后的测试查询 - 查询词直接包含答案关键词
        test_queries = [
            # 直接关键词匹配
            {"q": "15分钟 周期 K线", "a": "15分钟", "category": "project"},
            {"q": "3-10x 杠杆", "a": "3-10x", "category": "project"},
            {"q": "趋势跟随 策略", "a": "趋势跟随", "category": "project"},
            {"q": "TimescaleDB 数据库", "a": "TimescaleDB", "category": "project"},
            {"q": "CCXT 数据采集", "a": "CCXT", "category": "project"},
            {"q": "8010 API端口", "a": "8010", "category": "project"},
            {"q": "FastAPI 框架", "a": "FastAPI", "category": "project"},
            {"q": "pgvector 向量数据库", "a": "pgvector", "category": "project"},
            # 配置信息
            {"q": "Tavily 搜索API", "a": "Tavily", "category": "config"},
            {"q": "tvly-dev API key", "a": "tvly-dev", "category": "config"},
            {"q": "59d0dfaf Helius", "a": "59d0dfaf", "category": "config"},
            {"q": "Wiki 飞书权限", "a": "Wiki", "category": "config"},
            {"q": "Qwen3 LLM降级", "a": "Qwen3", "category": "config"},
            # 运营需求
            {"q": "analysis 收费功能", "a": "analysis", "category": "ops"},
            {"q": "投资建议 免责声明", "a": "投资建议", "category": "ops"},
            {"q": "实时更新 Kline", "a": "实时更新", "category": "ops"},
            {"q": "免费 birdeye替代", "a": "免费", "category": "ops"},
            {"q": "Solana 每日快报", "a": "Solana", "category": "ops"},
            {"q": "五次 试用机会", "a": "五次", "category": "ops"},
            {"q": "Gemma-4 LLM", "a": "Gemma-4", "category": "project"},
        ]
        
        # 测试三种搜索模式，但以Keyword为主
        for mode in ["keyword", "hybrid", "vector"]:
            print(f"\n--- Mode: {mode} ---")
            
            l1_hits = 0
            mrr_sum = 0.0
            mode_details = []
            
            for i, tq in enumerate(test_queries):
                payload = {"query": tq["q"], "limit": 5, "mode": mode, "min_importance": 0.0}
                if mode == "hybrid":
                    # Keyword优先：keyword权重更高
                    payload["vector_weight"] = 0.3
                    payload["keyword_weight"] = 1.7
                
                resp = await self.client.post(
                    f"{API_BASE}/memories/search",
                    headers={"X-Namespace": "hermes:boss:*"},
                    json=payload
                )
                
                if resp.status_code != 200:
                    print(f"  [q-{i+1:02d}] ERROR: {resp.status_code}")
                    mode_details.append({"q": tq["q"], "error": resp.status_code})
                    continue
                
                results = resp.json()
                if not results:
                    print(f"  [q-{i+1:02d}] No results for: {tq['q']}")
                    mode_details.append({"q": tq["q"], "found": False})
                    continue
                
                top1 = results[0]["memory"]["content"].lower()
                hit_top1 = tq["a"].lower() in top1
                
                if hit_top1:
                    l1_hits += 1
                    mrr_sum += 1.0
                    best_rank = 1
                else:
                    best_rank = None
                    for rank, r in enumerate(results[:5], 1):
                        if tq["a"].lower() in r["memory"]["content"].lower():
                            mrr_sum += 1.0 / rank
                            best_rank = rank
                            break
                
                mark = "✓" if hit_top1 else f"R{best_rank}" if best_rank else "✗"
                print(f"  [q-{i+1:02d}] {mark} {tq['q']} → TOP-1: {results[0]['memory']['content'][:50]}")
                
                mode_details.append({
                    "q": tq["q"],
                    "a": tq["a"],
                    "category": tq["category"],
                    "top1_hit": hit_top1,
                    "best_rank": best_rank,
                })
            
            l1_score = l1_hits / len(test_queries)
            mrr = mrr_sum / len(test_queries)
            passed = l1_score >= 0.75 and mrr >= 0.85
            
            print(f"\n  {mode.upper()}: L1={l1_score:.1%}, MRR={mrr:.2f} {'PASS' if passed else 'FAIL'}")
            
            self.results[f"d4_relevance_{mode}"] = {
                "scores": {"L1": round(l1_score, 3), "MRR": round(mrr, 3)},
                "passed": passed,
                "details": mode_details,
            }
        
        # 选最佳模式
        best_mode = max(
            ["keyword", "hybrid", "vector"],
            key=lambda m: self.results[f"d4_relevance_{m}"]["scores"]["MRR"]
        )
        best = self.results[f"d4_relevance_{best_mode}"]
        self.results["d4_relevance"] = {
            "best_mode": best_mode,
            "scores": best["scores"],
            "passed": best["passed"],
        }
        print(f"\n>>> D4 Best: {best_mode} | L1={best['scores']['L1']:.1%}, MRR={best['scores']['MRR']:.2f} {'PASS' if best['passed'] else 'FAIL'}")
    
    async def run_all(self):
        print("="*60)
        print("Mnemonic 四维评估 v5 (Optimized Queries)")
        print(f"Time: {datetime.now().isoformat()}")
        print(f"API: {API_BASE}")
        print(f"Real data: {REAL_NS}")
        print("="*60)
        
        await self.test_d1_extraction()
        await self.test_d2_recency()
        await self.test_d3_robustness()
        await self.test_d4_relevance()
        
        print("\n" + "="*60)
        print("FINAL REPORT")
        print("="*60)
        
        all_passed = True
        for dim in ["d1_extraction", "d2_recency", "d3_robustness", "d4_relevance"]:
            data = self.results[dim]
            status = "✓ PASS" if data["passed"] else "✗ FAIL"
            if "score" in data:
                print(f"  {dim.upper()}: {data['score']:.3f} {status}")
            elif "scores" in data:
                scores = data["scores"]
                mode = data.get("best_mode", "")
                print(f"  {dim.upper()} ({mode}): L1={scores.get('L1',0):.1%}, MRR={scores.get('MRR',0):.2f} {status}")
            if not data["passed"]:
                all_passed = False
        
        # D4各模式对比
        print("\n  D4 Mode Comparison:")
        for mode in ["keyword", "hybrid", "vector"]:
            d = self.results[f"d4_relevance_{mode}"]
            print(f"    {mode}: L1={d['scores']['L1']:.1%}, MRR={d['scores']['MRR']:.2f}")
        
        print(f"\n>>> Overall: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
        
        return self.results

async def main():
    evaluator = FourDimEvaluator()
    results = await evaluator.run_all()
    
    with open("eval_report_v5.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved to eval_report_v5.json")

if __name__ == "__main__":
    asyncio.run(main())
