#!/bin/bash
# Mnemonic Hermes Plugin Installer
# 一键安装Mnemonic记忆插件到Hermes

set -e

echo "══════════════════════════════════════════════"
echo "  Mnemonic Hermes Plugin Installer"
echo "══════════════════════════════════════════════"
echo ""

# 配置
PLUGIN_DIR="$HOME/.hermes/plugins/mnemonic"
GITHUB_RAW="https://raw.githubusercontent.com/kopalam/Mnemonic/main/plugins/mnemonic"

# 生成随机namespace的函数
generate_random_namespace() {
    local random_suffix=$(cat /dev/urandom | tr -dc 'a-z0-9' | fold -w 8 | head -n 1)
    echo "hermes:user:${random_suffix}"
}

# 1. 安装Python包
echo "[1/7] 安装 hermes-mnemonic Python包..."
PIP_INSTALLED=false

if command -v pip &> /dev/null; then
    if pip install hermes-mnemonic 2>&1 | tee /tmp/pip_install.log && grep -q "Successfully installed hermes-mnemonic" /tmp/pip_install.log || pip show hermes-mnemonic > /dev/null 2>&1; then
        echo "  ✓ 已安装 hermes-mnemonic"
        PIP_INSTALLED=true
    else
        echo "  ✗ pip安装失败"
    fi
elif command -v pip3 &> /dev/null; then
    if pip3 install hermes-mnemonic 2>&1 | tee /tmp/pip_install.log && grep -q "Successfully installed hermes-mnemonic" /tmp/pip_install.log || pip3 show hermes-mnemonic > /dev/null 2>&1; then
        echo "  ✓ 已安装 hermes-mnemonic"
        PIP_INSTALLED=true
    else
        echo "  ✗ pip3安装失败"
    fi
else
    echo "  ✗ pip/pip3 未找到"
fi

if [ "$PIP_INSTALLED" = false ]; then
    echo ""
    echo "  警告: Python包安装失败，但将继续安装插件文件"
    echo ""
fi

# 2. 创建目录
echo "[2/7] 创建插件目录..."
mkdir -p "$PLUGIN_DIR"

# 3. 下载插件文件
echo "[3/7] 下载插件文件..."
cd "$PLUGIN_DIR"

echo "  - 下载 __init__.py"
curl -fsSL "$GITHUB_RAW/__init__.py" -o __init__.py

echo "  - 下载 plugin.yaml"
curl -fsSL "$GITHUB_RAW/plugin.yaml" -o plugin.yaml

echo "  - 下载 README.md"
curl -fsSL "$GITHUB_RAW/README.md" -o README.md

# 4. 配置mnemonic.json（如果不存在）
echo "[4/7] 配置Mnemonic API地址..."
MNEMONIC_CONFIG="$HOME/.hermes/mnemonic.json"

if [ ! -f "$MNEMONIC_CONFIG" ]; then
    # 提示用户输入API地址
    echo ""
    echo "请输入Mnemonic API地址（默认: http://localhost:8010）："
    read -r API_URL
    API_URL=${API_URL:-http://localhost:8010}
    
    # 自动生成随机namespace
    NAMESPACE=$(generate_random_namespace)
    echo ""
    echo "已自动生成Namespace: $NAMESPACE"
    echo "（用于隔离不同用户的记忆数据）"
    
    cat > "$MNEMONIC_CONFIG" <<EOF
{
  "api_url": "$API_URL",
  "namespace": "$NAMESPACE"
}
EOF
    echo ""
    echo "  ✓ 已创建 $MNEMONIC_CONFIG"
else
    echo "  ✓ 配置文件已存在: $MNEMONIC_CONFIG"
    # 读取现有配置的API地址
    API_URL=$(grep -o '"api_url"[[:space:]]*:[[:space:]]*"[^"]*"' "$MNEMONIC_CONFIG" | cut -d'"' -f4)
    NAMESPACE=$(grep -o '"namespace"[[:space:]]*:[[:space:]]*"[^"]*"' "$MNEMONIC_CONFIG" | cut -d'"' -f4)
    echo "  当前Namespace: $NAMESPACE"
fi

# 5. 配置Hermes
echo "[5/7] 配置Hermes..."
if command -v hermes &> /dev/null; then
    # 设置memory provider
    hermes config set memory.provider mnemonic
    echo "  ✓ 已设置 memory.provider=mnemonic"
    
    # 启用memory
    hermes config set memory.memory_enabled true
    echo "  ✓ 已设置 memory.memory_enabled=true"
    
    # 启用插件
    hermes plugins enable mnemonic
    echo "  ✓ 已执行 hermes plugins enable mnemonic"
else
    echo "  ✗ hermes命令未找到，请手动配置config.yaml"
fi

# 6. 检查服务端连通性
echo "[6/7] 检查Mnemonic API服务连通性..."

if [ -n "$API_URL" ]; then
    # 尝试访问health endpoint
    HEALTH_URL="$API_URL/health"
    
    if curl -fsSL --max-time 5 "$HEALTH_URL" > /dev/null 2>&1; then
        echo "  ✓ Mnemonic API服务可达: $API_URL"
    else
        echo "  ✗ Mnemonic API服务不可达: $API_URL"
        echo ""
        echo "  请确保Mnemonic API服务已启动："
        echo "    - 检查服务状态: curl $HEALTH_URL"
        echo "    - 启动服务: cd ~/Mnemonic && docker-compose up -d"
        echo "    - 查看日志: docker-compose logs -f mnemonic-api"
        echo ""
    fi
else
    echo "  ! 未找到API地址配置，跳过连通性检查"
fi

# 7. 验证安装
echo "[7/7] 验证安装..."
if command -v hermes &> /dev/null; then
    echo ""
    echo "Memory status:"
    hermes memory status
    echo ""
    echo "Plugins list:"
    hermes plugins list | grep -A1 mnemonic || echo "  mnemonic插件状态未知"
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
echo "Namespace: $NAMESPACE"
echo "Python包: $([ "$PIP_INSTALLED" = true ] && echo "已安装" || echo "未安装")"
echo ""
echo "下一步："
echo "  1. 确保Mnemonic API服务已启动并可达"
echo "  2. 测试记忆功能: hermes chat"
echo ""
