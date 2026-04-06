"""
LangGraph Supervisor — 广告优化闭环的核心编排层。

架构：Supervisor Pattern（动态路由 + 条件分支 + 循环优化）

流程：
  1. Monitor Agent → 采集指标、检测异常
  2. Audience Agent → 受众分析（可与Monitor并行）
  3. Creative Agent → 生成新素材变体
  4. Bidding Agent  → 优化竞价策略
  5. Optimize Agent → 整合所有输出，生成优化方案
  6. 若仍有未解决告警且未达最大迭代数 → 回到步骤1
"""

from __future__ import annotations

import json
import os
from typing import Any

import structlog

from ..agents.audience_agent import AudienceAgent
from ..agents.bidding_agent import BiddingAgent
from ..agents.creative_agent import CreativeAgent
from ..agents.monitor_agent import MonitorAgent
from ..agents.optimize_agent import OptimizeAgent
from ..data.mock_data import compute_mock_metrics, generate_full_mock_dataset
from ..models.schemas import CampaignMetrics

logger = structlog.get_logger()

# LangGraph 是可选依赖
try:
    from langgraph.graph import END, StateGraph
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False


# ────────── State Schema ──────────

STATE_SCHEMA = {
    "task": str,
    "campaign_ids": list,
    "metrics": list,
    "new_creatives": list,
    "audience_insights": dict,
    "bidding_decisions": list,
    "optimization_actions": list,
    "budget_allocations": list,
    "alerts": list,
    "agent_messages": list,
    "current_agent": str,
    "iteration": int,
    "max_iterations": int,
    "is_complete": bool,
}


def _merge_lists(old: list, new: list) -> list:
    """状态合并策略：列表追加而非覆盖."""
    if new is None:
        return old
    return new


def _merge_dicts(old: dict, new: dict) -> dict:
    if new is None:
        return old
    merged = dict(old) if old else {}
    merged.update(new)
    return merged


# ────────── Supervisor 构建 ──────────

class AdOptimizerSupervisor:
    """广告优化 Supervisor：编排5个Agent的闭环工作流."""

    def __init__(self, llm: Any = None, db_client: Any = None, ads_client: Any = None) -> None:
        self.creative = CreativeAgent(llm=llm)
        self.audience = AudienceAgent(llm=llm, db_client=db_client)
        self.bidding = BiddingAgent(llm=llm)
        self.monitor = MonitorAgent(llm=llm, db_client=db_client)
        self.optimize = OptimizeAgent(llm=llm, ads_client=ads_client)
        self.graph = self._build_graph() if HAS_LANGGRAPH else None

    def _build_graph(self) -> Any:
        """构建 LangGraph 状态图."""
        graph = StateGraph(dict)

        graph.add_node("monitor", self.monitor.run)
        graph.add_node("audience", self.audience.run)
        graph.add_node("creative", self.creative.run)
        graph.add_node("bidding", self.bidding.run)
        graph.add_node("optimize", self.optimize.run)

        graph.set_entry_point("monitor")
        graph.add_edge("monitor", "audience")
        graph.add_edge("audience", "creative")
        graph.add_edge("creative", "bidding")
        graph.add_edge("bidding", "optimize")

        graph.add_conditional_edges(
            "optimize",
            self._should_continue,
            {"continue": "monitor", "end": END},
        )

        return graph.compile()

    @staticmethod
    def _should_continue(state: dict) -> str:
        """条件分支：是否继续迭代优化."""
        if state.get("is_complete", False):
            return "end"
        iteration = state.get("iteration", 0)
        max_iter = state.get("max_iterations", 3)
        if iteration >= max_iter:
            return "end"
        if state.get("alerts"):
            return "continue"
        return "end"

    def run(self, campaign_ids: list[str] | None = None, max_iterations: int = 3) -> dict:
        """运行完整的优化闭环."""
        mock_data = generate_full_mock_dataset()
        metrics = mock_data["metrics"]

        if campaign_ids:
            metrics = [m for m in metrics if m.campaign_id in campaign_ids]
        else:
            campaign_ids = [m.campaign_id for m in metrics]

        initial_state = {
            "task": "optimize_campaigns",
            "campaign_ids": campaign_ids,
            "metrics": [m.model_dump() for m in metrics],
            "new_creatives": [],
            "audience_insights": {},
            "bidding_decisions": [],
            "optimization_actions": [],
            "budget_allocations": [],
            "alerts": [],
            "agent_messages": [],
            "current_agent": "",
            "iteration": 0,
            "max_iterations": max_iterations,
            "is_complete": False,
        }

        if self.graph is not None:
            logger.info("supervisor_start_langgraph", campaigns=len(campaign_ids))
            result = self.graph.invoke(initial_state)
        else:
            logger.info("supervisor_start_sequential", campaigns=len(campaign_ids))
            result = self._run_sequential(initial_state)

        return result

    def _run_sequential(self, state: dict) -> dict:
        """无 LangGraph 时的顺序执行回退方案."""
        for iteration in range(state.get("max_iterations", 3)):
            logger.info("sequential_iteration", iteration=iteration + 1)

            state = {**state, **self.monitor.run(state)}
            state = {**state, **self.audience.run(state)}
            state = {**state, **self.creative.run(state)}
            state = {**state, **self.bidding.run(state)}
            state = {**state, **self.optimize.run(state)}

            if state.get("is_complete", False):
                break
            if not state.get("alerts"):
                break

        return state

    def get_summary(self, result: dict) -> str:
        """生成人类可读的优化摘要."""
        messages = result.get("agent_messages", [])
        actions = result.get("optimization_actions", [])
        budgets = result.get("budget_allocations", [])
        iterations = result.get("iteration", 0)

        lines = [
            "=" * 60,
            "  多Agent广告优化系统 — 执行报告",
            "=" * 60,
            f"\n总迭代轮次: {iterations}",
            f"优化操作数: {len(actions)}",
            f"预算调整数: {len(budgets)}",
            "\n--- Agent 执行日志 ---",
        ]

        for msg in messages:
            lines.append(f"[{msg.get('agent', '?')}] {msg.get('content', '')}")

        if budgets:
            lines.append("\n--- 预算分配建议 ---")
            for b_data in budgets:
                b = b_data if isinstance(b_data, dict) else b_data
                lines.append(
                    f"  {b.get('campaign_id', '?')}: "
                    f"¥{b.get('current_budget', 0):.0f} → ¥{b.get('recommended_budget', 0):.0f} "
                    f"({b.get('change_pct', 0):+.1f}%) — {b.get('reason', '')}"
                )

        if actions:
            lines.append("\n--- 优化操作列表 ---")
            for a_data in actions:
                a = a_data if isinstance(a_data, dict) else a_data
                lines.append(
                    f"  [{a.get('action_type', '?')}] Campaign {a.get('campaign_id', '?')}: "
                    f"{a.get('reason', '')}"
                )

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)


# ────────── CLI 入口 ──────────

def main() -> None:
    """命令行运行入口."""
    from dotenv import load_dotenv
    load_dotenv()

    llm = None
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key and not api_key.startswith("sk-your"):
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0.7)
            logger.info("llm_initialized", model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        except ImportError:
            logger.warning("langchain_openai not installed, using mock mode")

    supervisor = AdOptimizerSupervisor(llm=llm)
    result = supervisor.run(max_iterations=2)
    print(supervisor.get_summary(result))


if __name__ == "__main__":
    main()
