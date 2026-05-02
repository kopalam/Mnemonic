# Mnemonic

独立部署的 AI Agent 持久化记忆存储中间件，服务 Hermes / OpenClaw 等多 Agent 框架。

## 快速开始

```bash
# 1. 安装依赖
uv sync

# 2. 启动 PostgreSQL (Docker)
docker compose up -d

# 3. 启动服务
MNEMONIC_DB_PASSWORD=mnemonic_dev_password \
MNEMONIC_LLM_API_KEY=<your-key> \
MNEMONIC_EMBEDDING_API_KEY=<your-key> \
.venv/bin/uvicorn mnemonic.api:app --host 0.0.0.0 --port 8010
```

**端口:** API `8010`, PostgreSQL `5434`

**环境变量:**

| 变量 | 说明 | 示例 |
|------|------|------|
| `MNEMONIC_DB_PASSWORD` | PG密码 (docker-compose中设为 `mnemonic_dev_password`) | `mnemonic_dev_password` |
| `MNEMONIC_LLM_API_KEY` | LLM端点API Key (Gemma-4) | — |
| `MNEMONIC_EMBEDDING_API_KEY` | Embedding API Key (SiliconFlow) | `sk-xxx...` |

## API 端点

命名空间通过 Header 传递：`X-Namespace: client_id:user_id:agent_id[:session_id]`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/memories` | 创建记忆 |
| GET | `/memories` | 列表查询 (limit/offset/type/importance) |
| GET | `/memories/{id}` | 获取单条 |
| PATCH | `/memories/{id}` | 更新 |
| DELETE | `/memories/{id}` | 软删除 |
| POST | `/memories/search` | 向量语义搜索 |
| POST | `/memories/extract` | LLM提取事实+自动存储 (冲突检测) |

## 技术栈

| 组件 | 选型 |
|------|------|
| API框架 | FastAPI (async) |
| ORM | SQLAlchemy 2.0 (async) |
| 数据库 | PostgreSQL 16 |
| 向量引擎 | pgvector |
|| LLM | Gemma-4 (自部署) |
|| Embedding | Qwen3-Embedding-8B via SiliconFlow |
| 向量维度 | **4096** |
| 容器 | Docker Compose |

## 向量索引

pgvector IVFFlat/HNSW 上限 2000 维，4096 维暂用精确搜索。
Phase 2 考虑降维投影或 Matryoshka 维度后再建索引。

## 项目结构

```
monic/
├── mnemonic/
│   ├── api.py          # FastAPI 端点
│   ├── store.py        # CRUD + 向量搜索
│   ├── services.py     # Embedding + LLM 提取
│   ├── models.py       # ORM 模型
│   ├── schemas.py      # Pydantic 模型
│   ├── config.py       # YAML 配置加载
│   ├── database.py     # DB 引擎
│   └── provider.py     # Hermes MemoryProvider 适配器
├── tests/
├── config.yaml
├── init.sql
├── docker-compose.yml
├── phase.md            # 开发进度与计划
└── .hermes.md          # Agent 项目说明
```

## 语义搜索验证

SiliconFlow + Qwen3-Embedding-8B 测试结果：

| 查询 | 命中文档 | cosine |
|------|----------|--------|
| "Hermes技术栈" | "Hermes Agent使用Python开发..." | **0.75** |
| "Hermes技术栈" | "Boss是Web3资深运营专家..." | 0.55 |
| "Solana链上运营" | "Boss是Web3资深运营专家..." | **0.73** |
| "Solana链上运营" | "用户偏好简洁回复..." | 0.47 |
| "今天晚饭吃什么" | (无强匹配) | <0.4 |

## 架构设计

详见飞书文档：https://feishu.cn/docx/NsN9dmczxol3i2xWZ3IcxBAZndg

详细进度见 [`phase.md`](phase.md)
