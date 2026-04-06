package com.adoptimizer.agent;

import com.adoptimizer.model.AgentResult;
import com.adoptimizer.model.BudgetAllocation;
import com.adoptimizer.model.CampaignMetrics;
import com.adoptimizer.model.OptimizationAction;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.*;

/**
 * Optimize Agent — 整合所有Agent输出，生成最终优化方案。
 * 包括：暂停低效素材、预算再分配、A/B测试管理、告警处理。
 */
@Component
public class OptimizeAgent extends BaseAgent {
    private static final Logger log = LoggerFactory.getLogger(OptimizeAgent.class);
    private static final double SCORE_THRESHOLD = 40.0;

    public OptimizeAgent() {
        super("Optimize Agent");
    }

    @Override
    public AgentResult execute(List<CampaignMetrics> metrics, Map<String, Object> context) {
        log.info("[{}] 开始生成优化方案", name);

        List<OptimizationAction> actions = new ArrayList<>();
        List<BudgetAllocation> allocations = new ArrayList<>();

        // 评估素材表现
        for (CampaignMetrics m : metrics) {
            double score = scoreCreative(m);
            if (score < SCORE_THRESHOLD && m.getImpressions() > 500) {
                actions.add(OptimizationAction.builder()
                    .actionType("pause_creative")
                    .campaignId(m.getCampaignId())
                    .reason(String.format("素材得分 %.1f 低于阈值 %.1f", score, SCORE_THRESHOLD))
                    .confidence(Math.min(score / 100, 0.95))
                    .build());
            }
        }

        // 启发式预算分配
        double totalBudget = metrics.stream().mapToDouble(CampaignMetrics::getTotalCost).sum();
        double totalRoas = metrics.stream().mapToDouble(CampaignMetrics::getRoas).sum();

        for (CampaignMetrics m : metrics) {
            if (m.getTotalCost() <= 0) continue;
            double weight = totalRoas > 0 ? m.getRoas() / totalRoas : 1.0 / metrics.size();
            double recommended = totalBudget * weight;
            double changePct = (recommended - m.getTotalCost()) / m.getTotalCost() * 100;

            String reason = changePct > 5 ? "ROAS较高，建议增加预算"
                : changePct < -5 ? "ROAS较低，建议减少预算"
                : "预算维持不变";

            allocations.add(BudgetAllocation.builder()
                .campaignId(m.getCampaignId())
                .campaignName(m.getCampaignName())
                .currentBudget(m.getTotalCost())
                .recommendedBudget(Math.round(recommended * 100.0) / 100.0)
                .changePct(Math.round(changePct * 10.0) / 10.0)
                .reason(reason)
                .build());

            if (Math.abs(changePct) > 5) {
                actions.add(OptimizationAction.builder()
                    .actionType("adjust_budget")
                    .campaignId(m.getCampaignId())
                    .beforeValue(String.format("¥%.2f", m.getTotalCost()))
                    .afterValue(String.format("¥%.2f", recommended))
                    .reason(reason)
                    .confidence(0.85)
                    .build());
            }
        }

        return AgentResult.builder()
            .agentName(name)
            .summary(String.format("优化方案: %d项操作, %d个预算调整", actions.size(), allocations.size()))
            .data(Map.of("allocations", allocations))
            .actions(actions)
            .messages(List.of(String.format("生成 %d 项优化操作", actions.size())))
            .build();
    }

    private double scoreCreative(CampaignMetrics m) {
        double ctrScore = Math.min(m.getCtr() / 0.05, 1.0) * 40;
        double cvrScore = Math.min(m.getCvr() / 0.1, 1.0) * 35;
        double cpaScore = m.getCpa() < Double.MAX_VALUE
            ? Math.max(1 - m.getCpa() / 200, 0) * 25 : 0;
        return ctrScore + cvrScore + cpaScore;
    }
}
