"""ClickHouse 数据访问层 — 封装所有数据库操作."""

from __future__ import annotations

import os
from typing import Any

import structlog

logger = structlog.get_logger()

# 当 clickhouse-connect 不可用时退回到 mock 模式
try:
    import clickhouse_connect
    HAS_CLICKHOUSE = True
except ImportError:
    HAS_CLICKHOUSE = False


class ClickHouseClient:
    """ClickHouse 读写封装，支持 mock 和 live 两种模式."""

    def __init__(self) -> None:
        self.mode = os.getenv("RUN_MODE", "mock")
        self._client = None

        if self.mode == "live" and HAS_CLICKHOUSE:
            self._client = clickhouse_connect.get_client(
                host=os.getenv("CLICKHOUSE_HOST", "localhost"),
                port=int(os.getenv("CLICKHOUSE_HTTP_PORT", "8123")),
                username=os.getenv("CLICKHOUSE_USER", "default"),
                password=os.getenv("CLICKHOUSE_PASSWORD", ""),
                database=os.getenv("CLICKHOUSE_DATABASE", "ad_optimizer"),
            )
            logger.info("clickhouse_connected", mode="live")
        else:
            logger.info("clickhouse_mock_mode", reason="mock mode or driver not installed")

    # ──────────── 通用查询 ────────────

    def query(self, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
        if self._client is None:
            return []
        result = self._client.query(sql, parameters=params or {})
        columns = result.column_names
        return [dict(zip(columns, row)) for row in result.result_rows]

    def execute(self, sql: str, params: dict | None = None) -> None:
        if self._client is None:
            return
        self._client.command(sql, parameters=params or {})

    # ──────────── Campaign 指标查询 ────────────

    def get_campaign_metrics(self, campaign_ids: list[str] | None = None) -> list[dict]:
        """从物化视图查询 campaign 级别的聚合指标."""
        where = ""
        if campaign_ids:
            ids = ", ".join(f"'{cid}'" for cid in campaign_ids)
            where = f"WHERE campaign_id IN ({ids})"

        sql = f"""
        SELECT
            campaign_id,
            sum(impressions)  AS impressions,
            sum(clicks)       AS clicks,
            sum(conversions)  AS conversions,
            sum(total_cost)   AS total_cost,
            sum(total_revenue) AS total_revenue
        FROM campaign_creative_stats_mv
        {where}
        GROUP BY campaign_id
        """
        return self.query(sql)

    def get_creative_metrics(self, campaign_id: str) -> list[dict]:
        """查询单个 campaign 下各 creative 的指标."""
        sql = """
        SELECT
            creative_id,
            sum(impressions)  AS impressions,
            sum(clicks)       AS clicks,
            sum(conversions)  AS conversions,
            sum(total_cost)   AS total_cost,
            sum(total_revenue) AS total_revenue
        FROM campaign_creative_stats_mv
        WHERE campaign_id = %(cid)s
        GROUP BY creative_id
        ORDER BY clicks DESC
        """
        return self.query(sql, {"cid": campaign_id})

    def get_hourly_trend(self, campaign_id: str, hours: int = 24) -> list[dict]:
        """查询最近N小时的趋势数据."""
        sql = """
        SELECT
            stat_hour,
            sum(impressions)  AS impressions,
            sum(clicks)       AS clicks,
            sum(conversions)  AS conversions,
            sum(total_cost)   AS total_cost,
            sum(total_revenue) AS total_revenue
        FROM hourly_stats_mv
        WHERE campaign_id = %(cid)s
          AND stat_hour >= now() - INTERVAL %(hrs)s HOUR
        GROUP BY stat_hour
        ORDER BY stat_hour
        """
        return self.query(sql, {"cid": campaign_id, "hrs": hours})

    # ──────────── 受众分析查询 ────────────

    def get_audience_breakdown(self, campaign_id: str) -> dict:
        """按年龄/性别/设备分析受众特征."""
        age_sql = """
        SELECT age_group, count() AS cnt,
               countIf(event_type = 'click') AS clicks,
               countIf(event_type = 'conversion') AS conversions
        FROM ad_events
        WHERE campaign_id = %(cid)s
        GROUP BY age_group ORDER BY cnt DESC
        """
        device_sql = """
        SELECT device, count() AS cnt,
               countIf(event_type = 'click') AS clicks
        FROM ad_events
        WHERE campaign_id = %(cid)s
        GROUP BY device ORDER BY cnt DESC
        """
        return {
            "by_age": self.query(age_sql, {"cid": campaign_id}),
            "by_device": self.query(device_sql, {"cid": campaign_id}),
        }

    # ──────────── 写入操作 ────────────

    def insert_events(self, events: list[dict]) -> None:
        if self._client is None or not events:
            return
        columns = list(events[0].keys())
        data = [list(e.values()) for e in events]
        self._client.insert("ad_events", data, column_names=columns)

    def insert_bid_logs(self, logs: list[dict]) -> None:
        if self._client is None or not logs:
            return
        columns = list(logs[0].keys())
        data = [list(l.values()) for l in logs]
        self._client.insert("bid_logs", data, column_names=columns)
