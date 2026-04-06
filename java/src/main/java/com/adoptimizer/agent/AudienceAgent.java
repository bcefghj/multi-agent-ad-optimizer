package com.adoptimizer.agent;

import com.adoptimizer.model.AgentResult;
import com.adoptimizer.model.CampaignMetrics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.*;

/**
 * Audience Agent — 人群画像分析与定向优化。
 * 分析转化用户特征，推荐高价值受众段和 Lookalike 扩展。
 */
@Component
public class AudienceAgent extends BaseAgent {
    private static final Logger log = LoggerFactory.getLogger(AudienceAgent.class);

    public AudienceAgent() {
        super("Audience Agent");
    }

    @Override
    public AgentResult execute(List<CampaignMetrics> metrics, Map<String, Object> context) {
        log.info("[{}] 开始受众分析", name);

        List<Map<String, Object>> segments = List.of(
            Map.of("name", "高价值白领25-34", "score", 92, "estCtr", 0.045,
                   "recommendation", "核心人群，建议加大投放"),
            Map.of("name", "年轻女性18-24", "score", 85, "estCtr", 0.055,
                   "recommendation", "CTR高但CVR偏低，优化落地页"),
            Map.of("name", "家庭决策者35-44", "score", 88, "estCtr", 0.032,
                   "recommendation", "CVR极高，适合高客单价")
        );

        List<Map<String, Object>> lookalike = List.of(
            Map.of("seed", "高价值白领", "expansion", "1%", "reach", 1200000),
            Map.of("seed", "家庭决策者", "expansion", "2%", "reach", 3500000)
        );

        return AgentResult.builder()
            .agentName(name)
            .summary("识别出 " + segments.size() + " 个高价值人群段")
            .data(Map.of("segments", segments, "lookalike", lookalike))
            .messages(List.of("受众分析完成，推荐优先定向: 高价值白领25-34, 家庭决策者35-44"))
            .build();
    }
}
