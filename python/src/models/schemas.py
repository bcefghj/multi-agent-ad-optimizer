"""Pydantic 数据模型 — 广告投放系统的核心数据结构."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ───────────────────── 枚举类型 ─────────────────────

class Platform(str, Enum):
    GOOGLE = "google"
    META = "meta"
    TIKTOK = "tiktok"


class CampaignStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class CreativeType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"


class CreativeStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    REJECTED = "rejected"


class EventType(str, Enum):
    IMPRESSION = "impression"
    CLICK = "click"
    CONVERSION = "conversion"


class DeviceType(str, Enum):
    MOBILE = "mobile"
    DESKTOP = "desktop"
    TABLET = "tablet"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


# ───────────────────── 业务模型 ─────────────────────

class Campaign(BaseModel):
    campaign_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    campaign_name: str
    platform: Platform
    status: CampaignStatus = CampaignStatus.ACTIVE
    daily_budget: float
    total_budget: float
    start_date: date
    end_date: date | None = None
    target_audience: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


class Creative(BaseModel):
    creative_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    campaign_id: str
    creative_type: CreativeType = CreativeType.TEXT
    headline: str
    description: str
    cta_text: str = "Learn More"
    status: CreativeStatus = CreativeStatus.ACTIVE
    ab_group: str = "control"
    created_at: datetime = Field(default_factory=datetime.now)


class AdEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    campaign_id: str
    creative_id: str
    event_type: EventType
    cost: float = 0.0
    revenue: float = 0.0
    platform: Platform = Platform.GOOGLE
    device: DeviceType = DeviceType.MOBILE
    country: str = "CN"
    age_group: str = "25-34"
    gender: Gender = Gender.UNKNOWN
    event_time: datetime = Field(default_factory=datetime.now)


class AudienceProfile(BaseModel):
    audience_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    segment_name: str
    age_range: str
    gender: str
    interests: list[str] = Field(default_factory=list)
    location: str = ""
    device_pref: str = "mobile"
    estimated_size: int = 0
    avg_ctr: float = 0.0
    avg_cvr: float = 0.0


class BidLog(BaseModel):
    bid_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    campaign_id: str
    creative_id: str
    bid_amount: float
    win_price: float = 0.0
    is_won: bool = False
    predicted_ctr: float = 0.0
    predicted_cvr: float = 0.0
    ecpm: float = 0.0
    bid_time: datetime = Field(default_factory=datetime.now)


# ───────────────────── Agent 通信模型 ─────────────────────

class CampaignMetrics(BaseModel):
    """单个campaign的汇总指标."""
    campaign_id: str
    campaign_name: str = ""
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    total_cost: float = 0.0
    total_revenue: float = 0.0

    @property
    def ctr(self) -> float:
        return self.clicks / self.impressions if self.impressions > 0 else 0.0

    @property
    def cvr(self) -> float:
        return self.conversions / self.clicks if self.clicks > 0 else 0.0

    @property
    def cpa(self) -> float:
        return self.total_cost / self.conversions if self.conversions > 0 else float("inf")

    @property
    def roas(self) -> float:
        return self.total_revenue / self.total_cost if self.total_cost > 0 else 0.0


class CreativeVariant(BaseModel):
    """Creative Agent 输出的创意变体."""
    headline: str
    description: str
    cta_text: str
    target_emotion: str = ""
    ab_group: str = "variant"


class BiddingDecision(BaseModel):
    """Bidding Agent 输出的竞价决策."""
    campaign_id: str
    recommended_bid: float
    bid_multiplier: float = 1.0
    predicted_ctr: float = 0.0
    predicted_cvr: float = 0.0
    ecpm: float = 0.0
    reasoning: str = ""


class OptimizationAction(BaseModel):
    """Optimize Agent 输出的优化操作."""
    action_type: str  # pause_creative / adjust_budget / start_ab_test
    campaign_id: str
    target_id: str = ""
    before_value: str = ""
    after_value: str = ""
    reason: str = ""
    confidence: float = 0.0


class BudgetAllocation(BaseModel):
    """预算分配结果."""
    campaign_id: str
    campaign_name: str = ""
    current_budget: float
    recommended_budget: float
    change_pct: float = 0.0
    reason: str = ""


# ───────────────────── LangGraph 全局状态 ─────────────────────

class AdOptimizerState(BaseModel):
    """LangGraph Supervisor 管理的全局共享状态."""
    task: str = ""
    campaign_ids: list[str] = Field(default_factory=list)
    metrics: list[CampaignMetrics] = Field(default_factory=list)
    new_creatives: list[CreativeVariant] = Field(default_factory=list)
    audience_insights: dict[str, Any] = Field(default_factory=dict)
    bidding_decisions: list[BiddingDecision] = Field(default_factory=list)
    optimization_actions: list[OptimizationAction] = Field(default_factory=list)
    budget_allocations: list[BudgetAllocation] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)
    agent_messages: list[dict[str, str]] = Field(default_factory=list)
    current_agent: str = ""
    iteration: int = 0
    max_iterations: int = 3
    is_complete: bool = False
