# MyStock - 我的股票

🚀 **MyStock** 是一个智能股票分析助手，提供实时行情、打板分析、股东动态监控、投资组合管理和 AI 智能对话功能。

![MyStock Screenshot](assets/screenshot.png)

## ✨ 功能特点

### 📊 实时行情
- 自动获取股票实时价格和涨跌幅
- 支持自选股管理
- 实时数据自动刷新

### 🚀 打板分析
- 追踪涨停板股票
- 识别首板机会
- 技术分析支持

### 💰 股东动态
- **股东增持**：监控大股东持股变动
- **回购概念**：追踪上市公司回购动态
- **高管增持**：关注高管持股变化

### 🤖 AI 智能助手
- AI 驱动的股票问答
- 投资策略建议
- 市场分析支持

### 📝 投资备忘
- 记录投资决策和分析
- 管理投资笔记
- 追踪研究过程

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Node.js 14+ (可选，用于前端开发)
- 网络连接（获取实时数据）

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/wangz/mystock.git
cd mystock
```

#### 2. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

主要依赖：
- fastapi
- uvicorn
- pandas
- pywencai
- requests

#### 3. 配置（可选）

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，添加你的 API Key（如果需要）
```

#### 4. 启动后端服务

```bash
# 方式一：使用启动脚本
chmod +x start.sh
./start.sh

# 方式二：直接运行
python main.py
```

后端服务将在 `http://localhost:8000` 启动

#### 5. 启动前端界面（可选）

```bash
cd ../frontend

# 方式一：使用 Python HTTP 服务器
python -m http.server 5000

# 方式二：使用 Node.js（如果你有 http-server）
npx http-server -p 5000

# 方式三：直接用浏览器打开 index.html
```

访问 `http://localhost:5000` 使用 Web 界面

## 📖 使用指南

### Web 界面使用

#### 1. 添加自选股

- 在搜索框输入股票代码或名称
- 点击添加按钮将股票加入自选

#### 2. 查看行情

- 自选股列表自动显示实时价格
- 涨跌幅用颜色区分（红色上涨，绿色下跌）
- 支持手动刷新和自动刷新

#### 3. 打板分析

- 点击"打板分析"标签
- 点击"刷新"获取最新涨停板数据
- 查看首板候选和涨停强度

#### 4. 股东动态

- 点击"股东动态"标签
- 切换查看不同类型：
  - 股东增持
  - 回购概念
  - 高管增持
- 点击"详情"查看完整列表

### API 使用

#### 获取股票报价

```bash
curl http://localhost:8000/api/stocks
```

#### 获取打板分析

```bash
curl http://localhost:8000/api/limit-up-analysis
```

#### 获取股东动态

```bash
curl http://localhost:8000/api/shareholder-activity
```

#### 获取投资组合

```bash
curl http://localhost:8000/api/portfolio
```

## 🔧 开发

### 项目结构

```
mystock/
├── backend/
│   ├── main.py              # FastAPI 主程序
│   ├── ai_service.py        # AI 服务
│   ├── ai_config.py         # AI 配置
│   ├── sync_all_stocks.py   # 股票数据同步
│   ├── requirements.txt     # Python 依赖
│   └── start.sh             # 启动脚本
├── frontend/
│   └── index.html           # Vue 3 单页应用
├── scripts/
│   └── check_api.py         # API 健康检查
├── .env.example             # 环境变量模板
├── .gitignore
├── README.md
└── LICENSE
```

### 后端开发

后端使用 FastAPI 框架，API 文档可通过以下地址访问：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 前端开发

前端是单文件 Vue 3 应用，无需额外构建步骤：

- 所有代码都在 `frontend/index.html` 中
- 使用 Element Plus UI 组件库
- 支持响应式设计

### 测试

```bash
# 运行 API 健康检查
python scripts/check_api.py

# 测试特定股票
curl "http://localhost:8000/api/stocks?code=600519.SH"
```

## ⚙️ 配置

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `AI_PROVIDER` | AI 服务提供商 | `silence` |
| `AI_API_KEY` | API Key | - |
| `AI_MODEL` | 模型名称 | `default` |

### 数据存储

- 投资组合：存储在 `portfolio_data.json`
- 股票代码：存储在 `stock_codes.json`
- 股票备忘：存储在 `memos.json`

## ⚠️ 免责声明

本工具仅供教育和研究目的。投资决策请谨慎，风险自担。过往表现不代表未来收益。

## 🐛 故障排除

### 后端无法启动

1. 检查端口是否被占用：
   ```bash
   lsof -i:8000
   ```

2. 重新安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 检查 Python 版本：
   ```bash
   python --version  # 需要 3.8+
   ```

### 数据不加载

1. 确认后端服务正在运行：
   ```bash
   curl http://localhost:8000/
   ```

2. 检查网络连接
3. 查看后端日志错误

### 前端显示异常

1. 确认 API 可访问
2. 检查浏览器控制台错误
3. 清除浏览器缓存

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [Vue.js](https://vuejs.org/) - 前端框架
- [Element Plus](https://element-plus.org/) - UI 组件库
- [FastAPI](https://fastapi.tiangolo.com/) - 后端框架
- [pywencai](https://github.com/mpjaqua/pywencai) - 问财数据查询

## 📞 联系

- GitHub Issues: https://github.com/wangz/mystock/issues
- Email: (请在 GitHub 上联系)

---

Made with ❤️ by [wangz](https://github.com/wangz)
