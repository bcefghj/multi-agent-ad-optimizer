package com.adoptimizer.orchestrator;

import com.adoptimizer.agent.*;
import com.adoptimizer.model.AgentResult;
import com.adoptimizer.model.CampaignMetrics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.stream.Collectors;

/**
 * Agent Supervisor — Supervisor Pattern 编排层。
 *
 * 流程:
 * 1. Monitor → 采集指标、检测异常
 * 2. Audience + Creative → 并行执行（受众分析 & 创意生成）
 * 3. Bidding → 竞价策略优化
 * 4. Optimize → 整合输出，生成方案
 * 5. 若有告警且未达最大迭代 → 回到步骤1
 */
@Service
public class AgentSupervisor {
    private static final Logger log = LoggerFactory.getLogger(AgentSupervisor.class);

    private final MonitorAgent monitorAgent;
    private final AudienceAgent audienceAgent;
    private final CreativeAgent creativeAgent;
    private final BiddingAgent biddingAgent;
    private final OptimizeAgent optimizeAgent;
    private final ExecutorService executor = Executors.newFixedThreadPool(4);

    public AgentSupervisor(
        MonitorAgent monitorAgent,
        AudienceAgent audienceAgent,
        CreativeAgent creativeAgent,
        BiddingAgent biddingAgent,
        OptimizeAgent optimizeAgent
    ) {
        this.monitorAgent = monitorAgent;
        this.audienceAgent = audienceAgent;
        this.creativeAgent = creativeAgent;
        this.biddingAgent = biddingAgent;
        this.optimizeAgent = optimizeAgent;
    }

    public Map<String, Object> runPipeline(List<CampaignMetrics> metrics, int maxIterations) {
        log.info("Supervisor启动, campaigns={}, maxIter={}", metrics.size(), maxIterations);

        Map<String, Object> context = new HashMap<>();
        List<AgentResult> allResults = new ArrayList<>();

        for (int i = 0; i < maxIterations; i++) {
            log.info("=== 迭代 {} ===", i + 1);

            // Step 1: Monitor
            AgentResult monitorResult = monitorAgent.execute(metrics, context);
            allResults.add(monitorResult);
            context.put("monitor", monitorResult);

            // Step 2: Audience + Creative 并行
            CompletableFuture<AgentResult> audienceFuture =
                CompletableFuture.supplyAsync(() -> audienceAgent.execute(metrics, context), executor);
            CompletableFuture<AgentResult> creativeFuture =
                CompletableFuture.supplyAsync(() -> creativeAgent.execute(metrics, context), executor);

            AgentResult audienceResult = audienceFuture.join();
            AgentResult creativeResult = creativeFuture.join();
            allResults.add(audienceResult);
            allResults.add(creativeResult);
            context.put("audience", audienceResult);
            context.put("creative", creativeResult);

            // Step 3: Bidding
            AgentResult biddingResult = biddingAgent.execute(metrics, context);
            allResults.add(biddingResult);
            context.put("bidding", biddingResult);

            // Step 4: Optimize
            AgentResult optimizeResult = optimizeAgent.execute(metrics, context);
            allResults.add(optimizeResult);
            context.put("optimize", optimizeResult);

            // 检查是否继续
            @SuppressWarnings("unchecked")
            List<String> alerts = (List<String>) monitorResult.getData().getOrDefault("alerts", List.of());
            if (alerts.isEmpty()) {
                log.info("无告警，结束迭代");
                break;
            }
        }

        return Map.of(
            "iterations", allResults.size() / 5,
            "results", allResults,
            "messages", allResults.stream()
                .flatMap(r -> r.getMessages().stream())
                .collect(Collectors.toList()),
            "summary", generateSummary(allResults)
        );
    }

    private String generateSummary(List<AgentResult> results) {
        StringBuilder sb = new StringBuilder();
        sb.append("=== 多Agent广告优化执行报告 ===\n");
        for (AgentResult r : results) {
            sb.append(String.format("[%s] %s\n", r.getAgentName(), r.getSummary()));
        }
        return sb.toString();
    }
}
