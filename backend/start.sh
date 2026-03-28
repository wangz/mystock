#!/bin/bash
# MyStock 我的股票 启动脚本

# 设置 Node.js 全局模块路径（pywencai 依赖 jsdom）
export NODE_PATH=$(npm root -g 2>/dev/null)
if [ -n "$NODE_PATH" ]; then
    echo "✅ Node.js 模块路径: $NODE_PATH"
else
    echo "⚠️  未找到 Node.js，请运行: npm install -g jsdom"
fi

# 加载 .env 文件（如果存在）
if [ -f .env ]; then
    echo "加载环境变量配置..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# 显示当前 AI 配置
echo "=========================================="
echo "AI 服务配置："
echo "  Provider: ${AI_PROVIDER:-silence (默认)}"
echo "  API Key:  ${AI_API_KEY:+已配置}"
echo "  Model:    ${AI_MODEL:-默认}"
echo "=========================================="
echo ""

# 启动服务
echo "启动 MyStock 后端服务..."
python main.py
