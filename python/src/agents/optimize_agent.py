"""Optimize Agent — 自动暂停低效素材、调整预算分配、A/B测试管理."""

from __future__ import annotations

import structlog
from typing import Any

from ..models.schemas import (
    BudgetAllocation,
    CampaignMetrics,
    OptimizationAction,
)
from ..tools.analytics import optimize_budget_allocation, score_creative_performance

logger = structlog.get_logger()

SYSTEM_PROMPT = """你是一个专业的广告优化专家（Optimize Agent）。
你的职责：
1. 根据 Monitor Agent 的告警，决定优化行动
2. 自动暂停低效素材（得分低于阈值）
3. 通过 CVXPY 数学优化进行预算再分配
4. 管理 A/B 测试的启停和结果判定
5. 综合所有Agent的建议，输出最终优化方案
"""


class OptimizeAgent:
    """优化 Agent：闭环优化的执行者，整合所有 Agent 输出."""

    def __init__(self, llm: Any = None, ads_client: Any = None) -> None:
        self.llm = llm
        self.ads_client = ads_client
        self.name = "Optimize Agent"
        self.creative_score_threshold = 40.0

    def run(self, state: dict) -> dict:
        """LangGraph 节点入口."""
        logger.info("optimize_agent_start")

        metrics_data = state.get("metrics", [])
        alerts = state.get("alerts", [])
        bidding_decisions = state.get("bidding_decisions", [])
        new_creatives = state.get("new_creatives", [])

        metrics = [
            CampaignMetrics(**m) if isinstance(m, dict) else m
            for m in metrics_data
        ]

        actions: list[dict] = []
        messages = list(state.get("agent_messages", []))

        pause_actions = self._evaluate_creatives(metrics)
        actions.extend([a.model_dump() for a in pause_actions])

        budget_allocs = optimize_budget_allocation(metrics)
        budget_actions = self._budget_to_actions(budget_allocs)
        actions.extend([a.model_dump() for a in budget_actions])

        if alerts:
            alert_actions = self._handle_alerts(alerts, metrics)
            actions.extend([a.model_dump() for a in alert_actions])

        ab_actions = self._manage_ab_tests(new_creatives, metrics)
        actions.extend([a.model_dump() for a in ab_actions])

        messages.append({
            "agent": self.name,
            "content": (
                f"优化方案生成完成。共 {len(actions)} 项操作："
                f"暂停素材 {len(pause_actions)} 个，"
                f"预算调整 {len(budget_actions)} 个，"
                f"告警处理 {len(actions) - len(pause_actions) - len(budget_actions) - len(ab_actions)} 个，"
                f"A/B测试 {len(ab_actions)} 个"
            ),
        })

        iteration = state.get("iteration", 0) + 1
        is_complete = iteration >= state.get("max_iterations", 3) or not alerts

        logger.info("optimize_agent_done", actions=len(actions), iteration=iteration)
        return {
            "optimization_actions": actions,
            "budget_allocations": [a.model_dump() for a in budget_allocs],
            "agent_messages": messages,
            "current_agent": "optimize",
            "iteration": iteration,
            "is_complete": is_complete,
        }

    def _evaluate_creatives(self, metrics: list[CampaignMetrics]) -> list[OptimizationAction]:
        """评估素材表现，暂停低效素材."""
        actions = []
        for m in metrics:
            score = score_creative_performance(
                m.impressions, m.clicks, m.conversions, m.total_cost
            )
            if score < self.creative_score_threshold and m.impressions > 500:
                actions.append(OptimizationAction(
                    action_type="pause_creative",
                    campaign_id=m.campaign_id,
                    target_id=m.campaign_id,
                    before_value="active",
                    after_value="paused",
                    reason=f"素材综合得分 {score} 低于阈值 {self.creative_score_threshold}",
                    confidence=min(score / 100, 0.95),
                ))
        return actions

    def _budget_to_actions(self, allocations: list[BudgetAllocation]) -> list[OptimizationAction]:
        """将预算分配结果转为优化操作."""
        actions = []
        for alloc in allocations:
            if abs(alloc.change_pct) > 5:
                actions.append(OptimizationAction(
                    action_type="adjust_budget",
                    campaign_id=alloc.campaign_id,
                    before_value=f"¥{alloc.current_budget:.2f}",
                    after_value=f"¥{alloc.recommended_budget:.2f}",
                    reason=alloc.reason,
                    confidence=0.85,
                ))
        return actions

    def _handle_alerts(
        self, alerts: list[str], metrics: list[CampaignMetrics]
    ) -> list[OptimizationAction]:
        """处理监控告警."""
        actions = []
        for alert_msg in alerts:
            if "CTR" in alert_msg and "低于" in alert_msg:
                actions.append(OptimizationAction(
                    action_type="refresh_creative",
                    campaign_id=self._extract_campaign_id(alert_msg),
                    reason=f"告警触发：{alert_msg}",
                    confidence=0.8,
                ))
            elif "CPA" in alert_msg and "超过" in alert_msg:
                actions.append(OptimizationAction(
                    action_type="reduce_bid",
                    campaign_id=self._extract_campaign_id(alert_msg),
                    reason=f"告警触发：{alert_msg}",
                    confidence=0.85,
                ))
            elif "ROAS" in alert_msg and "低于" in alert_msg:
                actions.append(OptimizationAction(
                    action_type="pause_campaign",
                    campaign_id=self._extract_campaign_id(alert_msg),
                    reason=f"告警触发：{alert_msg}",
                    confidence=0.7,
                ))
        return actions

    def _manage_ab_tests(
        self, new_creatives: list, metrics: list[CampaignMetrics]
    ) -> list[OptimizationAction]:
        """管理A/B测试."""
        actions = []
        if new_creatives and metrics:
            campaign_id = metrics[0].campaign_id if metrics else "unknown"
            actions.append(OptimizationAction(
                action_type="start_ab_test",
                campaign_id=campaign_id,
                target_id=f"ab_test_{len(new_creatives)}_variants",
                reason=f"新增 {len(new_creatives)} 个创意变体，启动A/B测试",
                confidence=0.9,
            ))
        return actions

    @staticmethod
    def _extract_campaign_id(message: str) -> str:
        """从告警消息中提取 campaign_id."""
        for word in message.split():
            if word.startswith("camp_"):
                return word.rstrip(",;.")
        return "unknown"
