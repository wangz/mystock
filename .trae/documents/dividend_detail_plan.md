# 股票详情页加入分红情况 - 实现计划

## 📋 需求概述
在股票详情页中添加近几年分红情况的展示，并计算对应当时的派息率

## 🔍 研究结论

### 数据源分析
| 数据源 | 状态 | 说明 |
|--------|------|------|
| Tushare | ❌ Token过期 | 无法使用 |
| pywencai | ⚠️ 分页数据 | 返回摘要信息 |
| baostock | ✅ 可用 | 可查分红数据和历史股价 |

### 分红数据字段（baostock）
| 字段 | 说明 | 示例 |
|------|------|------|
| dividPayDate | 除权除息日 | 2023-08-11 |
| dividCashPsBeforeTax | 税前每股分红 | 0.2 |
| dividPlanAnnounceDate | 分红预案公告日 | 2023-03-31 |

### 派息率计算
```
派息率 = 每股分红(含税) / 除权除息日收盘价 × 100%
```

## 📁 修改文件

### 1. 后端 `backend/main.py`
- 修改 `/api/stock-detail/{code}` 接口
- 添加分红数据查询（baostock）
- 添加除权除息日股价查询
- 计算派息率

### 2. 前端 `frontend/index.html`
- 在详情弹窗中添加分红情况表格
- 展示：分红年份、每股分红、除权除息日、派息率

## 🔧 实现步骤

### Step 1: 修改后端 API
```python
# 在 get_stock_detail 函数中添加：
# 1. 使用 baostock 查询历年分红 (近5年)
# 2. 使用 baostock 查询除权除息日股价
# 3. 计算派息率
# 4. 返回 dividend_list
```

### Step 2: 修改前端展示
```html
<!-- 在 ROE 趋势图下方添加 -->
<div>
    <div style="font-weight: bold; margin-bottom: 10px;">💰 分红情况</div>
    <el-table :data="stockDetail.dividend_list">
        <el-table-column prop="year" label="报告期"></el-table-column>
        <el-table-column prop="cash_per_share" label="每股分红"></el-table-column>
        <el-table-column prop="pay_date" label="除权除息日"></el-table-column>
        <el-table-column prop="dividend_yield" label="派息率">
            <template #default="{row}">
                {{ row.dividend_yield ? row.dividend_yield + '%' : '-' }}
            </template>
        </el-table-column>
    </el-table>
</div>
```

### Step 3: 测试验证
1. 重启后端服务
2. 测试中国中车、贵州茅台等股票详情
3. 验证分红数据和派息率展示

## 📊 预期效果
```
┌─────────────────────────────────────────────────┐
│ 💰 分红情况                                     │
│ 报告期   | 每股分红 | 除权除息日 | 派息率       │
│ 2023年报  | 0.20元  | 2023-08-11 | 2.85%       │
│ 2022年报  | 0.15元  | 2022-08-12 | 2.34%       │
│ ...                                             │
└─────────────────────────────────────────────────┘
```
