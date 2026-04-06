"""Creative Agent — 自动生成广告文案/素材变体."""

from __future__ import annotations

import json
import random
import structlog
from typing import Any

from ..models.schemas import (
    AdOptimizerState,
    CampaignMetrics,
    CreativeVariant,
)

logger = structlog.get_logger()

SYSTEM_PROMPT = """你是一个专业的广告创意专家（Creative Agent）。
你的职责：
1. 根据campaign的表现数据，生成新的广告文案变体
2. 分析现有素材的优劣势，提出改进方向
3. 为A/B测试生成对照组和实验组素材

输出要求：
- 每个campaign生成3-5个文案变体
- 每个变体包含：headline（标题）、description（描述）、cta_text（行动号召）、target_emotion（目标情感）
- 基于数据反馈优化文案方向
"""

# 用于 mock 模式的文案模板
EMOTION_MAP = {
    "urgency": ["限时特惠", "最后机会", "倒计时"],
    "trust": ["万人好评", "品质保障", "专业认证"],
    "curiosity": ["你不知道的", "揭秘", "真相是"],
    "benefit": ["立省", "轻松获得", "一步到位"],
    "social_proof": ["百万用户选择", "热销爆款", "口碑之选"],
}


class CreativeAgent:
    """创意 Agent：自动生成广告文案变体，支持 LLM 和 Mock 两种模式."""

    def __init__(self, llm: Any = None) -> None:
        self.llm = llm
        self.name = "Creative Agent"

    def run(self, state: dict) -> dict:
        """LangGraph 节点入口."""
        logger.info("creative_agent_start")
        metrics = state.get("metrics", [])
        campaign_ids = state.get("campaign_ids", [])

        new_creatives: list[dict] = []
        messages: list[dict] = list(state.get("agent_messages", []))

        for m_data in metrics:
            m = CampaignMetrics(**m_data) if isinstance(m_data, dict) else m_data
            if m.campaign_id not in campaign_ids and campaign_ids:
                continue

            variants = self._generate_variants(m)
            new_creatives.extend([v.model_dump() for v in variants])

            messages.append({
                "agent": self.name,
                "content": (
                    f"为 Campaign {m.campaign_id} 生成了 {len(variants)} 个新创意变体。"
                    f"当前 CTR={m.ctr:.2%}, 优化方向: "
                    f"{'提升点击吸引力' if m.ctr < 0.03 else '提升转化说服力'}"
                ),
            })

        logger.info("creative_agent_done", variants_count=len(new_creatives))
        return {
            "new_creatives": new_creatives,
            "agent_messages": messages,
            "current_agent": "creative",
        }

    def _generate_variants(self, metrics: CampaignMetrics) -> list[CreativeVariant]:
        """根据指标数据生成文案变体."""
        if self.llm is not None:
            return self._llm_generate(metrics)
        return self._mock_generate(metrics)

    def _llm_generate(self, metrics: CampaignMetrics) -> list[CreativeVariant]:
        """通过 LLM 生成创意文案."""
        prompt = (
            f"为以下广告活动生成5个文案变体：\n"
            f"Campaign: {metrics.campaign_name} (ID: {metrics.campaign_id})\n"
            f"当前指标: CTR={metrics.ctr:.2%}, CVR={metrics.cvr:.2%}, "
            f"CPA=¥{metrics.cpa:.2f}, ROAS={metrics.roas:.2f}\n\n"
            f"请以JSON数组格式返回，每个元素包含: headline, description, cta_text, target_emotion"
        )
        try:
            response = self.llm.invoke(
                [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
            )
            content = response.content if hasattr(response, "content") else str(response)
            data = json.loads(content)
            return [CreativeVariant(**item) for item in data]
        except Exception as e:
            logger.warning("llm_generate_fallback", error=str(e))
            return self._mock_generate(metrics)

    def _mock_generate(self, metrics: CampaignMetrics) -> list[CreativeVariant]:
        """Mock 模式：基于规则生成文案变体."""
        if metrics.ctr < 0.03:
            emotions = ["urgency", "curiosity", "social_proof"]
        elif metrics.cvr < 0.05:
            emotions = ["benefit", "trust", "social_proof"]
        else:
            emotions = ["urgency", "benefit", "curiosity"]

        product = metrics.campaign_name.split(" - ")[0] if " - " in metrics.campaign_name else "产品"
        variants = []

        for i, emotion in enumerate(emotions):
            keywords = EMOTION_MAP.get(emotion, ["精选"])
            keyword = random.choice(keywords)
            variants.append(CreativeVariant(
                headline=f"{keyword}！{product}专属福利",
                description=f"精选{product}，{keyword.lower()}价格，品质生活从此开始。限量优惠不容错过！",
                cta_text=random.choice(["立即抢购", "了解详情", "限时体验", "马上领取"]),
                target_emotion=emotion,
                ab_group=f"variant_{chr(97 + i)}",
            ))

        return variants
