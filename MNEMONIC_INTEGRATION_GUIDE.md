# Mnemonic 接入指南

Mnemonic 是自托管的 AI Agent 记忆系统，支持 BM25 关键词搜索和向量搜索，自动去重与合并记忆。

## 前置条件

- Docker & Docker Compose
- Hermes Agent 已安装
- PostgreSQL 客户端（可选，用于调试）

---

## 第一步：部署 Mnemonic 后端

### 1. 克隆项目

```bash
cd ~/Documents
git clone https://github.com/your-org/mnemonic.git
cd mnemonic
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# LLM 配置（用于记忆提取和去重）
MNEMONIC_LLM_API_KEY=your_llm_api_key
MNEMONIC_LLM_FALLBACK_API_KEY=your_fallback_key  # 可选
MNEMONIC_LLM_BASE_URL=https://api.example.com/v1  # 可选

# Embedding 配置（用于向量搜索）
MNEMONIC_EMBEDDING_API_KEY=your_embedding_api_key
MNEMONIC_EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1  # 推荐 SiliconFlow

# 数据库配置
MNEMONIC_DB_PASSWORD=your_secure_password
```

### 3. 启动服务

```bash
docker compose up -d
```

### 4. 验证服务

```bash
curl http://localhost:8010/health
# 应返回: {"status":"ok","version":"0.1.0","database":"connected"}
```

---

## 第二步：安装 Hermes 插件

### 1. 复制插件到 Hermes

```bash
# 插件已在 ~/.hermes/hermes-agent/plugins/memory/mnemonic/
# 如果是从源码安装：
cp -r /path/to/mnemonic/hermes-plugin ~/.hermes/hermes-agent/plugins/memory/mnemonic/
```

### 2. 创建配置文件

在 `$HERMES_HOME` 目录创建 `mnemonic.json`：

```bash
cat > ~/.hermes/profiles/oper/mnemonic.json << 'EOF'
{
  "api_url": "http://localhost:8010",
  "namespace": "hermes:boss:hnoe:*"
}
EOF
```

**参数说明**：
- `api_url`: Mnemonic API 地址
- `namespace`: 记忆命名空间，格式 `client_id:user_id:agent_id:session_id`
  - 使用 `*` 通配所有 session，例如 `hermes:boss:hnoe:*`

---

## 第三步：激活插件

### 修改 Hermes 配置

编辑 `~/.hermes/profiles/oper/config.yaml`：

```yaml
memory:
  memory_enabled: true
  user_profile_enabled: true
  memory_char_limit: 2200
  user_char_limit: 1375
  provider: mnemonic  # 设置为 mnemonic
```

---

## 第四步：验证接入

### 1. 重启 Hermes

```bash
# 如果 Hermes 正在运行
hermes restart

# 或启动新的 Hermes 会话
hermes
```

### 2. 测试记忆搜索

在 Hermes 对话中：

```
你: 帮我回忆一下 zSunKoin 项目的架构
Hermes: [自动从 Mnemonic 搜索并返回相关记忆]
```

### 3. 测试记忆存储

```
你: 记住，我要求所有回复都要简洁
Hermes: [自动提取并存储到 Mnemonic]
```

---

## 工作原理

### 自动注入（Prefetch）

每次用户发送消息时，Mnemonic 会：
1. 用用户消息作为查询词搜索记忆
2. 将 Top 3 相关记忆注入到 context
3. Agent 基于历史记忆生成回复

```
用户消息: "ATR 止损参数怎么调整"
    ↓
Mnemonic Search → "zSunKoin 项目中，SOL 止损设置为 1.5x-2.5x ATR"
    ↓
注入到 Context → Agent 获得历史记忆
    ↓
Agent 回复: "根据你的 zSunKoin 项目，SOL 止损当前是 1.5x-2.5x ATR..."
```

### 自动存储（Sync Turn）

每次对话结束后，Mnemonic 会：
1. 提取用户消息中的事实
2. LLM 判断：ADD（新增）、UPDATE（更新）、DELETE（删除）、NONE（重复）
3. 自动去重和合并

```
用户消息: "把 SOL 止损改成 3x ATR"
    ↓
Mnemonic Extract → LLM 提取事实
    ↓
判断: UPDATE（更新现有记忆）
    ↓
下次搜索 → 返回更新后的记忆
```

---

## 高级配置

### 环境变量

```bash
# 覆盖 mnemonic.json 配置
export MNEMONIC_API_URL="http://localhost:8010"
export MNEMONIC_NAMESPACE="hermes:boss:hnoe:*"
```

### 多用户隔离

不同用户使用不同的 namespace：

```json
{
  "api_url": "http://localhost:8010",
  "namespace": "hermes:${user_id}:hnoe:*"
}
```

### 禁用自动存储

如果只想使用搜索功能，可以在插件中注释掉 `sync_turn()` 方法。

---

## 故障排查

### 1. Mnemonic API 无法访问

```bash
# 检查服务状态
docker compose ps

# 查看日志
docker compose logs mnemonic-api

# 重启服务
docker compose restart mnemonic-api
```

### 2. 搜索返回空结果

```bash
# 检查数据库中的记忆
docker exec mnemonic-postgres psql -U mnemonic -d mnemonic -c "SELECT COUNT(*) FROM memories WHERE deleted_at IS NULL"

# 检查 content_tokens 是否正确
docker exec mnemonic-postgres psql -U mnemonic -d mnemonic -c "SELECT content_tokens FROM memories LIMIT 1"
```

### 3. Circuit Breaker 触发

如果 Mnemonic 连续失败 5 次，插件会自动禁用 120 秒。

检查日志：
```bash
tail -f ~/.hermes/logs/agent.log | grep Mnemonic
```

---

## 性能指标

| 指标 | 数值 |
|------|------|
| 记忆数量 | 17 条（合并后） |
| Keyword L1 准确率 | 100%（18/18 测试查询） |
| 搜索延迟 | 100-300ms |
| 自动去重 | 支持（LLM 三阶段） |
| 记忆合并 | 支持（同实体合并） |

---

## 与 Built-in Memory 的关系

Mnemonic **不会替换** Hermes 的内置记忆（MEMORY.md / USER.md），而是**并行运行**：

- **Built-in Memory**: 结构化存储，全量注入，适合精确配置
- **Mnemonic**: 语义存储，按需搜索，适合长尾记忆

两者互补，不冲突。

---

## 下一步

- [ ] 添加更多记忆（通过对话自然积累）
- [ ] 优化 Vector 搜索质量
- [ ] 配置 Entity Boost（提升特定实体的排名）
- [ ] 监控 Mnemonic API 健康状态

---

## 支持

- 项目地址: `/Users/kopa/Documents/monic`
- 插件地址: `~/.hermes/hermes-agent/plugins/memory/mnemonic/`
- 问题反馈: 联系 HNOE
