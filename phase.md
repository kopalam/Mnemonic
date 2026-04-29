# Mnemonic 开发进度与计划

> AI Agent 持久化记忆存储中间件  
> 项目路径: `/Users/kopa/Documents/monic`  
> 飞书文档: `NsN9dmczxol3i2xWZ3IcxBAZndg`

---

## 当前状态

**Phase 1: 核心骨架** — ✅ 已完成 (2026-04-29)

- [x] 项目结构初始化
- [x] PostgreSQL + pgvector Schema
- [x] FastAPI CRUD API (8个端点)
- [x] 四级命名空间隔离 (client/user/agent/session)
- [x] 向量搜索 (pgvector cosine)
- [x] LLM事实提取 (Gemma-4)
- [x] 冲突检测 (向量预检 + LLM)
- [x] Hermes Provider适配器骨架
- [x] Docker Compose (PG 16 + pgvector)

**Git Commits:**
```
c9a7f22 Fix: pseudo-embedding NaN bug + ExtractRequest body
54f4c98 Phase 1: FastAPI skeleton + PG Schema + pgvector + CRUD API + Hermes Provider adapter
```

---

## 代码统计

| 文件 | 行数 | 说明 |
|------|------|------|
| `mnemonic/api.py` | 254 | FastAPI端点: health/create/list/get/update/delete/search/extract |
| `mnemonic/store.py` | 199 | CRUD + 向量搜索 + 命名空间过滤 |
| `mnemonic/services.py` | 225 | EmbeddingService (pseudo) + ExtractionService (Gemma-4) |
| `mnemonic/models.py` | 90 | Memory + MemoryAccessLog ORM模型 |
| `mnemonic/schemas.py` | 129 | Pydantic请求/响应模型 |
| `mnemonic/provider.py` | 161 | Hermes MemoryProvider适配器 |
| `mnemonic/config.py` | 57 | YAML配置加载 |
| `mnemonic/database.py` | 55 | AsyncPG + SQLAlchemy引擎 |
| `config.yaml` | 61 | 运行时配置 |
| `init.sql` | 100 | PG Schema + 索引 |
| `tests/test_api.py` | 67 | API测试 |
| `tests/test_provider.py` | 35 | Provider测试 |

**总计: ~1,500行核心代码**

---

## 部署状态

### Docker
```bash
CONTAINER ID   IMAGE                    STATUS         PORTS
c851c32dc684   pgvector/pgvector:pg16   Up 3 hours     0.0.0.0:5434->5432/tcp
```

### 启动命令
```bash
cd /Users/kopa/Documents/monic
MNEMONIC_DB_PASSWORD=mnemonic \
MNEMONIC_LLM_API_KEY=<key> \
.venv/bin/uvicorn mnemonic.api:app --host 0.0.0.0 --port 8010
```

### 配置
- **API端口**: 8010 (8000被aiShop占用)
- **PG端口**: 5434 (5432/5433被其他PG占用)
- **LLM端点**: `http://120.25.63.187:9119/v1` (Gemma-4)
- **Embedding**: pseudo-embedding (hash-based, 待替换)

---

## API端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/memories` | 创建记忆 |
| GET | `/memories` | 列表查询 |
| GET | `/memories/{id}` | 获取单条 |
| PATCH | `/memories/{id}` | 更新 |
| DELETE | `/memories/{id}` | 软删除 |
| POST | `/memories/search` | 向量搜索 |
| POST | `/memories/extract` | LLM提取+存储 |

### 命名空间Header
```
X-Namespace: client_id:user_id:agent_id[:session_id]
```

---

## Hermes兼容方案

已分析Hermes MemoryProvider接口 (`/Users/kopa/.hermes/hermes-agent/agent/memory_provider.py`):

**核心方法:**
- `is_available()` → 检查服务可用性
- `initialize()` → 初始化连接
- `get_tool_schemas()` → 返回tool定义
- `prefetch()` → 预取相关记忆
- `sync_turn()` → 同步对话结束时的记忆
- `handle_tool_call()` → 处理tool调用

**两条落地路线:**

### 路线A: 专属Mnemonic插件 (推荐)
- 新建 `plugins/memory/mnemonic/`
- 实现MemoryProvider接口
- Mnemonic服务端不改代码
- 优点: 干净解耦, Mnemonic保持通用

### 路线B: mem0 REST兼容层
- 在Mnemonic上添加 `/v1/memories` 路由
- 兼容mem0 Cloud API格式
- Hermes现有mem0插件可直接用
- 优点: 无需改Hermes代码

**待用户选择落地路线**

---

## 待解决问题

### 1. Embedding方案 (阻塞)
当前使用pseudo-embedding (hash-based), 无语义能力, cosine相似度极低 (~0.04)。

**选项:**
- (a) 自部署embedding端点 (如sentence-transformers)
- (b) OpenAI官方embedding API
- (c) 先跳过, Phase 2再处理

### 2. Hermes兼容落地
需用户选择路线A或B。

### 3. 飞书文档同步
飞书API限制较多, 建议用本地 `phase.md` + 手动同步。

---

## Phase 2 计划

### 2.1 搜索增强
- [ ] BM25关键词搜索 (tsvector + GIN索引)
- [ ] 混合检索 (向量 + BM25)
- [ ] 重排序 (WRRF权重融合)

### 2.2 记忆管理
- [ ] 遗忘机制 (四态机: Active → Dormant → Archived → Deleted)
- [ ] 自适应WRRF权重 (基于访问频率/时间衰减)
- [ ] 记忆压缩 (长对话摘要)

### 2.3 多租户
- [ ] API Key认证
- [ ] 速率限制
- [ ] 使用量统计

### 2.4 可观测性
- [ ] Prometheus metrics
- [ ] 结构化日志
- [ ] 健康检查增强 (DB/LLM/Embedding)

---

## Phase 3 计划

### 3.1 高级特性
- [ ] 记忆关联图谱 (entity linking)
- [ ] 时序推理 (before/after关系)
- [ ] 上下文窗口优化 (token预算)

### 3.2 部署
- [ ] Helm Chart (K8s)
- [ ] 备份/恢复
- [ ] 多区域部署

---

## 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| 框架 | FastAPI | 异步, OpenAPI自动文档 |
| ORM | SQLAlchemy 2.0 | 异步支持 |
| 数据库 | PostgreSQL 16 | 主存储 |
| 向量 | pgvector | 余弦相似度搜索 |
| LLM | Gemma-4 (自部署) | 事实提取 |
| Embedding | TBD | 语义向量 |
| 容器 | Docker Compose | 本地开发 |

---

## 关键决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| 存储 | PG + pgvector | 不引入新组件, 向量+关系一体化 |
| 命名空间 | 四级隔离 | client/user/agent/session, 灵活控制粒度 |
| 冲突检测 | 两阶段 | 向量预检(cosine>0.7) → LLM确认 |
| 提取粒度 | 细粒度 | 每条事实独立存储, 避免大块更新 |
| 跨Agent | 完全隔离 | 不同agent记忆不共享, 安全优先 |
| 配置 | config.yaml | 统一配置文件, 废弃.env |

---

## 下一步行动

1. **用户决定Embedding方案** → 替换pseudo-embedding
2. **用户选择Hermes兼容路线** → 落地插件或兼容层
3. **Phase 2开发** → BM25 + 遗忘机制

---

*最后更新: 2026-04-29*
