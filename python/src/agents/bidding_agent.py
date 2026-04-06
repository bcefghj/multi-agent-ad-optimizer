"""Bidding Agent — 实时竞价策略优化，ROI最大化出价."""

from __future__ import annotations

import random
import structlog
from typing import Any

from ..models.schemas import BiddingDecision, CampaignMetrics
from ..tools.analytics import calculate_ecpm

logger = structlog.get_logger()

SYSTEM_PROMPT = """你是一个专业的广告竞价策略专家（Bidding Agent）。
你的职责：
1. 基于历史数据预估 CTR 和 CVR
2. 计算最优 eCPM 和出价策略
3. 在 ROI 约束下最大化曝光和转化
4. 动态调整出价倍率（时段/人群/设备维度）
"""


class BiddingAgent:
    """竞价 Agent：实时出价策略优化."""

    def __init__(self, llm: Any = None, target_roas: float = 2.0) -> None:
        self.llm = llm
        self.target_roas = target_roas
        self.name = "Bidding Agent"

    def run(self, state: dict) -> dict:
        """LangGraph 节点入口."""
        logger.info("bidding_agent_start")
        metrics = state.get("metrics", [])
        audience = state.get("audience_insights", {})

        decisions: list[dict] = []
        messages = list(state.get("agent_messages", []))

        for m_data in metrics:
            m = CampaignMetrics(**m_data) if isinstance(m_data, dict) else m_data
            decision = self._compute_bid(m, audience)
            decisions.append(decision.model_dump())

        avg_bid = sum(d["recommended_bid"] for d in decisions) / len(decisions) if decisions else 0
        messages.append({
            "agent": self.name,
            "content": (
                f"竞价策略更新完成。优化了 {len(decisions)} 个 Campaign 的出价。"
                f"平均推荐出价: ¥{avg_bid:.2f}, 目标 ROAS: {self.target_roas}"
            ),
        })

        logger.info("bidding_agent_done", decisions_count=len(decisions))
        return {
            "bidding_decisions": decisions,
            "agent_messages": messages,
            "current_agent": "bidding",
        }

    def _compute_bid(self, metrics: CampaignMetrics, audience: dict) -> BiddingDecision:
        """计算单个 Campaign 的竞价决策."""
        pred_ctr = self._predict_ctr(metrics)
        pred_cvr = self._predict_cvr(metrics)

        target_cpa = metrics.cpa if metrics.cpa < float("inf") else 100.0
        ecpm = calculate_ecpm(pred_ctr, pred_cvr, target_cpa)

        multiplier = self._calculate_multiplier(metrics)
        recommended_bid = round(ecpm / 1000 * multiplier, 2)
        recommended_bid = max(0.01, min(recommended_bid, target_cpa * 0.8))

        if metrics.roas > self.target_roas * 1.5:
            reasoning = "ROAS远超目标，可适当提高出价争取更多流量"
            multiplier *= 1.2
        elif metrics.roas < self.target_roas * 0.5:
            reasoning = "ROAS远低于目标，降低出价控制成本"
            multiplier *= 0.7
        else:
            reasoning = "ROAS在合理范围，维持当前出价策略"

        return BiddingDecision(
            campaign_id=metrics.campaign_id,
            recommended_bid=round(recommended_bid * multiplier / self._calculate_multiplier(metrics), 2),
            bid_multiplier=round(multiplier, 2),
            predicted_ctr=round(pred_ctr, 4),
            predicted_cvr=round(pred_cvr, 4),
            ecpm=round(ecpm, 2),
            reasoning=reasoning,
        )

    def _predict_ctr(self, metrics: CampaignMetrics) -> float:
        """简化版 CTR 预估：历史均值 + 随机波动."""
        base = metrics.ctr if metrics.ctr > 0 else 0.03
        noise = random.gauss(0, base * 0.1)
        return max(0.001, base + noise)

    def _predict_cvr(self, metrics: CampaignMetrics) -> float:
        """简化版 CVR 预估."""
        base = metrics.cvr if metrics.cvr > 0 else 0.05
        noise = random.gauss(0, base * 0.1)
        return max(0.001, base + noise)

    def _calculate_multiplier(self, metrics: CampaignMetrics) -> float:
        """基于 ROAS 的动态出价倍率."""
        if metrics.roas <= 0:
            return 0.8
        ratio = metrics.roas / self.target_roas
        if ratio > 2.0:
            return 1.3
        if ratio > 1.2:
            return 1.1
        if ratio > 0.8:
            return 1.0
        if ratio > 0.5:
            return 0.8
        return 0.6
