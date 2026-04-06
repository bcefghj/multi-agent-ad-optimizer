"""Monitor Agent — 实时追踪投放效果（CTR/CVR/CPA/ROAS）."""

from __future__ import annotations

import structlog
from typing import Any

from ..models.schemas import CampaignMetrics
from ..tools.analytics import detect_anomalies

logger = structlog.get_logger()

SYSTEM_PROMPT = """你是一个专业的广告投放监控专家（Monitor Agent）。
你的职责：
1. 实时追踪所有 Campaign 的核心指标：CTR、CVR、CPA、ROAS
2. 检测异常情况（CTR暴跌、CPA飙升、预算超支）
3. 生成告警信息并通知 Optimize Agent
4. 提供数据驱动的投放健康度评分
"""


class MonitorAgent:
    """监控 Agent：实时追踪投放效果，异常检测告警."""

    def __init__(self, llm: Any = None, db_client: Any = None) -> None:
        self.llm = llm
        self.db = db_client
        self.name = "Monitor Agent"

    def run(self, state: dict) -> dict:
        """LangGraph 节点入口."""
        logger.info("monitor_agent_start")
        metrics_data = state.get("metrics", [])

        metrics = [
            CampaignMetrics(**m) if isinstance(m, dict) else m
            for m in metrics_data
        ]

        alerts = detect_anomalies(metrics)
        health_report = self._generate_health_report(metrics)
        messages = list(state.get("agent_messages", []))

        alert_msgs = [a["message"] for a in alerts]
        status = "异常" if alerts else "健康"
        messages.append({
            "agent": self.name,
            "content": (
                f"监控报告：系统状态【{status}】。"
                f"监控 {len(metrics)} 个 Campaign，发现 {len(alerts)} 个异常。"
                + (f"\n告警详情: {'; '.join(alert_msgs[:3])}" if alerts else "")
            ),
        })

        logger.info("monitor_agent_done", alerts=len(alerts))
        return {
            "alerts": [a["message"] for a in alerts],
            "agent_messages": messages,
            "current_agent": "monitor",
        }

    def _generate_health_report(self, metrics: list[CampaignMetrics]) -> dict:
        """生成投放健康度报告."""
        if not metrics:
            return {"status": "no_data", "score": 0}

        total_impressions = sum(m.impressions for m in metrics)
        total_clicks = sum(m.clicks for m in metrics)
        total_conversions = sum(m.conversions for m in metrics)
        total_cost = sum(m.total_cost for m in metrics)
        total_revenue = sum(m.total_revenue for m in metrics)

        overall_ctr = total_clicks / total_impressions if total_impressions > 0 else 0
        overall_cvr = total_conversions / total_clicks if total_clicks > 0 else 0
        overall_cpa = total_cost / total_conversions if total_conversions > 0 else float("inf")
        overall_roas = total_revenue / total_cost if total_cost > 0 else 0

        score = 0
        score += min(overall_ctr / 0.05, 1.0) * 25
        score += min(overall_cvr / 0.10, 1.0) * 25
        score += max(1 - overall_cpa / 200, 0) * 25
        score += min(overall_roas / 3.0, 1.0) * 25

        return {
            "status": "healthy" if score > 60 else "warning" if score > 40 else "critical",
            "score": round(score, 1),
            "summary": {
                "total_campaigns": len(metrics),
                "total_impressions": total_impressions,
                "total_clicks": total_clicks,
                "total_conversions": total_conversions,
                "total_cost": round(total_cost, 2),
                "total_revenue": round(total_revenue, 2),
                "overall_ctr": round(overall_ctr, 4),
                "overall_cvr": round(overall_cvr, 4),
                "overall_cpa": round(overall_cpa, 2) if overall_cpa < float("inf") else None,
                "overall_roas": round(overall_roas, 2),
            },
        }
