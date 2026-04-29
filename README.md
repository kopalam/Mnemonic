# Mnemonic

独立部署的 AI Agent 持久化记忆存储中间件，服务 Hermes / OpenClaw 等多 Agent 框架。

## 架构设计

详见飞书文档：https://feishu.cn/docx/NsN9dmczxol3i2xWZ3IcxBAZndg

## Phase 1 目标

- [x] FastAPI 骨架
- [ ] PostgreSQL Schema + pgvector
- [ ] POST /memories (添加记忆)
- [ ] GET /memories (检索记忆)
- [ ] DELETE /memories/{id} (删除记忆)

## 快速开始

```bash
# 安装依赖
uv sync

# 启动 PostgreSQL (Docker)
docker-compose up -d

# 运行服务
uv run uvicorn mnemonic.api:app --reload
```

## 命名空间隔离

四级命名空间：`client_id / user_id / agent_id / session_id`

所有 API 请求必须携带 `X-Namespace` header：
```
X-Namespace: client123:user456:agent789:session0
```
