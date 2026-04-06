"""广告平台 API 封装 — 支持 mock 和真实 API 两种模式."""

from __future__ import annotations

import os
import random
import structlog
from typing import Any

from ..models.schemas import Campaign, Creative, Platform

logger = structlog.get_logger()


class AdsAPIClient:
    """统一的广告平台 API 客户端."""

    def __init__(self) -> None:
        self.mode = os.getenv("RUN_MODE", "mock")
        logger.info("ads_api_init", mode=self.mode)

    def create_campaign(self, campaign: Campaign) -> dict[str, Any]:
        if self.mode == "mock":
            return self._mock_create_campaign(campaign)
        if campaign.platform == Platform.GOOGLE:
            return self._google_create_campaign(campaign)
        return self._meta_create_campaign(campaign)

    def update_campaign_budget(self, campaign_id: str, new_budget: float, platform: Platform) -> dict:
        if self.mode == "mock":
            logger.info("mock_budget_update", campaign_id=campaign_id, new_budget=new_budget)
            return {"success": True, "campaign_id": campaign_id, "new_budget": new_budget}
        raise NotImplementedError(f"Live API for {platform} not implemented")

    def pause_creative(self, creative_id: str, campaign_id: str, platform: Platform) -> dict:
        if self.mode == "mock":
            logger.info("mock_pause_creative", creative_id=creative_id)
            return {"success": True, "creative_id": creative_id, "status": "paused"}
        raise NotImplementedError(f"Live API for {platform} not implemented")

    def create_creative(self, creative: Creative, platform: Platform) -> dict:
        if self.mode == "mock":
            logger.info("mock_create_creative", creative_id=creative.creative_id)
            return {"success": True, "creative_id": creative.creative_id}
        raise NotImplementedError(f"Live API for {platform} not implemented")

    def get_campaign_report(self, campaign_id: str, platform: Platform) -> dict:
        """拉取广告平台的原始报告数据."""
        if self.mode == "mock":
            return {
                "campaign_id": campaign_id,
                "impressions": random.randint(10000, 100000),
                "clicks": random.randint(300, 5000),
                "conversions": random.randint(10, 200),
                "spend": round(random.uniform(500, 5000), 2),
                "revenue": round(random.uniform(1000, 15000), 2),
            }
        raise NotImplementedError(f"Live API for {platform} not implemented")

    # ──────── Mock 实现 ────────

    def _mock_create_campaign(self, campaign: Campaign) -> dict[str, Any]:
        logger.info("mock_create_campaign", campaign_id=campaign.campaign_id)
        return {
            "success": True,
            "campaign_id": campaign.campaign_id,
            "platform_campaign_id": f"ext_{campaign.campaign_id}_{random.randint(1000, 9999)}",
        }

    # ──────── Google Ads 真实 API（占位） ────────

    def _google_create_campaign(self, campaign: Campaign) -> dict:
        """真实环境下调用 Google Ads API。需配置 OAuth2 凭证."""
        raise NotImplementedError(
            "Google Ads API integration requires google-ads library. "
            "See docs/tutorial/01-environment-setup.md"
        )

    # ──────── Meta Marketing API（占位） ────────

    def _meta_create_campaign(self, campaign: Campaign) -> dict:
        """真实环境下调用 Meta Marketing API。需配置 App Token."""
        raise NotImplementedError(
            "Meta Marketing API integration requires facebook-business library. "
            "See docs/tutorial/01-environment-setup.md"
        )
