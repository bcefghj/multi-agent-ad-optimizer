package com.adoptimizer.service;

import com.adoptimizer.model.CampaignMetrics;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Random;

/**
 * 模拟数据服务 — 生成演示用的广告投放数据。
 */
@Service
public class MockDataService {
    private static final Random RANDOM = new Random(42);
    private static final String[] PRODUCTS = {
        "智能手表Pro", "AI学习助手", "健康膳食包", "电动牙刷X1", "无线降噪耳机"
    };
    private static final String[] PLATFORMS = {"google", "meta", "tiktok"};

    public List<CampaignMetrics> generateMetrics(int count) {
        return java.util.stream.IntStream.rangeClosed(1, count)
            .mapToObj(i -> {
                long impressions = 5000 + RANDOM.nextInt(95000);
                long clicks = (long) (impressions * (0.01 + RANDOM.nextDouble() * 0.06));
                long conversions = (long) (clicks * (0.02 + RANDOM.nextDouble() * 0.1));
                double cost = impressions * 0.01 + clicks * (0.5 + RANDOM.nextDouble() * 4.5);
                double revenue = conversions * (20 + RANDOM.nextDouble() * 180);

                return CampaignMetrics.builder()
                    .campaignId(String.format("camp_%03d", i))
                    .campaignName(PRODUCTS[i % PRODUCTS.length] + " - " + PLATFORMS[i % PLATFORMS.length])
                    .impressions(impressions)
                    .clicks(clicks)
                    .conversions(conversions)
                    .totalCost(Math.round(cost * 100.0) / 100.0)
                    .totalRevenue(Math.round(revenue * 100.0) / 100.0)
                    .build();
            })
            .toList();
    }
}
