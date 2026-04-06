package com.adoptimizer.agent;

import com.adoptimizer.model.AgentResult;
import com.adoptimizer.model.CampaignMetrics;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.*;

/**
 * Creative Agent — 自动生成广告文案变体。
 * 根据 CTR/CVR 数据选择不同的文案策略（紧迫感/信任感/好奇心/利益点）。
 */
@Component
public class CreativeAgent extends BaseAgent {
    private static final Logger log = LoggerFactory.getLogger(CreativeAgent.class);

    private static final Map<String, List<String>> EMOTION_KEYWORDS = Map.of(
        "urgency", List.of("限时特惠", "最后机会", "倒计时"),
        "trust", List.of("万人好评", "品质保障", "专业认证"),
        "curiosity", List.of("揭秘", "你不知道的", "真相"),
        "benefit", List.of("立省", "轻松获得", "一步到位")
    );

    public CreativeAgent() {
        super("Creative Agent");
    }

    @Override
    public AgentResult execute(List<CampaignMetrics> metrics, Map<String, Object> context) {
        log.info("[{}] 开始生成创意变体, campaigns={}", name, metrics.size());

        List<Map<String, Object>> variants = new ArrayList<>();
        List<String> messages = new ArrayList<>();

        for (CampaignMetrics m : metrics) {
            List<String> emotions = m.getCtr() < 0.03
                ? List.of("urgency", "curiosity")
                : List.of("benefit", "trust");

            for (String emotion : emotions) {
                List<String> keywords = EMOTION_KEYWORDS.getOrDefault(emotion, List.of("精选"));
                String keyword = keywords.get(new Random().nextInt(keywords.size()));
                String product = m.getCampaignName().split(" - ")[0];

                variants.add(Map.of(
                    "campaignId", m.getCampaignId(),
                    "headline", keyword + "！" + product + "专属福利",
                    "description", product + "，品质生活从此开始",
                    "emotion", emotion,
                    "abGroup", "variant_" + emotion
                ));
            }
            messages.add(String.format("Campaign %s: 生成 %d 个变体 (CTR=%.2f%%)",
                m.getCampaignId(), emotions.size(), m.getCtr() * 100));
        }

        log.info("[{}] 生成完成, total_variants={}", name, variants.size());
        return AgentResult.builder()
            .agentName(name)
            .summary("生成了 " + variants.size() + " 个创意变体")
            .data(Map.of("variants", variants))
            .messages(messages)
            .build();
    }
}
