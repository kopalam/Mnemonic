# Mnemonic Memory Plugin

AI Agent 持久化记忆系统 - 基于 pgvector 的向量搜索 + 四级命名空间隔离

## 一键安装

```bash
# 方式1: curl 安装脚本
curl -sSL https://raw.githubusercontent.com/kopalam/Mnemonic/main/install.sh | bash

# 方式2: 指定安装目录
INSTALL_DIR=~/mnemonic curl -sSL https://raw.githubusercontent.com/kopalam/Mnemonic/main/install.sh | bash
```

## 手动安装

### 1. 前置要求

- PostgreSQL 14+ with pgvector extension
- Docker & docker-compose（可选，用于运行 API）
- SiliconFlow API Key（用于 embedding）

### 2. 克隆仓库

```bash
git clone https://github.com/kopalam/Mnemonic.git
cd Mnemonic
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入数据库连接信息
```

`.env` 配置项：

```bash
# Database
DB_HOST=your-postgres-host
DB_PORT=5432
DB_NAME=mnemonic
DB_USER=postgres
DB_PASSWORD=your-password

# API
API_PORT=8010

# Embedding (SiliconFlow)
EMBEDDING_PROVIDER=siliconflow
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
SILICONFLOW_API_KEY=your-api-key
```

### 4. 启动服务

```bash
docker-compose up -d
```

API 会自动：
- 创建 `vector` 和 `uuid-ossp` 扩展
- 创建 `memories`, `entities`, `memory_access_logs` 表
- 创建索引和触发器

### 5. 配置 Hermes

编辑 `~/.hermes/profiles/oper/config.yaml`:

```yaml
memory:
  provider: mnemonic
```

创建 `~/.hermes/profiles/oper/plugins/memory/mnemonic/config.json`:

```json
{
  "api_url": "http://localhost:8010",
  "namespace": "hermes:boss:hnoe:*"
}
```

## 验证安装

```bash
# 健康检查
curl http://localhost:8010/health
# {"status": "ok", "version": "0.2.0", "database": "connected"}

# 创建记忆
curl -X POST http://localhost:8010/memories \
  -H "Content-Type: application/json" \
  -H "X-Namespace: hermes:boss:hnoe:session1" \
  -d '{"content": "Hello Mnemonic!"}'

# 搜索记忆
curl -X POST http://localhost:8010/memories/search \
  -H "Content-Type: application/json" \
  -H "X-Namespace: hermes:boss:hnoe:*" \
  -d '{"query": "Hello", "limit": 5}'
```

## 特性

- ✅ **向量搜索**: pgvector 支持语义相似度检索
- ✅ **关键词搜索**: TSVector + jieba 中文分词
- ✅ **命名空间隔离**: client:user:agent:session 四级隔离
- ✅ **实体提取**: 自动提取并关联实体
- ✅ **访问日志**: 支持 WRRF 权重计算
- ✅ **自动初始化**: 启动时自动创建表结构

## 架构

```
┌─────────────────┐
│  Hermes Agent   │
└────────┬────────┘
         │ mnemonic plugin
         ▼
┌─────────────────┐
│  Mnemonic API   │ :8010
│  (FastAPI)      │
└────────┬────────┘
         │ SQLAlchemy
         ▼
┌─────────────────┐
│  PostgreSQL     │
│  + pgvector     │
└─────────────────┘
```

## 数据库 Schema

### memories 表

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| client_id | VARCHAR(255) | 客户端 ID |
| user_id | VARCHAR(255) | 用户 ID |
| agent_id | VARCHAR(255) | Agent ID |
| session_id | VARCHAR(255) | 会话 ID |
| content | TEXT | 记忆内容 |
| content_hash | VARCHAR(32) | MD5 去重 |
| embedding | vector(1024) | 向量嵌入 |
| content_tokens | TSVECTOR | 中文分词 tokens |
| memory_type | VARCHAR(50) | fact/event/preference |
| importance | FLOAT | 重要性权重 |
| created_at | TIMESTAMPTZ | 创建时间 |
| deleted_at | TIMESTAMPTZ | 软删除 |

## 开发

```bash
# 本地开发
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 运行测试
pytest

# 启动开发服务器
uvicorn mnemonic.api:app --reload --port 8010
```

## License

MIT