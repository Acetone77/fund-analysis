"""基金业绩分析工具 — Streamlit 主页面.

运行: streamlit run app.py
"""

import streamlit as st
import pandas as pd

from fund_analysis import db, fetcher
from fund_analysis import metrics as m
from fund_analysis import charts
from fund_analysis import export

# ═══════════════════════════════════════════════════════════════
# 页面配置
# ═══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="基金业绩分析",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 基金业绩分析工具")

# 初始化数据库
db.init_db()

# ═══════════════════════════════════════════════════════════════
# 侧边栏
# ═══════════════════════════════════════════════════════════════

with st.sidebar:
    st.header("📋 已保存基金")

    funds = db.list_funds()

    if funds:
        for f in funds:
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(
                    f"{f['code']} {f['name']}",
                    key=f"select_{f['code']}",
                    use_container_width=True,
                ):
                    st.session_state.selected_fund = f["code"]
            with col2:
                if st.button("🗑", key=f"del_{f['code']}", help=f"删除 {f['code']}"):
                    db.delete_fund(f["code"])
                    st.session_state.pop("selected_fund", None)
                    st.rerun()
    else:
        st.info("暂无已保存基金，请添加")

    st.divider()

    # ── 添加基金 ──
    st.header("➕ 添加基金")
    new_code = st.text_input(
        "基金代码（6 位）", placeholder="例如: 000001", key="add_code"
    )
    if st.button(
        "拉取数据", type="primary", use_container_width=True, disabled=not new_code
    ):
        with st.spinner(f"正在拉取 {new_code} ..."):
            result = fetcher.fetch_and_save(new_code)
        if result:
            st.success(f"✅ {result['name']} — {result['nav_count']} 条净值")
            st.session_state.selected_fund = new_code
            st.rerun()
        else:
            st.error("拉取失败，请检查基金代码或网络连接")

    st.divider()

    # ── 对比选择 ──
    st.header("📊 基金对比")
    if funds:
        cmp_codes = st.multiselect(
            "选择基金（2-5只）",
            options=[f["code"] for f in funds],
            format_func=lambda c: f"{c} {db.get_fund(c)['name']}",
            default=list(st.session_state.get("compare_codes", [])),
            key="compare_select",
        )
        st.session_state.compare_codes = cmp_codes
    else:
        cmp_codes = []

    st.divider()

    # ── 导出 ──
    st.header("📥 导出报告")
    if funds:
        export_code = st.selectbox(
            "选择基金",
            options=[f["code"] for f in funds],
            format_func=lambda c: f"{c} {db.get_fund(c)['name']}",
            key="export_select",
        )
        if st.button("导出 Excel 报告", use_container_width=True):
            with st.spinner("生成报告中..."):
                buf = export.export_report(export_code)
            if buf:
                fund = db.get_fund(export_code)
                st.download_button(
                    label=f"📥 下载 {fund['name']} 报告.xlsx",
                    data=buf,
                    file_name=f"{export_code}_{fund['name']}_报告.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                st.error("导出失败")

    st.divider()

    # ── 设置 ──
    st.header("⚙ 参数设置")
    rf = (
        st.number_input(
            "无风险利率",
            value=2.5,
            min_value=0.0,
            max_value=20.0,
            step=0.5,
            format="%.1f",
        )
        / 100
    )
    st.caption(f"当前: {rf:.2%}（10 年期国债近似）")

# ═══════════════════════════════════════════════════════════════
# 主区域
# ═══════════════════════════════════════════════════════════════

selected = st.session_state.get("selected_fund")

if selected:
    fund = db.get_fund(selected)
    if fund:
        tab1, tab2, tab3, tab4 = st.tabs(
            ["📈 业绩概览", "📉 风险分析", "📊 多基金对比", "📋 明细数据"]
        )
        df = db.get_nav_df(selected)

        if df.empty:
            st.warning("该基金暂无净值数据")
        else:
            indicators = m.calc_all(df["nav"], rf)

            # ── Tab 1: 业绩概览 ──
            with tab1:
                st.subheader(f"{fund['name']}（{selected}）")

                cols = st.columns(6)
                metrics_def = [
                    ("累计收益", indicators.get("total_return"), "pct"),
                    ("年化收益", indicators.get("annual_return"), "pct"),
                    ("年化波动率", indicators.get("annual_volatility"), "pct"),
                    ("最大回撤", indicators.get("max_drawdown"), "pct"),
                    ("Sharpe Ratio", indicators.get("sharpe_ratio"), "num"),
                    ("胜率", indicators.get("win_rate"), "pct"),
                ]
                for col, (label, val, fmt) in zip(cols, metrics_def):
                    with col:
                        if fmt == "pct" and val is not None:
                            st.metric(label, f"{val * 100:.2f}%")
                        elif fmt == "num" and val is not None:
                            st.metric(label, f"{val:.2f}")
                        else:
                            st.metric(label, "-")

                st.plotly_chart(
                    charts.nav_chart(df, fund["name"]), use_container_width=True
                )

                col_l, col_r = st.columns(2)
                with col_l:
                    pivot = m.calc_monthly_returns(df["nav"])
                    st.plotly_chart(
                        charts.monthly_heatmap(pivot, fund["name"]),
                        use_container_width=True,
                    )
                with col_r:
                    yearly = m.calc_yearly_returns(df["nav"])
                    st.plotly_chart(
                        charts.yearly_bar_chart(yearly, fund["name"]),
                        use_container_width=True,
                    )

                st.plotly_chart(
                    charts.rolling_return_chart(df, window=252, fund_name=fund["name"]),
                    use_container_width=True,
                )

            # ── Tab 2: 风险分析 ──
            with tab2:
                st.subheader("风险指标")

                risk_cols = st.columns(6)
                risk_def = [
                    ("最大回撤", indicators.get("max_drawdown"), "pct"),
                    ("回撤持续", indicators.get("max_dd_days"), "raw"),
                    ("VaR (95%)", indicators.get("var_95"), "pct"),
                    ("VaR (99%)", indicators.get("var_99"), "pct"),
                    ("Sortino Ratio", indicators.get("sortino_ratio"), "num"),
                    ("Calmar Ratio", indicators.get("calmar_ratio"), "num"),
                ]
                for col, (label, val, fmt) in zip(risk_cols, risk_def):
                    with col:
                        if fmt == "pct" and val is not None:
                            st.metric(label, f"{val * 100:.2f}%")
                        elif fmt == "num" and val is not None:
                            st.metric(label, f"{val:.2f}")
                        elif fmt == "raw" and val is not None:
                            st.metric(label, f"{val} 天")
                        else:
                            st.metric(label, "-")

                st.caption(
                    f"回撤区间: {indicators.get('max_dd_start', '-')} → "
                    f"{indicators.get('max_dd_end', '-')}，"
                    f"恢复: {indicators.get('max_dd_recovery', '-')}"
                )

                st.plotly_chart(
                    charts.drawdown_chart(df, fund["name"]), use_container_width=True
                )

                st.plotly_chart(
                    charts.rolling_return_chart(df, window=756, fund_name=fund["name"]),
                    use_container_width=True,
                )

            # ── Tab 3: 多基金对比 ──
            with tab3:
                st.subheader("基金对比分析")
                cmp_codes = st.session_state.get("compare_codes", [])

                if len(cmp_codes) < 1:
                    st.info("请在侧边栏「📊 基金对比」中选择 2-5 只基金")
                else:
                    cmp_data = {}
                    cmp_metrics = {}
                    for c in cmp_codes:
                        f = db.get_fund(c)
                        d = db.get_nav_df(c)
                        if f and not d.empty:
                            cmp_data[f"{c} {f['name']}"] = d
                            cmp_metrics[f"{c} {f['name']}"] = m.calc_all(d["nav"], rf)

                    if len(cmp_data) >= 1:
                        st.plotly_chart(
                            charts.comparison_chart(cmp_data), use_container_width=True
                        )
                        if len(cmp_metrics) >= 2:
                            st.plotly_chart(
                                charts.risk_return_scatter(cmp_metrics),
                                use_container_width=True,
                            )

                        st.subheader("指标对比表")
                        table_rows = []
                        for name, met in cmp_metrics.items():
                            table_rows.append({
                                "基金": name,
                                "累计收益": f"{met.get('total_return', 0) * 100:.2f}%",
                                "年化收益": f"{met.get('annual_return', 0) * 100:.2f}%",
                                "年化波动": f"{met.get('annual_volatility', 0) * 100:.2f}%",
                                "最大回撤": f"{met.get('max_drawdown', 0) * 100:.2f}%",
                                "Sharpe": f"{met.get('sharpe_ratio', 0):.2f}",
                                "Sortino": f"{met.get('sortino_ratio', 0):.2f}",
                                "Calmar": f"{met.get('calmar_ratio', 0):.2f}",
                                "胜率": f"{met.get('win_rate', 0) * 100:.2f}%",
                            })
                        st.dataframe(
                            pd.DataFrame(table_rows),
                            use_container_width=True,
                            hide_index=True,
                        )

            # ── Tab 4: 明细数据 ──
            with tab4:
                st.subheader("净值明细")
                disp = df.copy()
                disp.index = disp.index.strftime("%Y-%m-%d")
                for c in ["nav", "acc_nav"]:
                    if c in disp.columns:
                        disp[c] = disp[c].round(4)
                if "daily_return" in disp.columns:
                    disp["daily_return"] = (disp["daily_return"] * 100).round(4)
                    disp.rename(columns={"daily_return": "日收益(%)"}, inplace=True)

                st.dataframe(
                    disp.reset_index().rename(columns={"index": "日期"}),
                    use_container_width=True,
                    hide_index=True,
                )

    else:
        st.info("该基金数据不存在，请重新添加")

else:
    st.markdown("""
        ### 👋 欢迎使用基金业绩分析工具

        在左侧边栏 **输入基金代码** 开始分析。

        #### 快速开始
        1. 在左侧「➕ 添加基金」输入 6 位基金代码（如 `000001`）
        2. 点击「拉取数据」自动下载历史净值
        3. 查看业绩概览、风险分析图表
        4. 选多只基金进行对比分析
        5. 导出 Excel 报告

        #### 已支持基金类型
        - 开放式股票型、混合型、债券型、货币型基金
        - ETF 基金
        - LOF 基金
    """)

    cmp_codes = st.session_state.get("compare_codes", [])
    if len(cmp_codes) >= 2:
        st.markdown("---")
        st.subheader("📊 快速对比")
        cmp_data = {}
        cmp_metrics = {}
        for c in cmp_codes:
            f = db.get_fund(c)
            d = db.get_nav_df(c)
            if f and not d.empty:
                cmp_data[f"{c} {f['name']}"] = d
                cmp_metrics[f"{c} {f['name']}"] = m.calc_all(d["nav"], rf)

        if cmp_data:
            st.plotly_chart(
                charts.comparison_chart(cmp_data), use_container_width=True
            )
            if len(cmp_metrics) >= 2:
                st.plotly_chart(
                    charts.risk_return_scatter(cmp_metrics), use_container_width=True
                )
