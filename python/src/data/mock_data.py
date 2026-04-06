"""模拟数据生成器 — 用于演示和测试，无需真实广告平台."""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta

from ..models.schemas import (
    AdEvent,
    AudienceProfile,
    BudgetAllocation,
    Campaign,
    CampaignMetrics,
    CampaignStatus,
    Creative,
    CreativeStatus,
    CreativeType,
    DeviceType,
    EventType,
    Gender,
    Platform,
)

random.seed(42)

PRODUCT_NAMES = [
    "智能手表Pro", "AI学习助手", "健康膳食包", "电动牙刷X1",
    "无线降噪耳机", "便携投影仪", "智能门锁S3", "空气净化器",
]

HEADLINES = [
    "限时特惠 立减{discount}%", "新品首发 抢先体验",
    "好评如潮 万人推荐", "智能生活 从{product}开始",
    "买一送一 最后{days}天", "年度爆款 不容错过",
    "专业品质 匠心之选", "科技改变生活",
]

CTA_OPTIONS = ["立即购买", "了解更多", "免费试用", "限时抢购", "预约体验"]

INTERESTS = [
    ["科技", "数码", "智能家居"], ["健身", "运动", "健康"],
    ["美食", "烹饪", "生活"], ["旅行", "摄影", "户外"],
    ["教育", "学习", "职场"], ["时尚", "美妆", "穿搭"],
]

COUNTRIES = ["CN", "US", "JP", "UK", "DE", "KR"]
AGE_GROUPS = ["18-24", "25-34", "35-44", "45-54", "55+"]


def generate_campaigns(n: int = 5) -> list[Campaign]:
    campaigns = []
    for i in range(n):
        product = random.choice(PRODUCT_NAMES)
        platform = random.choice(list(Platform))
        campaigns.append(Campaign(
            campaign_id=f"camp_{i+1:03d}",
            campaign_name=f"{product} - {platform.value}投放",
            platform=platform,
            status=random.choice([CampaignStatus.ACTIVE, CampaignStatus.ACTIVE, CampaignStatus.PAUSED]),
            daily_budget=round(random.uniform(500, 5000), 2),
            total_budget=round(random.uniform(10000, 100000), 2),
            start_date=datetime.now().date() - timedelta(days=random.randint(7, 30)),
        ))
    return campaigns


def generate_creatives(campaigns: list[Campaign], per_campaign: int = 4) -> list[Creative]:
    creatives = []
    for camp in campaigns:
        for j in range(per_campaign):
            product = camp.campaign_name.split(" - ")[0]
            headline = random.choice(HEADLINES).format(
                discount=random.randint(10, 50),
                product=product,
                days=random.randint(1, 7),
            )
            creatives.append(Creative(
                creative_id=f"cre_{camp.campaign_id}_{j+1:02d}",
                campaign_id=camp.campaign_id,
                creative_type=random.choice(list(CreativeType)),
                headline=headline,
                description=f"{product}，品质保障，售后无忧。现在下单享受专属优惠！",
                cta_text=random.choice(CTA_OPTIONS),
                status=random.choices(
                    [CreativeStatus.ACTIVE, CreativeStatus.PAUSED],
                    weights=[0.8, 0.2],
                )[0],
                ab_group=random.choice(["control", "variant_a", "variant_b"]),
            ))
    return creatives


def generate_events(
    campaigns: list[Campaign],
    creatives: list[Creative],
    days: int = 7,
    events_per_day: int = 500,
) -> list[AdEvent]:
    """生成模拟的广告投放事件数据."""
    events = []
    now = datetime.now()

    for day_offset in range(days):
        event_time_base = now - timedelta(days=day_offset)
        for _ in range(events_per_day):
            camp = random.choice(campaigns)
            camp_creatives = [c for c in creatives if c.campaign_id == camp.campaign_id]
            if not camp_creatives:
                continue
            creative = random.choice(camp_creatives)

            hour = random.randint(0, 23)
            minute = random.randint(0, 59)
            event_time = event_time_base.replace(hour=hour, minute=minute, second=random.randint(0, 59))

            base_ctr = 0.03 + random.gauss(0, 0.01)
            base_cvr = 0.05 + random.gauss(0, 0.02)

            cpc = round(random.uniform(0.5, 5.0), 2)

            events.append(AdEvent(
                event_id=str(uuid.uuid4())[:8],
                campaign_id=camp.campaign_id,
                creative_id=creative.creative_id,
                event_type=EventType.IMPRESSION,
                cost=cpc * 0.01,
                revenue=0.0,
                platform=camp.platform,
                device=random.choice(list(DeviceType)),
                country=random.choice(COUNTRIES),
                age_group=random.choice(AGE_GROUPS),
                gender=random.choice(list(Gender)),
                event_time=event_time,
            ))

            if random.random() < base_ctr:
                events.append(AdEvent(
                    event_id=str(uuid.uuid4())[:8],
                    campaign_id=camp.campaign_id,
                    creative_id=creative.creative_id,
                    event_type=EventType.CLICK,
                    cost=cpc,
                    revenue=0.0,
                    platform=camp.platform,
                    device=events[-1].device,
                    country=events[-1].country,
                    age_group=events[-1].age_group,
                    gender=events[-1].gender,
                    event_time=event_time + timedelta(seconds=random.randint(1, 10)),
                ))

                if random.random() < base_cvr:
                    revenue = round(random.uniform(20, 200), 2)
                    events.append(AdEvent(
                        event_id=str(uuid.uuid4())[:8],
                        campaign_id=camp.campaign_id,
                        creative_id=creative.creative_id,
                        event_type=EventType.CONVERSION,
                        cost=0.0,
                        revenue=revenue,
                        platform=camp.platform,
                        device=events[-1].device,
                        country=events[-1].country,
                        age_group=events[-1].age_group,
                        gender=events[-1].gender,
                        event_time=event_time + timedelta(seconds=random.randint(30, 600)),
                    ))

    return events


def generate_audience_profiles(n: int = 6) -> list[AudienceProfile]:
    profiles = []
    segment_names = ["高价值白领", "年轻学生党", "科技发烧友", "家庭主妇", "运动爱好者", "商务人士"]
    for i in range(min(n, len(segment_names))):
        profiles.append(AudienceProfile(
            audience_id=f"aud_{i+1:03d}",
            segment_name=segment_names[i],
            age_range=random.choice(AGE_GROUPS),
            gender=random.choice(["male", "female", "all"]),
            interests=random.choice(INTERESTS),
            location=random.choice(["一线城市", "二线城市", "三线城市", "全国"]),
            device_pref=random.choice(["mobile", "desktop", "all"]),
            estimated_size=random.randint(50000, 5000000),
            avg_ctr=round(random.uniform(0.01, 0.08), 4),
            avg_cvr=round(random.uniform(0.02, 0.15), 4),
        ))
    return profiles


def compute_mock_metrics(
    campaigns: list[Campaign],
    events: list[AdEvent],
) -> list[CampaignMetrics]:
    """从事件数据中聚合计算各 campaign 指标."""
    metrics_map: dict[str, CampaignMetrics] = {}

    for camp in campaigns:
        metrics_map[camp.campaign_id] = CampaignMetrics(
            campaign_id=camp.campaign_id,
            campaign_name=camp.campaign_name,
        )

    for event in events:
        m = metrics_map.get(event.campaign_id)
        if m is None:
            continue
        if event.event_type == EventType.IMPRESSION:
            m.impressions += 1
            m.total_cost += event.cost
        elif event.event_type == EventType.CLICK:
            m.clicks += 1
            m.total_cost += event.cost
        elif event.event_type == EventType.CONVERSION:
            m.conversions += 1
            m.total_revenue += event.revenue

    return list(metrics_map.values())


def generate_full_mock_dataset() -> dict:
    """一键生成完整的模拟数据集."""
    campaigns = generate_campaigns(5)
    creatives = generate_creatives(campaigns, per_campaign=4)
    events = generate_events(campaigns, creatives, days=7, events_per_day=500)
    audiences = generate_audience_profiles(6)
    metrics = compute_mock_metrics(campaigns, events)

    return {
        "campaigns": campaigns,
        "creatives": creatives,
        "events": events,
        "audiences": audiences,
        "metrics": metrics,
    }
