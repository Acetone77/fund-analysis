# 📊 基金业绩分析工具

轻量级公募基金业绩分析工具 —— 支持数据拉取、指标计算、图表展示、多基金对比和 Excel 报告导出。

## 功能

- 🔍 **一键拉取**：输入基金代码，自动下载历史净值数据
- 📈 **业绩分析**：累计/年化/滚动收益率、月度/年度收益分解
- 📉 **风险度量**：年化波动率、最大回撤、VaR、下行波动率
- 🎯 **风险调整**：Sharpe Ratio、Sortino Ratio、Calmar Ratio、胜率
- 📊 **多基金对比**：归一化净值走势、风险-收益散点图、指标对比表
- 📥 **Excel 报告**：多 Sheet 专业报告一键导出

## 安装

```bash
# 1. 进入项目目录
cd fund-analysis

# 2. 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 安装依赖
pip install -e .
```

## 快速开始

```bash
streamlit run app.py
```

浏览器打开 `http://localhost:8501`，在左侧边栏输入基金代码（如 `000001`），点击「拉取数据」即可。

## 项目结构

```
fund-analysis/
├── app.py                       # Streamlit 主页面
├── pyproject.toml               # 项目配置
├── fund_analysis/
│   ├── db.py                    # SQLite 数据库层
│   ├── fetcher.py               # akshare 数据采集
│   ├── metrics.py               # 业绩指标计算引擎
│   ├── charts.py                # Plotly 图表生成
│   └── export.py                # Excel 报告导出
├── tests/
│   └── test_metrics.py          # 指标计算单元测试
└── data/                        # 本地数据库（自动生成）
```

## 基金代码示例

| 代码 | 名称 | 类型 |
|------|------|------|
| 000001 | 华夏成长混合 | 混合型 |
| 110011 | 易方达中小盘混合 | 混合型 |
| 510050 | 华夏上证50ETF | ETF |
| 003171 | 鹏华丰禄债券 | 债券型 |

## 运行测试

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## 技术栈

- **Python 3.10+**
- **Streamlit** — Web 界面
- **akshare** — 金融数据源
- **Plotly** — 交互式图表
- **SQLite** — 本地存储
- **openpyxl** — Excel 导出

## 数据说明

- 数据来源于 [akshare](https://github.com/akfamily/akshare)，通过天天基金等公开接口获取
- 历史净值存储在本地 SQLite 数据库，避免重复请求
- 无风险利率默认为 2.5%（中国 10 年期国债收益率近似值），可在界面上调整
