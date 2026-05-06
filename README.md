# Hermes Mnemonic - AI Agent持久化记忆系统

基于mem0架构的多端共享记忆存储中间件，专为Hermes Agent设计。

## 安装

### 方式一：PyPI安装（推荐）

```bash
pip install hermes-mnemonic
```

Hermes Agent会自动发现Mnemonic插件，无需手动复制文件。

Hermes Agent会自动发现Mnemonic插件，无需手动复制文件。

### 方式二：从源码安装

```bash
git clone https://github.com/kopalam/Mnemonic.git
cd Mnemonic
pip install -e .
```

## 配置

### 1. 环境变量（推荐）

```bash
# Mnemonic API地址
export MNEMONIC_API_URL=http://localhost:8010

# 命名空间（用于多租户隔离）
export MNEMONIC_NAMESPACE=hermes:boss:hnoe:*
```

### 2. 配置文件

创建 `~/.hermes/mnemonic.json`：

```json
{
  "api_url": "http://localhost:8010",
  "namespace": "hermes:boss:hnoe:*"
}
```

### 3. Hermes配置

编辑 `~/.hermes/config.yaml`：

```yaml
memory:
  provider: mnemonic
  memory_enabled: true
```

## 部署Mnemonic API服务

### Docker部署（推荐）

```bash
# 克隆仓库
git clone https://github.com/kopalam/Mnemonic.git
cd Mnemonic

# 配置环境变量
cp .env.example .env
# 编辑.env填入API keys

# 启动服务
docker-compose up -d

# 检查状态
docker-compose logs -f mnemonic-api
```

### 手动部署

```bash
# 安装依赖
pip install mnemonic

# 启动API服务
mnemonic-api

# 或直接运行
python -m mnemonic.api
```

## 使用

安装后，Hermes Agent会自动使用Mnemonic作为记忆后端：

```python
# 在Hermes会话中
# 记忆会自动保存和检索
"记住我的名字是Boss"
"我的名字是什么？"  # 会从Mnemonic检索
```

## 功能特性

- ✅ **BM25关键词搜索** - 中文分词优化
- ✅ **向量搜索** - 支持SiliconFlow/OpenAI/本地模型
- ✅ **多租户隔离** - namespace隔离不同用户
- ✅ **Circuit Breaker** - 自动熔断保护
- ✅ **会话记忆** - 支持session_id关联
- ✅ **实体提取** - 自动提取关键信息（开发中）

## API文档

启动服务后访问：http://localhost:8010/docs

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码检查
ruff check mnemonic/
```

## License

MIT
