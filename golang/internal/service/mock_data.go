package service

import (
	"fmt"
	"math/rand"

	"github.com/bcefghj/multi-agent-ad-optimizer/internal/model"
)

var (
	products  = []string{"智能手表Pro", "AI学习助手", "健康膳食包", "电动牙刷X1", "无线降噪耳机"}
	platforms = []string{"google", "meta", "tiktok"}
)

// GenerateMetrics 生成模拟数据
func GenerateMetrics(count int) []model.CampaignMetrics {
	rng := rand.New(rand.NewSource(42))
	metrics := make([]model.CampaignMetrics, count)

	for i := 0; i < count; i++ {
		impressions := int64(5000 + rng.Intn(95000))
		clicks := int64(float64(impressions) * (0.01 + rng.Float64()*0.06))
		conversions := int64(float64(clicks) * (0.02 + rng.Float64()*0.1))
		cost := float64(impressions)*0.01 + float64(clicks)*(0.5+rng.Float64()*4.5)
		revenue := float64(conversions) * (20 + rng.Float64()*180)

		metrics[i] = model.CampaignMetrics{
			CampaignID:   fmt.Sprintf("camp_%03d", i+1),
			CampaignName: fmt.Sprintf("%s - %s", products[i%len(products)], platforms[i%len(platforms)]),
			Impressions:  impressions,
			Clicks:       clicks,
			Conversions:  conversions,
			TotalCost:    float64(int(cost*100)) / 100,
			TotalRevenue: float64(int(revenue*100)) / 100,
		}
	}
	return metrics
}
