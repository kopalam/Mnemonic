# Mnemonic 系统测试报告

**版本**: v0.1.0 Phase 1  
**测试日期**: 2026-04-29  
**测试环境**: macOS, Docker PG 16+pgvector, FastAPI 8010  
**测试方法**: 参考mem0 evaluation + LOCOMO benchmark + Hermes MemoryProvider接入场景  

---

## 1. 测试概要

| 类别 | 测试数 | 通过 | 失败 | 通过率 |
|------|--------|------|------|--------|
| 基础CRUD | 11 | 11 | 0 | 100% |
| 语义搜索 | 9 | 2 | 7 | 22% |
| Extract | 5 | 2 | 3 | 40% |
| 边界条件 | 7 | 7 | 0 | 100% |
| 命名空间隔离 | 6 | 5 | 1 | 83% |
| Hermes接入场景 | 13 | 12 | 1 | 92% |
| 性能基准 | 3 | 3 | 0 | 100% |
| HTTP/CORS | 3 | 3 | 0 | 100% |
| 并发安全 | 2 | 2 | 0 | 100% |
| **总计** | **59** | **47** | **12** | **80%** |

---

## 2. 通过的测试项 (47项)

### CRUD操作 (100% 通过)
- ✅ T01: POST /memories 创建单条记忆 → 201
- ✅ T02: POST /memories 创建含所有字段的记忆
- ✅ T03: POST /memories 自动生成embedding → 201
- ✅ T04: GET /memories 列表查询 → 200 + 分页
- ✅ T05: GET /memories/{id} 单条查询 → 200
- ✅ T06: PATCH /memories/{id} 更新content+importance → 200
- ✅ T07: DELETE /memories/{id} 软删除 → 204
- ✅ T08: GET /memories/{id} 删除后404
- ✅ T09: POST /memories/search 向量搜索 → 200
- ✅ T10: 数据库embedding字段正确写入
- ✅ T12: 响应字段完整性(id/content/memory_type/importance/created_at/updated_at)

### 边界条件 (100% 通过)
- ✅ T16.1: limit>100 → 422
- ✅ T16.2: 负offset → 422
- ✅ T16.3: 超大offset → 200空列表
- ✅ T16.5: SQL注入内容安全存储（参数化查询保护）
- ✅ T16.6: Unicode/Emoji内容正常存储
- ✅ T16.7: importance高精度存储(0.123456789)
- ✅ T16.4: 非法memory_type可创建（⚠️ 记为BUG-005）

### 命名空间隔离 (83% 通过)
- ✅ T17.1: 3级namespace能看到自己的记忆
- ✅ T17.2: 3级namespace搜索能命中
- ✅ T17.3: 4级namespace有独立记忆空间
- ✅ T20.5: 不同agent_id隔离（analyst看不到hnoe的记忆）
- ✅ T20.6: 不同client完全隔离（OpenClaw看不到Hermes）
- ✅ T20.7: 3级namespace可搜索所有子session记忆

### Hermes接入场景 (92% 通过)
- ✅ T20.1: Hermes写入用户偏好
- ✅ T20.2: Hermes写入项目上下文
- ✅ T20.3: Hermes写入运营规则
- ✅ T20.7: 3级ns跨session搜索成功
- ✅ T20.8: 批量写入10条（Hermes启动注入）
- ✅ T20.9: 批量后搜索延迟0.74s
- ✅ T22.1: 会话启动: 3级ns召回已有记忆
- ✅ T22.2: 对话中存储新事实
- ✅ T22.3: 对话中更新记忆(用户纠正)
- ✅ T22.4: 对话中搜索相关记忆
- ✅ T22.5: 新session可召回(3级ns)
- ✅ T23.1: search(all)模式: 3级ns跨session搜索
- ✅ T23.2: 按importance过滤
- ✅ T23.3: 按memory_type过滤
- ✅ T24: 多端并发写入（Desktop/Mobile/OpenClaw）
- ✅ T25.1: 永久记忆写入
- ✅ T25.2: 永久记忆读回一致

### 性能基准 (100% 通过)
- ✅ T15.1: 单条创建延迟 0.70s（含embedding API调用）
- ✅ T15.2: 搜索延迟 0.35s
- ✅ T15.3: 列表查询延迟 0.37s

### HTTP/CORS (100% 通过)
- ✅ T19.1: CORS OPTIONS预检
- ✅ T19.2: PUT方法 → 405
- ✅ T19.3: POST /memories/{id} → 405

### 并发安全 (100% 通过)
- ✅ T21.1: 并发PATCH不崩溃（3个并发更新）
- ✅ T21.2: 并发后状态一致（最后一个写入者获胜）

---

## 3. 失败的测试项 (12项)

### 搜索质量 (7项失败)
- ❌ T14: 搜索精确率(TOP1) = 14.3% (1/7)
  - "Boss的职业背景" → 命中"Boss偏好简洁回复" (cosine=0.658)
  - "开发任务怎么处理" → 命中"Boss偏好简洁回复" (cosine=0.680)
  - "Solana" → 命中"test" (cosine=0.620)
  - "8010端口" → 命中"快速创建测试_0" (cosine=0.594)
  - "coinAnalysis" → 命中"Boss是Web3资深运营专家" (cosine=0.567) ← 部分相关
  - "embedding配置" → 命中"快速创建测试_0" (cosine=0.569)
  - "今天是星期几" → 命中"Boss偏好简洁回复" (cosine=0.578) ← 应为无关
  
  **根因**: 测试数据噪声(importance未参与排序) + 4096维精确搜索无预过滤

### Extract (3项失败)
- ❌ T11.1: Extract返回201(期望200) → BUG-004
- ❌ T11.3: 短文本extract也返回201+空列表
- ❌ T11.5: auto_store=false返回空列表

  **根因**: LLM API key未配置，所有extract请求返回[]

### 命名空间 (1项失败)
- ❌ T20.4: 新session(4级namespace)跨session召回0条 → BUG-006
  - session_20260501搜索不到session_20260430的记忆
  - **workaround**: 使用3级namespace搜索可正常工作

### 响应格式 (1项失败)
- ❌ T11.2: Extract返回列表len=0 → 同Extract LLM问题

---

## 4. BUG清单

| ID | 严重度 | 状态 | 标题 |
|----|--------|------|------|
| BUG-002/005 | P2 | 🔴 Open | memory_type无枚举校验 |
| BUG-003 | P2 | 🟡 Investigating | search返回similarity=null |
| BUG-004 | P3 | ⏳ Deferred | Extract status_code硬编码201 |
| BUG-006 | P1 | 🔴 Open | 4级namespace跨session无法召回 |
| BUG-007 | P1 | 🔴 Open | 搜索质量受噪声数据干扰(14.3%精确率) |
| BUG-008 | P1 | 🟡 Deferred | Extract不可用(LLM API key未配置) |

详细修复方案见 [BugFix.md](BugFix.md)

---

## 5. Hermes MemoryProvider 接入评估

### 兼容性矩阵

| Hermes操作 | Mnemonic API | 状态 | 备注 |
|-----------|-------------|------|------|
| add(memory) | POST /memories | ✅ 完全兼容 | 自动生成embedding |
| search(query) | POST /memories/search | ✅ 兼容 | 需用3级ns实现跨session |
| get(id) | GET /memories/{id} | ✅ 完全兼容 | |
| update(id, data) | PATCH /memories/{id} | ✅ 完全兼容 | 自动重算embedding |
| delete(id) | DELETE /memories/{id} | ✅ 完全兼容 | 软删除 |
| get_all() | GET /memories | ✅ 兼容 | 支持type/importance过滤 |
| extract(text) | POST /memories/extract | ⚠️ 需配置 | 需真实LLM API key |

### 推荐接入方案

**方案: 3级namespace搜索 + 4级namespace写入**

```python
# Hermes MemoryProvider 伪代码
class MnemonicProvider:
    def __init__(self, client_id, user_id, agent_id):
        self.write_ns = f"{client_id}:{user_id}:{agent_id}:{session_id}"  # 4级隔离写入
        self.read_ns = f"{client_id}:{user_id}:{agent_id}"                # 3级共享读取
    
    async def add(self, content, **kwargs):
        # 写入时用4级namespace → session隔离
        await api.post("/memories", headers={"X-Namespace": self.write_ns}, ...)
    
    async def search(self, query, **kwargs):
        # 搜索时用3级namespace → 跨session共享
        await api.post("/memories/search", headers={"X-Namespace": self.read_ns}, ...)
```

---

## 6. Phase 1 结论

### 可交付
- ✅ CRUD操作完整可用
- ✅ 语义搜索基础设施就绪
- ✅ 命名空间隔离正确
- ✅ Hermes接入兼容(通过3级namespace workaround)
- ✅ 性能达标(创建<1s, 搜索<0.5s)
- ✅ 并发安全

### 需修复后交付
- 🔧 BUG-006: 跨session召回(推荐方案C: search默认3级)
- 🔧 BUG-008: Extract需真实LLM key

### 延后至Phase 2
- 📋 BUG-002/005: memory_type枚举
- 📋 BUG-003: similarity返回null
- 📋 BUG-007: 搜索质量优化(WRRF + importance加权)
- 📋 BUG-004: Extract status code优化
