package com.adoptimizer.agent;

import com.adoptimizer.model.AgentResult;
import com.adoptimizer.model.CampaignMetrics;
import java.util.List;
import java.util.Map;

/**
 * Agent 基类 — 定义所有 Agent 的通用接口和行为。
 */
public abstract class BaseAgent {
    protected final String name;

    protected BaseAgent(String name) {
        this.name = name;
    }

    public abstract AgentResult execute(List<CampaignMetrics> metrics, Map<String, Object> context);

    public String getName() {
        return name;
    }
}
