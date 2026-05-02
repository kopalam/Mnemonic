# Mnemonic 快速开始

## 1. 启动 Mnemonic 后端

```bash
cd ~/Documents/monic
docker compose up -d
```

验证：
```bash
curl http://localhost:8010/health
```

## 2. 配置 Hermes

创建 `~/.hermes/profiles/oper/mnemonic.json`：
```json
{
  "api_url": "http://localhost:8010",
  "namespace": "hermes:boss:hnoe:*"
}
```

修改 `~/.hermes/profiles/oper/config.yaml`：
```yaml
memory:
  provider: mnemonic
```

## 3. 重启 Hermes

```bash
hermes restart
```

## 4. 测试

```
你: 帮我回忆一下 zSunKoin 项目
Hermes: [自动返回相关记忆]
```

---

**完成！** Mnemonic 已接入 Hermes。

详细文档见: [MNEMONIC_INTEGRATION_GUIDE.md](./MNEMONIC_INTEGRATION_GUIDE.md)
