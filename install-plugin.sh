#!/bin/bash
# Mnemonic Hermes Plugin Installer
# 一键安装Mnemonic记忆插件到Hermes

set -e

echo "══════════════════════════════════════════════"
echo "  Mnemonic Hermes Plugin Installer"
echo "══════════════════════════════════════════════"
echo ""

# 配置
PLUGIN_DIR="$HOME/.hermes/plugins/memory/mnemonic"
GITHUB_RAW="https://raw.githubusercontent.com/kopalam/Mnemonic/main/plugins/mnemonic"

# 1. 创建目录
echo "[1/5] 创建插件目录..."
mkdir -p "$PLUGIN_DIR"

# 2. 下载插件文件
echo "[2/5] 下载插件文件..."
cd "$PLUGIN_DIR"

echo "  - 下载 __init__.py"
curl -fsSL "$GITHUB_RAW/__init__.py" -o __init__.py

echo "  - 下载 plugin.yaml"
curl -fsSL "$GITHUB_RAW/plugin.yaml" -o plugin.yaml

echo "  - 下载 README.md"
curl -fsSL "$GITHUB_RAW/README.md" -o README.md

# 3. 配置mnemonic.json（如果不存在）
echo "[3/5] 配置Mnemonic API地址..."
MNEMONIC_CONFIG="$HOME/.hermes/mnemonic.json"

if [ ! -f "$MNEMONIC_CONFIG" ]; then
    # 提示用户输入API地址
    echo ""
    echo "请输入Mnemonic API地址（默认: http://localhost:8010）："
    read -r API_URL
    API_URL=${API_URL:-http://localhost:8010}
    
    echo "请输入Namespace（默认: hermes:boss:hnoe:*）："
    read -r NAMESPACE
    NAMESPACE=${NAMESPACE:-hermes:boss:hnoe:*}
    
    cat > "$MNEMONIC_CONFIG" <<EOF
{
  "api_url": "$API_URL",
  "namespace": "$NAMESPACE"
}
EOF
    echo "  ✓ 已创建 $MNEMONIC_CONFIG"
else
    echo "  ✓ 配置文件已存在: $MNEMONIC_CONFIG"
fi

# 4. 配置Hermes
echo "[4/5] 配置Hermes..."
if command -v hermes &> /dev/null; then
    hermes config set memory.provider mnemonic 2>/dev/null || true
    hermes config set memory.memory_enabled true 2>/dev/null || true
    hermes plugins enable mnemonic 2>/dev/null || true
    echo "  ✓ 已配置 memory.provider=mnemonic"
    echo "  ✓ 已启用 mnemonic 插件"
else
    echo "  ! hermes命令未找到，请手动配置config.yaml"
fi

# 5. 验证安装
echo "[5/5] 验证安装..."
if command -v hermes &> /dev/null; then
    echo ""
    hermes memory status
    echo ""
else
    echo "  请手动运行: hermes memory status"
fi

# 完成
echo "══════════════════════════════════════════════"
echo "  安装完成！"
echo "══════════════════════════════════════════════"
echo ""
echo "插件目录: $PLUGIN_DIR"
echo "配置文件: $MNEMONIC_CONFIG"
echo ""
echo "下一步："
echo "  1. 确保Mnemonic API服务已启动"
echo "  2. 测试记忆功能: hermes chat"
echo ""
