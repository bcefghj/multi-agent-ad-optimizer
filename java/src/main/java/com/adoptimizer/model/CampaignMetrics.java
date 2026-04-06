package com.adoptimizer.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Campaign 聚合指标 — 所有 Agent 共享的核心数据模型。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CampaignMetrics {
    private String campaignId;
    private String campaignName;
    private long impressions;
    private long clicks;
    private long conversions;
    private double totalCost;
    private double totalRevenue;

    public double getCtr() {
        return impressions > 0 ? (double) clicks / impressions : 0.0;
    }

    public double getCvr() {
        return clicks > 0 ? (double) conversions / clicks : 0.0;
    }

    public double getCpa() {
        return conversions > 0 ? totalCost / conversions : Double.MAX_VALUE;
    }

    public double getRoas() {
        return totalCost > 0 ? totalRevenue / totalCost : 0.0;
    }
}
