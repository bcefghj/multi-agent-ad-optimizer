package com.adoptimizer.config;

import com.adoptimizer.model.CampaignMetrics;
import com.adoptimizer.orchestrator.AgentSupervisor;
import com.adoptimizer.service.MockDataService;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * REST API 控制器 — 广告优化系统的对外接口。
 */
@RestController
@RequestMapping("/api/v1")
public class AdOptimizerController {

    private final AgentSupervisor supervisor;
    private final MockDataService mockDataService;

    public AdOptimizerController(AgentSupervisor supervisor, MockDataService mockDataService) {
        this.supervisor = supervisor;
        this.mockDataService = mockDataService;
    }

    @PostMapping("/optimize")
    public Map<String, Object> runOptimization(
        @RequestParam(defaultValue = "5") int campaignCount,
        @RequestParam(defaultValue = "2") int maxIterations
    ) {
        List<CampaignMetrics> metrics = mockDataService.generateMetrics(campaignCount);
        return supervisor.runPipeline(metrics, maxIterations);
    }

    @GetMapping("/metrics")
    public List<CampaignMetrics> getMetrics(
        @RequestParam(defaultValue = "5") int count
    ) {
        return mockDataService.generateMetrics(count);
    }

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "UP", "service", "Multi-Agent Ad Optimizer (Java)");
    }
}
