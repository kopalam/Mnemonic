# Mnemonic Vector 搜索修复记录

**日期**: 2026-05-02
**问题**: Vector 搜索 L1=13.3%，几乎不可用
**根因**: SiliconFlow Embedding API Key 无效 → 系统自动 fallback 到伪向量（无语义信息）

---

## 问题诊断过程

### 1. 现象
```
D4 Mode Comparison:
  hybrid:  L1=46.7%, L3=0.54
  keyword: L1=60.0%, L3=0.63
  vector:  L1=13.3%, L3=0.22  ← 严重失败
```

所有 Vector 搜索结果 score=0.000，向量相似度计算无意义。

### 2. 排查步骤

| 检查项 | 结果 | 结论 |
|--------|------|------|
| 向量维度 | 1024 | ✓ 正确 |
| 向量索引 | 无 | ✗ 缺失 IVFFlat 索引 |
| Embedding API | "Api key is invalid" | ✗ Key 无效 |

### 3. 根因确认

```python
# mnemonic/services.py 中的 fallback 逻辑
async def embed(self, text: str) -> list[float]:
    try:
        response = await self.client.embeddings.create(...)
        return vec
    except Exception as e:
        logger.error(f"Embedding API failed: {e}")
        self._fallback = True
        return await self._pseudo_embed(text)  # ← 伪向量，无语义
```

API Key 无效 → 自动切换到 `_pseudo_embed`（SHA256 哈希生成伪向量）→ 所有向量无语义信息 → Vector 搜索失效。

---

## 修复步骤

### Step 1: 更新 Embedding API Key

```bash
# .env 文件
MNEMONIC_EMBEDDING_API_KEY=sk-rnyhgvxsytryydnhovcnttgursrzhwkoywrxlnsxdoopqqaq
```

### Step 2: 更新 LLM API Key

```bash
# .env 文件
MNEMONIC_LLM_API_KEY=sk-prod-2026-12ddxxcsaaz
```

### Step 3: 禁用 LLM 降级（只用 Gemma-4）

```yaml
# config.yaml
llm:
  failover:
    max_retries: 0           # 禁用降级
    error_codes: []
    timeout_trigger: false
```

### Step 4: 重启容器并重建向量

```bash
cd /Users/kopa/Documents/monic
export $(grep -v '^#' .env | xargs)
docker-compose down && docker-compose up -d
python rebuild_embeddings.py
```

### Step 5: 创建向量索引

```sql
CREATE INDEX IF NOT EXISTS memories_embedding_idx 
ON memories USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);
```

---

## 修复结果

### Vector 搜索对比

| 指标 | 修复前 | 修复后 | 提升 |
|------|--------|--------|------|
| **Vector L1** | 13.3% | **53.3%** | **+40%** |
| **Vector L3 (MRR)** | 0.22 | **0.62** | **+182%** |

### 四维评估结果

| 维度 | 得分 | 状态 |
|------|------|------|
| D1 Extraction | F1=0.974 | ✓ PASS |
| D2 Recency | 100% | ✓ PASS |
| D3 Robustness | 0.0% 噪声 | ✓ PASS |
| D4 Relevance | L1=60%, L3=0.67 | ✗ FAIL |

---

## 遗留问题

### D4 搜索相关性未达标

**目标**: L1≥75%, L3≥0.85
**当前**: L1=60%, L3=0.67

**可能原因**:
1. 数据量太少（25 条记忆）
2. IVFFlat 索引在数据量少时召回率低（PG 提示："ivfflat index created with little data will cause low recall"）
3. 测试用例与记忆内容匹配度不够

**优化方向**:
1. 增加记忆数据量（建议 >100 条）
2. 调整 Hybrid 权重（当前 vector_weight=0.6, keyword_weight=1.4）
3. 考虑使用 HNSW 索引替代 IVFFlat

---

## 配置文件最终状态

### .env
```bash
MNEMONIC_DB_PASSWORD=mnemonic_dev
MNEMONIC_LLM_API_KEY=sk-prod-2026-12ddxxcsaaz
MNEMONIC_LLM_FALLBACK_API_KEY=sk-prod-2026-12ddxxcsaaz
MNEMONIC_EMBEDDING_API_KEY=sk-rnyhgvxsytryydnhovcnttgursrzhwkoywrxlnsxdoopqqaq
```

### config.yaml (关键配置)
```yaml
vector:
  embedding:
    base_url: "https://api.siliconflow.cn/v1"
    model: "Qwen/Qwen3-Embedding-0.6B"
    dim: 1024

llm:
  primary:
    model: "gemma-4"
    base_url: "http://120.25.63.187:9119/v1"
  failover:
    max_retries: 0  # 禁用降级
```

---

## 关键教训

1. **API Key 验证**: Docker 容器环境变量加载问题（`docker-compose` 默认不读取 `.env`，需要 `export $(cat .env | xargs)`）
2. **Fallback 机制**: 静默降级到伪向量，难以察觉，需要监控日志
3. **向量索引**: pgvector IVFFlat 在数据量少时效果差，建议数据量 >1000 时使用

---

## 后续行动

- [ ] 增加记忆数据量至 100+ 条
- [ ] 监控 Embedding API 调用成功率
- [ ] 考虑添加向量索引健康检查
- [ ] 评估 HNSW 索引替代方案
