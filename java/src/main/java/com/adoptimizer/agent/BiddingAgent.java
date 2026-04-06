package com.adoptimizer.agent;

import com.adoptimizer.model.AgentResult;
import com.adoptimizer.model.CampaignMetrics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.*;

/**
 * Bidding Agent — 实时竞价策略优化。
 * 基于 eCPM 预估计算最优出价，在 ROI 约束下最大化转化。
 */
@Component
public class BiddingAgent extends BaseAgent {
    private static final Logger log = LoggerFactory.getLogger(BiddingAgent.class);
    private static final double TARGET_ROAS = 2.0;

    public BiddingAgent() {
        super("Bidding Agent");
    }

    @Override
    public AgentResult execute(List<CampaignMetrics> metrics, Map<String, Object> context) {
        log.info("[{}] 开始竞价策略优化", name);

        List<Map<String, Object>> decisions = new ArrayList<>();
        List<String> messages = new ArrayList<>();

        for (CampaignMetrics m : metrics) {
            double predCtr = m.getCtr() > 0 ? m.getCtr() : 0.03;
            double predCvr = m.getCvr() > 0 ? m.getCvr() : 0.05;
            double targetCpa = m.getCpa() < Double.MAX_VALUE ? m.getCpa() : 100.0;

            double ecpm = predCtr * predCvr * targetCpa * 1000;
            double multiplier = calculateMultiplier(m.getRoas());
            double bid = Math.max(0.01, Math.min(ecpm / 1000 * multiplier, targetCpa * 0.8));

            String reasoning = m.getRoas() > TARGET_ROAS * 1.5
                ? "ROAS优秀，适当提价争量"
                : m.getRoas() < TARGET_ROAS * 0.5
                    ? "ROAS偏低，降价控成本"
                    : "ROAS合理，维持策略";

            decisions.add(Map.of(
                "campaignId", m.getCampaignId(),
                "recommendedBid", Math.round(bid * 100.0) / 100.0,
                "multiplier", Math.round(multiplier * 100.0) / 100.0,
                "ecpm", Math.round(ecpm * 100.0) / 100.0,
                "reasoning", reasoning
            ));

            messages.add(String.format("Campaign %s: bid=¥%.2f, eCPM=%.2f, %s",
                m.getCampaignId(), bid, ecpm, reasoning));
        }

        return AgentResult.builder()
            .agentName(name)
            .summary("优化了 " + decisions.size() + " 个Campaign的出价策略")
            .data(Map.of("decisions", decisions))
            .messages(messages)
            .build();
    }

    private double calculateMultiplier(double roas) {
        double ratio = roas / TARGET_ROAS;
        if (ratio > 2.0) return 1.3;
        if (ratio > 1.2) return 1.1;
        if (ratio > 0.8) return 1.0;
        if (ratio > 0.5) return 0.8;
        return 0.6;
    }
}
