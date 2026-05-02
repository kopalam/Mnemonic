# Mnemonic

AI Agent 持久化记忆存储中间件，为 Hermes / OpenClaw 等多 Agent 框架提供长期记忆能力。

## 核心定位

Mnemonic 不是聊天记录存储，而是**从对话中提取有价值事实**的知识库。

### 存什么

从用户对话中提取的关键信息：

```text
对话: "我不喜欢太长的报告，给我bullet points就行"
↓ LLM 提取
Mnemonic: "Boss偏好简洁报告，格式用bullet points"
```

```text
对话: "zSunKoin用CCXT拉数据，15分钟周期"
↓ LLM 提取
Mnemonic: "zSunKoin项目：CCXT获取K线，15分钟周期"
```

### 不存什么

- AI 回答（可重新生成，不是知识）
- 完整对话原文（那是 Session History，Hermes 已有 session_search）
- 闲聊废话（"哈哈哈"、"中午吃什么"）

### 实际场景

**没有 Mnemonic：**
```text
会话1: "我是做Solana运营的"
会话2: （新会话）AI 不知道你是谁，重新问
```

**有 Mnemonic：**
```text
会话1: "我是做Solana运营的" → 存入记忆
会话2: AI 自动召回 "Boss是Web3运营专家，主攻Solana"
```

## 快速开始

### 1. 克隆仓库

```bash
git clone git@github.com:kopalam/Mnemonic.git
cd Mnemonic
```

### 2. 安装依赖

```bash
uv sync
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入你的 API Keys
```

环境变量说明：

| 变量 | 说明 |
|------|------|
| `MNEMONIC_DB_PASSWORD` | PostgreSQL 密码 |
| `MNEMONIC_LLM_API_KEY` | LLM API Key（Gemma-4 或兼容 OpenAI API 的服务） |
| `MNEMONIC_LLM_FALLBACK_API_KEY` | LLM 降级备用 Key（可选） |
| `MNEMONIC_EMBEDDING_API_KEY` | Embedding API Key |

### 4. 启动服务

```bash
# 启动 PostgreSQL (Docker)
docker compose up -d

# 启动 API 服务
.venv/bin/uvicorn mnemonic.api:app --host 0.0.0.0 --port 8010
```

**端口：** API `8010`，PostgreSQL `5434`

## API 端点

命名空间通过 Header 传递：`X-Namespace: client_id:user_id:agent_id[:session_id]`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/memories` | 创建记忆 |
| GET | `/memories` | 列表查询 |
| GET | `/memories/{id}` | 获取单条 |
| PATCH | `/memories/{id}` | 更新 |
| DELETE | `/memories/{id}` | 软删除 |
| POST | `/memories/search` | 向量语义搜索 |
| POST | `/memories/extract` | LLM 提取事实 + 自动存储 |

## 技术栈

| 组件 | 选型 |
|------|------|
| API 框架 | FastAPI (async) |
| ORM | SQLAlchemy 2.0 (async) |
| 数据库 | PostgreSQL 16 |
| 向量引擎 | pgvector |
| LLM | Gemma-4（自部署） |
| Embedding | Qwen3-Embedding-8B |
| 向量维度 | 4096 |
| 容器 | Docker Compose |

## 四维评估体系 (D1-D4)

用于验证记忆系统的核心能力。

### D1: Extraction（提取能力）

输入对话，验证 LLM 能否提取关键事实。

```text
输入: "我今天用Solana的Raydium做了一个SOL-USDC的swap，滑点设的1%"
期望提取: ["Raydium", "SOL-USDC", "滑点", "gas"]
```

### D2: Recency（时效性/冲突解决）

旧信息被新信息覆盖，搜索时返回最新值。

```text
写入旧: "Mnemonic系统的API端口是8000"
写入新: "Mnemonic系统的API端口已改为8010"
查询: "API端口"
期望: 返回 8010，不返回 8000
```

### D3: Robustness（噪声过滤）

对话中夹杂废话/闲聊，验证系统只存有价值信息。

```text
输入: "哈哈哈笑死我了。Boss要求TG Bot用Markdown格式。中午吃什么好呢。"
期望: 只提取 "TG Bot Markdown"，不存 "哈哈哈"、"中午吃"
```

### D4: Relevance（搜索相关性）

验证搜索能否精准召回相关记忆。

**指标：**
- **L1 (TOP-1)**: 搜索结果第一条是否命中正确答案
- **L3 (MRR)**: 平均倒数排名，衡量整体召回质量

```text
查询: "Boss是做什么的"
期望 TOP-1: "Boss是Web3资深运营专家，主攻Solana生态"
```

**当前状态：** D1-D3 已达标，D4 因数据量少（25 条记忆）暂未达标。

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
├── config.yaml
├── init.sql
├── docker-compose.yml
└── .env.example
```

## 向量索引

pgvector IVFFlat/HNSW 上限 2000 维，4096 维暂用精确搜索。

Phase 2 考虑降维投影或 Matryoshka 维度后再建索引。

## License

MIT
