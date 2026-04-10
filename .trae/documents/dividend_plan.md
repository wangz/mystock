# 股票详情页加入分红情况 - 实现计划

## 📋 需求概述
在股票详情页中添加近10年分红情况的展示，包含图表和明细表格，并计算对应除权日的股息率

## 🔍 研究结论

### 数据源
**akshare** - 免费、快速、数据完整

### 分红数据结构
```python
ak.stock_history_dividend_detail(symbol='600519')
```
| 字段 | 说明 | 示例 |
|------|------|------|
| 公告日期 | 分红公告时间 | 2024-12-14 |
| 派息 | 每股分红(元) | 238.82 |
| 进度 | 预案/实施 | 实施 |
| 除权除息日 | 分红到账日 | 2024-12-20 |

### 历史股价
```python
ak.stock_zh_a_hist(symbol='601766', period='daily', start_date='20240801', end_date='20240815')
```

### 派息率计算
```
派息率 = 每股分红 ÷ 除权除息日收盘价 × 100%
```

## 📊 图表展示方案

### 方案1：柱状图 + 折线图组合（推荐）
展示每年分红总额和派息率趋势

```javascript
// 数据处理：按年份聚合
const yearlyData = dividend_list.reduce((acc, item) => {
    const year = item.ex_div_date?.split('-')[0] || item.announce_date.split('-')[0];
    if (!acc[year]) {
        acc[year] = { total: 0, count: 0, yields: [] };
    }
    acc[year].total += item.cash_div;
    acc[year].count += 1;
    if (item.dividend_yield) {
        acc[year].yields.push(item.dividend_yield);
    }
    return acc;
}, {});

// ECharts 配置
option = {
    title: { text: '历年分红趋势' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['每股分红', '派息率'] },
    xAxis: { type: 'category', data: years },
    yAxis: [
        { type: 'value', name: '每股分红(元)' },
        { type: 'value', name: '派息率(%)', max: 10 }
    ],
    series: [
        { name: '每股分红', type: 'bar', data: cashDivData },
        { name: '派息率', type: 'line', yAxisIndex: 1, data: yieldData }
    ]
};
```

### 方案2：仅柱状图
简洁展示每年分红总额

### 方案3：表格优先
先展示表格，图表作为补充

## 📁 修改文件

### 1. 后端 `backend/main.py`
- 导入 akshare
- 添加 `get_dividend_data` 函数获取分红明细 + 计算派息率
- 在 `/api/stock-detail/{code}` 返回 `dividend_list`

### 2. 前端 `frontend/index.html`
- 添加分红趋势图表区域
- 添加分红明细表格
- 展示近10年分红数据

## 🔧 实现步骤

### Step 1: 后端实现
```python
def get_dividend_data(code: str, years: int = 10):
    """获取股票历年分红明细及派息率"""
    # 1. 转换代码格式 601766.SH -> 601766
    # 2. 调用 akshare.stock_history_dividend_detail 获取分红
    # 3. 筛选"实施"进度的分红
    # 4. 获取除权除息日收盘价
    # 5. 计算派息率
    # 6. 返回近10年列表
```

### Step 2: 前端图表实现
```html
<!-- 在基本信息前添加 -->
<div style="margin-bottom: 20px;">
    <div style="font-weight: bold; margin-bottom: 10px;">💰 历年分红</div>
    <div id="dividend-chart" style="width: 100%; height: 200px;"></div>
</div>
```

```javascript
const renderDividendChart = () => {
    const chartDom = document.getElementById('dividend-chart');
    if (!chartDom || !stockDetail.value?.dividend_list?.length) return;
    
    const chart = echarts.init(chartDom);
    const data = stockDetail.value.dividend_list;
    
    // 按年份聚合
    const yearly = {};
    data.forEach(item => {
        const year = (item.ex_div_date || item.announce_date).substring(0, 4);
        if (!yearly[year]) yearly[year] = { total: 0, yields: [] };
        yearly[year].total += item.cash_div;
        if (item.dividend_yield) yearly[year].yields.push(item.dividend_yield);
    });
    
    const years = Object.keys(yearly).sort().reverse().slice(0, 10);
    chart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { data: ['每股分红', '派息率'] },
        xAxis: { type: 'category', data: years },
        yAxis: [
            { type: 'value', name: '元' },
            { type: 'value', name: '%' }
        ],
        series: [
            { name: '每股分红', type: 'bar', data: years.map(y => yearly[y].total) },
            { name: '派息率', type: 'line', yAxisIndex: 1, 
              data: years.map(y => yearly[y].yields.length ? 
                (yearly[y].yields.reduce((a,b)=>a+b,0)/yearly[y].yields.length).toFixed(2) : null) }
        ]
    });
};
```

### Step 3: 前端表格实现
```html
<el-table :data="stockDetail.dividend_list.slice(0, 20)" size="small">
    <el-table-column prop="announce_date" label="公告日期" width="100"></el-table-column>
    <el-table-column prop="cash_div" label="每股派息" width="90">
        <template #default="{row}">{{ row.cash_div }}元</template>
    </el-table-column>
    <el-table-column prop="ex_div_date" label="除权除息日" width="110"></el-table-column>
    <el-table-column label="派息率">
        <template #default="{row}">
            <span :style="{color: row.dividend_yield > 3 ? '#67c23a' : 'inherit'}">
                {{ row.dividend_yield ? row.dividend_yield + '%' : '-' }}
            </span>
        </template>
    </el-table-column>
    <el-table-column prop="progress" label="进度" width="60"></el-table-column>
</el-table>
```

## 📊 预期效果
```
┌─────────────────────────────────────────────────────────┐
│ 💰 历年分红                                             │
│ ┌───────────────────────────────────────────────────┐ │
│ │  [柱状图: 每年分红]  [折线图: 派息率趋势]        │ │
│ └───────────────────────────────────────────────────┘ │
│ 明细表格                                               │
│ 公告日期   | 每股派息 | 除权除息日 | 派息率 | 进度   │
│ 2024-12-14| 2.00元  | 2024-08-14 | 2.82% | 实施      │
│ 2024-06-12| 3.09元  | 2024-06-19 | 3.45% | 实施      │
│ ...                                                  │
└─────────────────────────────────────────────────────────┘
```

## ⚠️ 注意事项
- 代码格式转换：`.SH` / `.SZ` -> 无后缀
- 只显示"实施"进度的分红
- 图表高度适中，避免占用太多空间
- 表格限制显示20条记录
