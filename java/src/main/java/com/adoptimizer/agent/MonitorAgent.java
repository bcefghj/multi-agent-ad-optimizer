package com.adoptimizer.agent;

import com.adoptimizer.model.AgentResult;
import com.adoptimizer.model.CampaignMetrics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.*;

/**
 * Monitor Agent — 实时追踪投放效果，异常检测与告警。
 */
@Component
public class MonitorAgent extends BaseAgent {
    private static final Logger log = LoggerFactory.getLogger(MonitorAgent.class);
    private static final double CTR_THRESHOLD = 0.005;
    private static final double CPA_CEILING = 200.0;
    private static final double ROAS_FLOOR = 1.0;

    public MonitorAgent() {
        super("Monitor Agent");
    }

    @Override
    public AgentResult execute(List<CampaignMetrics> metrics, Map<String, Object> context) {
        log.info("[{}] 开始监控检查, campaigns={}", name, metrics.size());

        List<String> alerts = new ArrayList<>();
        List<String> messages = new ArrayList<>();

        for (CampaignMetrics m : metrics) {
            if (m.getImpressions() > 100 && m.getCtr() < CTR_THRESHOLD) {
                alerts.add(String.format("Campaign %s CTR (%.2f%%) 低于阈值 (%.2f%%)",
                    m.getCampaignId(), m.getCtr() * 100, CTR_THRESHOLD * 100));
            }
            if (m.getConversions() > 0 && m.getCpa() > CPA_CEILING) {
                alerts.add(String.format("Campaign %s CPA (¥%.2f) 超过上限 (¥%.2f)",
                    m.getCampaignId(), m.getCpa(), CPA_CEILING));
            }
            if (m.getTotalCost() > 100 && m.getRoas() < ROAS_FLOOR) {
                alerts.add(String.format("Campaign %s ROAS (%.2f) 低于目标 (%.2f)",
                    m.getCampaignId(), m.getRoas(), ROAS_FLOOR));
            }
        }

        String status = alerts.isEmpty() ? "健康" : "异常";
        messages.add(String.format("系统状态【%s】，监控 %d 个Campaign，发现 %d 个异常",
            status, metrics.size(), alerts.size()));

        return AgentResult.builder()
            .agentName(name)
            .summary(String.format("监控完成: %s, %d个告警", status, alerts.size()))
            .data(Map.of("alerts", alerts, "status", status))
            .messages(messages)
            .build();
    }
}
