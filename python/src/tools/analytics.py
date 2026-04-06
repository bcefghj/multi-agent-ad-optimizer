"""分析工具 — 提供给各 Agent 使用的指标计算和优化工具."""

from __future__ import annotations

import numpy as np
from typing import Any

from ..models.schemas import BudgetAllocation, CampaignMetrics

# CVXPY 是可选依赖，用于预算优化
try:
    import cvxpy as cp
    HAS_CVXPY = True
except ImportError:
    HAS_CVXPY = False


def calculate_ecpm(ctr: float, cvr: float, target_cpa: float) -> float:
    """eCPM = CTR x CVR x TargetCPA x 1000."""
    return ctr * cvr * target_cpa * 1000


def detect_anomalies(
    metrics_list: list[CampaignMetrics],
    ctr_threshold: float = 0.005,
    cpa_ceiling: float = 200.0,
    roas_floor: float = 1.0,
) -> list[dict[str, Any]]:
    """基于规则的异常检测：CTR过低、CPA过高、ROAS过低."""
    alerts = []
    for m in metrics_list:
        if m.impressions > 100 and m.ctr < ctr_threshold:
            alerts.append({
                "campaign_id": m.campaign_id,
                "type": "low_ctr",
                "value": round(m.ctr, 4),
                "threshold": ctr_threshold,
                "message": f"Campaign {m.campaign_id} CTR ({m.ctr:.2%}) 低于阈值 ({ctr_threshold:.2%})",
            })
        if m.conversions > 0 and m.cpa > cpa_ceiling:
            alerts.append({
                "campaign_id": m.campaign_id,
                "type": "high_cpa",
                "value": round(m.cpa, 2),
                "threshold": cpa_ceiling,
                "message": f"Campaign {m.campaign_id} CPA (¥{m.cpa:.2f}) 超过上限 (¥{cpa_ceiling:.2f})",
            })
        if m.total_cost > 100 and m.roas < roas_floor:
            alerts.append({
                "campaign_id": m.campaign_id,
                "type": "low_roas",
                "value": round(m.roas, 2),
                "threshold": roas_floor,
                "message": f"Campaign {m.campaign_id} ROAS ({m.roas:.2f}) 低于目标 ({roas_floor:.2f})",
            })
    return alerts


def optimize_budget_allocation(
    metrics_list: list[CampaignMetrics],
    total_budget: float | None = None,
    max_change_pct: float = 0.5,
) -> list[BudgetAllocation]:
    """
    使用 CVXPY 凸优化进行预算再分配。

    目标：最大化 ROAS（收益/成本），约束：
    - 总预算不变
    - 单个 campaign 预算变动不超过 ±max_change_pct
    - 非负约束
    """
    active = [m for m in metrics_list if m.total_cost > 0]
    if not active:
        return []

    n = len(active)
    current_budgets = np.array([m.total_cost for m in active])
    if total_budget is None:
        total_budget = float(current_budgets.sum())

    roas_scores = np.array([m.roas for m in active])
    roas_scores = np.where(roas_scores > 0, roas_scores, 0.01)

    if HAS_CVXPY:
        x = cp.Variable(n, nonneg=True)
        objective = cp.Maximize(roas_scores @ x)
        constraints = [
            cp.sum(x) == total_budget,
            x >= current_budgets * (1 - max_change_pct),
            x <= current_budgets * (1 + max_change_pct),
        ]
        prob = cp.Problem(objective, constraints)
        prob.solve(solver=cp.SCS, verbose=False)

        if prob.status == "optimal":
            new_budgets = x.value
        else:
            new_budgets = _heuristic_allocation(current_budgets, roas_scores, total_budget, max_change_pct)
    else:
        new_budgets = _heuristic_allocation(current_budgets, roas_scores, total_budget, max_change_pct)

    allocations = []
    for i, m in enumerate(active):
        change_pct = (new_budgets[i] - current_budgets[i]) / current_budgets[i] if current_budgets[i] > 0 else 0
        reason = "ROAS较高，建议增加预算" if change_pct > 0.05 else \
                 "ROAS较低，建议减少预算" if change_pct < -0.05 else "预算维持不变"
        allocations.append(BudgetAllocation(
            campaign_id=m.campaign_id,
            campaign_name=m.campaign_name,
            current_budget=round(current_budgets[i], 2),
            recommended_budget=round(float(new_budgets[i]), 2),
            change_pct=round(float(change_pct) * 100, 1),
            reason=reason,
        ))

    return allocations


def _heuristic_allocation(
    current: np.ndarray,
    scores: np.ndarray,
    total: float,
    max_pct: float,
) -> np.ndarray:
    """当 CVXPY 不可用时的启发式分配算法."""
    weights = scores / scores.sum()
    ideal = weights * total
    lower = current * (1 - max_pct)
    upper = current * (1 + max_pct)
    result = np.clip(ideal, lower, upper)
    result = result / result.sum() * total
    return result


def score_creative_performance(
    impressions: int, clicks: int, conversions: int, cost: float
) -> float:
    """创意素材综合得分 = CTR权重 + CVR权重 + CPA权重."""
    ctr = clicks / impressions if impressions > 0 else 0
    cvr = conversions / clicks if clicks > 0 else 0
    cpa = cost / conversions if conversions > 0 else float("inf")

    ctr_score = min(ctr / 0.05, 1.0) * 40
    cvr_score = min(cvr / 0.1, 1.0) * 35
    cpa_score = max(1 - cpa / 200, 0) * 25

    return round(ctr_score + cvr_score + cpa_score, 2)
