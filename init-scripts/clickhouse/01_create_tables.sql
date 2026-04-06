CREATE DATABASE IF NOT EXISTS ad_optimizer;

-- 广告活动表
CREATE TABLE IF NOT EXISTS ad_optimizer.campaigns
(
    campaign_id    String,
    campaign_name  String,
    platform       Enum8('google' = 1, 'meta' = 2, 'tiktok' = 3),
    status         Enum8('active' = 1, 'paused' = 2, 'completed' = 3),
    daily_budget   Float64,
    total_budget   Float64,
    start_date     Date,
    end_date       Nullable(Date),
    target_audience String,
    created_at     DateTime DEFAULT now(),
    updated_at     DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (campaign_id);

-- 广告创意素材表
CREATE TABLE IF NOT EXISTS ad_optimizer.creatives
(
    creative_id    String,
    campaign_id    String,
    creative_type  Enum8('text' = 1, 'image' = 2, 'video' = 3),
    headline       String,
    description    String,
    cta_text       String,
    status         Enum8('active' = 1, 'paused' = 2, 'rejected' = 3),
    ab_group       String DEFAULT 'control',
    created_at     DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(created_at)
ORDER BY (creative_id, campaign_id);

-- 广告投放事件表（核心指标追踪）
CREATE TABLE IF NOT EXISTS ad_optimizer.ad_events
(
    event_id       String,
    campaign_id    String,
    creative_id    String,
    event_type     Enum8('impression' = 1, 'click' = 2, 'conversion' = 3),
    cost           Float64,
    revenue        Float64,
    platform       Enum8('google' = 1, 'meta' = 2, 'tiktok' = 3),
    device         Enum8('mobile' = 1, 'desktop' = 2, 'tablet' = 3),
    country        String,
    age_group      String,
    gender         Enum8('male' = 1, 'female' = 2, 'unknown' = 3),
    event_time     DateTime
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_time)
ORDER BY (campaign_id, creative_id, event_time);

-- 实时聚合物化视图：按campaign+creative维度统计
CREATE MATERIALIZED VIEW IF NOT EXISTS ad_optimizer.campaign_creative_stats_mv
ENGINE = SummingMergeTree()
ORDER BY (campaign_id, creative_id, stat_date)
AS SELECT
    campaign_id,
    creative_id,
    toDate(event_time) AS stat_date,
    countIf(event_type = 'impression') AS impressions,
    countIf(event_type = 'click') AS clicks,
    countIf(event_type = 'conversion') AS conversions,
    sumIf(cost, event_type = 'impression') AS total_cost,
    sumIf(revenue, event_type = 'conversion') AS total_revenue
FROM ad_optimizer.ad_events
GROUP BY campaign_id, creative_id, stat_date;

-- 实时聚合物化视图：按小时维度统计（用于实时监控）
CREATE MATERIALIZED VIEW IF NOT EXISTS ad_optimizer.hourly_stats_mv
ENGINE = SummingMergeTree()
ORDER BY (campaign_id, stat_hour)
AS SELECT
    campaign_id,
    toStartOfHour(event_time) AS stat_hour,
    countIf(event_type = 'impression') AS impressions,
    countIf(event_type = 'click') AS clicks,
    countIf(event_type = 'conversion') AS conversions,
    sumIf(cost, event_type = 'impression') AS total_cost,
    sumIf(revenue, event_type = 'conversion') AS total_revenue
FROM ad_optimizer.ad_events
GROUP BY campaign_id, stat_hour;

-- 受众画像表
CREATE TABLE IF NOT EXISTS ad_optimizer.audience_profiles
(
    audience_id    String,
    segment_name   String,
    age_range      String,
    gender         String,
    interests      Array(String),
    location       String,
    device_pref    String,
    estimated_size UInt64,
    avg_ctr        Float64,
    avg_cvr        Float64,
    created_at     DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(created_at)
ORDER BY (audience_id);

-- 竞价日志表
CREATE TABLE IF NOT EXISTS ad_optimizer.bid_logs
(
    bid_id         String,
    campaign_id    String,
    creative_id    String,
    bid_amount     Float64,
    win_price      Float64,
    is_won         UInt8,
    predicted_ctr  Float64,
    predicted_cvr  Float64,
    ecpm           Float64,
    bid_time       DateTime
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(bid_time)
ORDER BY (campaign_id, bid_time);

-- 优化操作日志表
CREATE TABLE IF NOT EXISTS ad_optimizer.optimization_logs
(
    log_id         String,
    campaign_id    String,
    agent_name     String,
    action_type    String,
    action_detail  String,
    before_value   String,
    after_value    String,
    reason         String,
    created_at     DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (campaign_id, created_at);
