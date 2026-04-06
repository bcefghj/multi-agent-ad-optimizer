package com.adoptimizer.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.List;
import java.util.Map;

/**
 * Agent 执行结果的统一封装。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AgentResult {
    private String agentName;
    private String summary;
    private Map<String, Object> data;
    private List<String> messages;
    private List<OptimizationAction> actions;
}
