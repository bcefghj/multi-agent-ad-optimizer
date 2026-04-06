"""
Streamlit 监控仪表板 — 广告投放效果实时可视化。

启动方式: streamlit run python/src/dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.data.mock_data import generate_full_mock_dataset
from src.models.schemas import CampaignMetrics, EventType
from src.orchestrator.supervisor import AdOptimizerSupervisor

# ──────────── 页面配置 ────────────

st.set_page_config(
    page_title="Ad Optimizer Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.metric-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 12px; padding: 20px; color: white; text-align: center;
}
.metric-value { font-size: 2em; font-weight: bold; }
.metric-label { font-size: 0.9em; opacity: 0.8; }
</style>
""", unsafe_allow_html=True)


# ──────────── 数据加载（缓存） ────────────

@st.cache_data
def load_data():
    return generate_full_mock_dataset()


@st.cache_data
def run_optimizer():
    supervisor = AdOptimizerSupervisor()
    result = supervisor.run(max_iterations=2)
    summary = supervisor.get_summary(result)
    return result, summary


# ──────────── 主页面 ────────────

def main():
    st.title("🎯 多Agent智能广告投放优化系统")
    st.caption("实时监控 · 智能优化 · 数据驱动")

    data = load_data()
    campaigns = data["campaigns"]
    creatives = data["creatives"]
    events = data["events"]
    metrics: list[CampaignMetrics] = data["metrics"]

    # ── 侧边栏 ──
    with st.sidebar:
        st.header("⚙️ 控制面板")
        selected_campaigns = st.multiselect(
            "选择Campaign", [c.campaign_id for c in campaigns],
            default=[c.campaign_id for c in campaigns],
        )
        st.divider()
        if st.button("🚀 运行优化Agent", type="primary", use_container_width=True):
            with st.spinner("Agent优化中..."):
                result, summary = run_optimizer()
                st.session_state["opt_result"] = result
                st.session_state["opt_summary"] = summary
        st.divider()
        st.info("💡 本系统使用模拟数据演示，切换至live模式需配置真实API")

    filtered_metrics = [m for m in metrics if m.campaign_id in selected_campaigns]

    # ── 核心指标卡片 ──
    total_imp = sum(m.impressions for m in filtered_metrics)
    total_clk = sum(m.clicks for m in filtered_metrics)
    total_conv = sum(m.conversions for m in filtered_metrics)
    total_cost = sum(m.total_cost for m in filtered_metrics)
    total_rev = sum(m.total_revenue for m in filtered_metrics)
    overall_ctr = total_clk / total_imp if total_imp > 0 else 0
    overall_roas = total_rev / total_cost if total_cost > 0 else 0

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("曝光量", f"{total_imp:,}")
    col2.metric("点击量", f"{total_clk:,}")
    col3.metric("转化量", f"{total_conv:,}")
    col4.metric("CTR", f"{overall_ctr:.2%}")
    col5.metric("花费", f"¥{total_cost:,.0f}")
    col6.metric("ROAS", f"{overall_roas:.2f}")

    st.divider()

    # ── 双栏布局 ──
    left, right = st.columns(2)

    with left:
        st.subheader("📈 Campaign 指标对比")
        df_metrics = pd.DataFrame([
            {
                "Campaign": m.campaign_id,
                "名称": m.campaign_name,
                "曝光": m.impressions,
                "点击": m.clicks,
                "转化": m.conversions,
                "CTR": f"{m.ctr:.2%}",
                "CVR": f"{m.cvr:.2%}",
                "CPA": f"¥{m.cpa:.1f}" if m.cpa < 1e6 else "N/A",
                "ROAS": f"{m.roas:.2f}",
                "花费": f"¥{m.total_cost:.0f}",
            }
            for m in filtered_metrics
        ])
        st.dataframe(df_metrics, use_container_width=True, hide_index=True)

    with right:
        st.subheader("🍩 花费分布")
        fig_pie = px.pie(
            values=[m.total_cost for m in filtered_metrics],
            names=[m.campaign_id for m in filtered_metrics],
            hole=0.4,
        )
        fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=350)
        st.plotly_chart(fig_pie, use_container_width=True)

    # ── 趋势图 ──
    st.subheader("📊 7天投放趋势")
    events_df = pd.DataFrame([e.model_dump() for e in events])
    events_df["date"] = pd.to_datetime(events_df["event_time"]).dt.date

    daily = events_df.groupby(["date", "event_type"]).size().reset_index(name="count")
    fig_trend = px.line(daily, x="date", y="count", color="event_type",
                        labels={"count": "事件数", "date": "日期", "event_type": "类型"})
    fig_trend.update_layout(height=350)
    st.plotly_chart(fig_trend, use_container_width=True)

    # ── ROAS 柱状图 ──
    left2, right2 = st.columns(2)
    with left2:
        st.subheader("💰 ROAS 排行")
        roas_data = sorted(filtered_metrics, key=lambda x: x.roas, reverse=True)
        fig_roas = px.bar(
            x=[m.campaign_id for m in roas_data],
            y=[m.roas for m in roas_data],
            labels={"x": "Campaign", "y": "ROAS"},
            color=[m.roas for m in roas_data],
            color_continuous_scale="RdYlGn",
        )
        fig_roas.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig_roas, use_container_width=True)

    with right2:
        st.subheader("🎯 CTR vs CVR 散点图")
        fig_scatter = px.scatter(
            x=[m.ctr for m in filtered_metrics],
            y=[m.cvr for m in filtered_metrics],
            size=[m.total_cost for m in filtered_metrics],
            text=[m.campaign_id for m in filtered_metrics],
            labels={"x": "CTR", "y": "CVR"},
        )
        fig_scatter.update_traces(textposition="top center")
        fig_scatter.update_layout(height=300)
        st.plotly_chart(fig_scatter, use_container_width=True)

    # ── Agent 优化结果 ──
    if "opt_result" in st.session_state:
        st.divider()
        st.subheader("🤖 Agent 优化结果")

        result = st.session_state["opt_result"]
        summary = st.session_state["opt_summary"]

        tab1, tab2, tab3, tab4 = st.tabs(["执行摘要", "预算分配", "优化操作", "Agent日志"])

        with tab1:
            st.code(summary)

        with tab2:
            budgets = result.get("budget_allocations", [])
            if budgets:
                df_budget = pd.DataFrame(budgets)
                st.dataframe(df_budget, use_container_width=True, hide_index=True)

                fig_budget = go.Figure()
                fig_budget.add_trace(go.Bar(
                    name="当前预算", x=[b["campaign_id"] for b in budgets],
                    y=[b["current_budget"] for b in budgets],
                ))
                fig_budget.add_trace(go.Bar(
                    name="推荐预算", x=[b["campaign_id"] for b in budgets],
                    y=[b["recommended_budget"] for b in budgets],
                ))
                fig_budget.update_layout(barmode="group", height=350)
                st.plotly_chart(fig_budget, use_container_width=True)

        with tab3:
            actions = result.get("optimization_actions", [])
            if actions:
                st.dataframe(pd.DataFrame(actions), use_container_width=True, hide_index=True)

        with tab4:
            for msg in result.get("agent_messages", []):
                agent = msg.get("agent", "?")
                content = msg.get("content", "")
                st.chat_message("assistant", avatar="🤖").write(f"**[{agent}]** {content}")


if __name__ == "__main__":
    main()
