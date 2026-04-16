# 股票K线图实现计划

## 一、项目现状分析

### 1.1 现有功能
- ✅ 后端已实现 `/api/stock-detail/{code}` 接口，返回股票基本信息和ROE数据
- ✅ 前端已集成 ECharts 5.4.3 图表库
- ✅ 前端已有股票详情页面和图表容器 (`stock-detail-chart`)
- ✅ 项目已使用 akshare 和 baostock 库获取股票数据

### 1.2 缺失功能
- ❌ 后端缺少 K 线数据 API
- ❌ 前端缺少 K 线图表显示
- ❌ 缺少 K 线数据获取和处理逻辑

## 二、K线数据来源验证

### 2.1 已测试的数据来源

| 数据来源 | 状态 | 说明 |
|---------|------|------|
| **腾讯API (推荐)** | ✅ 可用 | web.ifzq.gtimg.cn/appstock/app/fqkline/get |
| **BaoStock** | ✅ 可用 | 免费，数据稳定 |
| **akshare** | ❌ 网络问题 | 连接不稳定 |

### 2.2 选定的数据来源
**腾讯K线API**：
- ✅ API已验证可用
- ✅ 数据格式完美适配ECharts
- ✅ 支持前复权数据
- ✅ 支持日K、周K、月K
- ✅ 无需注册，免费使用
- ✅ 已在项目中使用腾讯API，集成方便

## 三、实现方案

### 3.1 后端实现

#### 3.1.1 K线数据API
**文件**：`backend/main.py`

**API 端点**：
- `GET /api/stock-kline/{code}` - 获取股票K线数据（默认日K，近30天）
- `GET /api/stock-kline/{code}?period=day&count=30` - 日K数据
- `GET /api/stock-kline/{code}?period=week&count=20` - 周K数据
- `GET /api/stock-kline/{code}?period=month&count=12` - 月K数据

**API URL格式**：
```
GET https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayqfq&param={code},{period},,,{count},qfq
```

**后端返回数据结构**：
```json
{
  "code": "600519",
  "name": "贵州茅台",
  "period": "day",
  "data": [
    {
      "date": "2026-04-01",
      "open": 1464.49,
      "close": 1459.44,
      "high": 1469.99,
      "low": 1452.88,
      "volume": 29125.00
    }
  ],
  "count": 30
}
```

#### 3.1.2 缓存策略
- 日K数据：缓存1小时
- 周K/月K数据：缓存6小时
- 使用现有缓存机制

### 3.2 前端实现

#### 3.2.1 修改股票详情页面
**文件**：`frontend/index.html`

**修改内容**：
1. 在股票详情区域添加K线图表容器
2. 添加周期选择按钮（日K/周K/月K）
3. 调用K线API获取数据
4. 使用ECharts绘制K线图

#### 3.2.2 ECharts配置
```javascript
option = {
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'cross' }
  },
  grid: [
    { left: '10%', right: '8%', top: '10%', height: '60%' },
    { left: '10%', right: '8%', top: '75%', height: '15%' }
  ],
  xAxis: [
    { type: 'category', data: dates, gridIndex: 0 },
    { type: 'category', data: dates, gridIndex: 1 }
  ],
  yAxis: [
    { scale: true, gridIndex: 0 },
    { scale: true, gridIndex: 1 }
  ],
  series: [
    {
      name: 'K线',
      type: 'candlestick',
      data: klineData,  // [open, close, low, high]
      xAxisIndex: 0,
      yAxisIndex: 0
    },
    {
      name: '成交量',
      type: 'bar',
      data: volumeData,
      xAxisIndex: 1,
      yAxisIndex: 1
    }
  ]
}
```

## 四、具体实施步骤

### 步骤1：后端添加K线数据API
1. 在 `main.py` 中添加 `get_stock_kline` 函数
2. 调用腾讯K线API获取数据
3. 处理数据格式（字符串转数值）
4. 添加缓存机制
5. 测试API响应

**关键代码片段**：
```python
@app.get("/api/stock-kline/{code}")
def get_stock_kline(code: str, period: str = "day", count: int = 30):
    """获取股票K线数据"""
    # 1. 检查缓存
    cache_key = f'kline_{code}_{period}_{count}'
    cached = get_cache(cache_key, 'kline')
    if cached:
        return cached
    
    # 2. 构建腾讯API URL
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    params = {
        '_var': f'kline_{period}qfq',
        'param': f'{code},{period},,,{count},qfq'
    }
    
    # 3. 调用API
    response = requests.get(url, params=params, timeout=5)
    
    # 4. 解析数据
    text = response.text
    if '=' in text:
        data_str = text.split('=', 1)[1]
        data = json.loads(data_str)
        
        if data['code'] == 0 and code in data['data']:
            kline_data = data['data'][code].get(f'qfq{period}', data['data'][code].get(period, []))
            
            # 5. 转换格式
            result = {
                'code': code,
                'period': period,
                'data': [
                    {
                        'date': item[0],
                        'open': float(item[1]),
                        'close': float(item[2]),
                        'high': float(item[3]),
                        'low': float(item[4]),
                        'volume': float(item[5])
                    }
                    for item in kline_data
                ],
                'count': len(kline_data)
            }
            
            # 6. 保存缓存
            set_cache(cache_key, 'kline', result, CACHE_DURATION_SHORT)
            
            return result
    
    return {'error': '获取K线数据失败'}
```

### 步骤2：前端添加K线图表
1. 在股票详情页面添加K线图表容器
2. 添加周期选择按钮
3. 实现K线数据获取函数
4. 配置ECharts K线图表
5. 测试图表显示

**关键代码片段**：
```javascript
async function loadStockKline(code) {
  const period = document.querySelector('.kline-period.active')?.dataset.period || 'day';
  const response = await fetch(`${API_BASE}/api/stock-kline/${code}?period=${period}&count=30`);
  const data = await response.json();
  
  if (data.error) {
    console.error('K线数据加载失败:', data.error);
    return;
  }
  
  // 准备图表数据
  const dates = data.data.map(d => d.date);
  const klineData = data.data.map(d => [d.open, d.close, d.low, d.high]);
  const volumeData = data.data.map(d => d.volume);
  
  // 初始化图表
  const chartDom = document.getElementById('kline-chart');
  const chart = echarts.init(chartDom);
  
  const option = {
    // ECharts配置...
  };
  
  chart.setOption(option);
}
```

### 步骤3：集成和测试
1. 测试不同股票代码
2. 测试不同周期的数据
3. 优化图表性能
4. 确保响应式显示

## 五、预期效果

### 5.1 功能效果
- ✅ 股票详情页面显示K线图
- ✅ 支持日K、周K、月K切换
- ✅ 显示成交量柱状图
- ✅ 支持图表缩放和数据提示
- ✅ 响应式布局

### 5.2 性能要求
- 首次加载K线数据 < 2秒
- 切换周期 < 1秒
- 图表缩放流畅

## 六、风险评估

### 6.1 潜在风险
- 腾讯API可能随时变更或失效
- 网络问题导致数据获取失败
- 大量数据可能影响前端性能

### 6.2 风险对策
- 添加错误处理和重试机制（最多重试3次）
- 实现数据分批加载
- 优化图表渲染性能（限制数据量）
- 预留BaoStock作为备用数据源

## 七、所需资源

### 7.1 依赖库
- ✅ requests (标准库)
- ✅ ECharts (已集成)
- ✅ 现有缓存机制

### 7.2 开发时间
- 后端API：20分钟
- 前端实现：40分钟
- 测试和优化：20分钟

## 八、测试计划

### 8.1 测试用例
1. ✅ 测试茅台（sh600519）的日K数据
2. 测试不同周期（day/week/month）
3. 测试不同股票代码
4. 测试图表交互
5. 测试响应式布局

### 8.2 验证方法
- API响应测试（curl或浏览器）
- 图表显示测试
- 数据准确性验证

## 九、结论

**腾讯K线API验证成功！** 可以使用该API快速实现K线图功能。该API：
- ✅ 数据格式完美
- ✅ 响应速度快
- ✅ 免费无需注册
- ✅ 已验证可用

建议优先使用腾讯K线API，同时预留BaoStock作为备用方案。