# MyStock - 我的股票

一个基于 Vue 3 和 FastAPI 的智能股票分析助手，提供实时行情、打板分析、股东动态监控等功能。

## 🎯 功能特点

- 📊 **实时行情**：监控股票实时价格和涨跌幅
- 🚀 **打板分析**：分析涨停板股票，追踪首板机会
- 💰 **股东动态**：监控股东增持、回购概念、高管增持等数据
- 🤖 **智能对话**：AI 驱动的股票问答和分析
- 📝 **股票备忘**：记录和管理投资笔记

## 🛠️ 技术栈

### 前端
- Vue 3 (Composition API)
- Element Plus UI
- 响应式设计

### 后端
- Python 3
- FastAPI
- Pandas 数据处理
- pywencai 问财数据查询

## 🚀 快速开始

### 后端启动

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 前端启动

```bash
cd frontend
# 使用任意静态服务器启动
# 例如：python -m http.server 5000
```

### 访问应用

打开浏览器访问：`http://localhost:5000`

## 📁 项目结构

```
ai-stock/
├── backend/
│   ├── main.py          # FastAPI 主程序
│   └── requirements.txt # Python 依赖
├── frontend/
│   └── index.html       # Vue 3 单页应用
├── .gitignore
└── README.md
```

## ⚙️ 配置

后端 API 地址在 `frontend/index.html` 中定义：

```javascript
const API_BASE = 'http://localhost:8000';
```

## 📝 使用说明

1. **添加自选股**：在搜索框中输入股票代码或名称
2. **查看行情**：自动获取股票实时价格
3. **打板分析**：点击"刷新"获取最新打板数据
4. **股东动态**：查看股东增持、回购概念、高管增持信息
5. **智能对话**：与 AI 助手交流股票问题

## 🔧 开发

### 前端开发

前端代码在 `frontend/index.html` 中，采用单文件组件形式，包含所有 Vue 逻辑和样式。

### 后端开发

后端 API 在 `backend/main.py` 中，使用 FastAPI 框架构建。

## 📄 License

MIT License
