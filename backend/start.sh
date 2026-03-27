#!/bin/bash
# MyStock 我的股票 启动脚本

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
