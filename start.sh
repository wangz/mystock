#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}  MyStock - 我的股票 FastAPI + Vue 应用启动器${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查后端是否已在运行
if curl -s http://127.0.0.1:8000/ > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  后端API已在运行 (http://127.0.0.1:8000)${NC}"
else
    echo -e "${GREEN}🚀 启动后端API...${NC}"
    cd backend
    python -m uvicorn main:app --reload --port 8000 &
    cd ..
    sleep 3
fi

echo ""
echo -e "${GREEN}✨ 启动完成！${NC}"
echo ""
echo -e "${BLUE}访问地址：${NC}"
echo -e "  前端: ${GREEN}http://localhost:8000${NC} (FastAPI文档)"
echo -e "  前端: ${GREEN}file://$(pwd)/frontend/index.html${NC} (Vue应用)"
echo ""
echo -e "${BLUE}API接口：${NC}"
echo -e "  GET  /api/portfolio     - 获取持仓数据"
echo -e "  GET  /api/watchlist     - 获取观察列表"
echo -e "  POST /api/chat           - 智能对话"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"
echo ""

# 等待
wait
