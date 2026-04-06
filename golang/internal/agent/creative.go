package agent

import (
	"fmt"
	"math/rand"
	"strings"

	"github.com/bcefghj/multi-agent-ad-optimizer/internal/model"
)

// CreativeAgent 创意生成Agent
type CreativeAgent struct{}

func NewCreativeAgent() *CreativeAgent { return &CreativeAgent{} }
func (a *CreativeAgent) Name() string  { return "Creative Agent" }

var emotionKeywords = map[string][]string{
	"urgency":   {"限时特惠", "最后机会", "倒计时"},
	"trust":     {"万人好评", "品质保障", "专业认证"},
	"curiosity": {"揭秘", "你不知道的", "真相"},
	"benefit":   {"立省", "轻松获得", "一步到位"},
}

func (a *CreativeAgent) Execute(metrics []model.CampaignMetrics, ctx map[string]interface{}) model.AgentResult {
	var variants []map[string]interface{}
	var messages []string

	for _, m := range metrics {
		emotions := []string{"benefit", "trust"}
		if m.CTR() < 0.03 {
			emotions = []string{"urgency", "curiosity"}
		}

		parts := strings.SplitN(m.CampaignName, " - ", 2)
		product := parts[0]

		for _, emo := range emotions {
			kws := emotionKeywords[emo]
			kw := kws[rand.Intn(len(kws))]
			variants = append(variants, map[string]interface{}{
				"campaign_id": m.CampaignID,
				"headline":    fmt.Sprintf("%s！%s专属福利", kw, product),
				"description": fmt.Sprintf("%s，品质生活从此开始", product),
				"emotion":     emo,
				"ab_group":    fmt.Sprintf("variant_%s", emo),
			})
		}
		messages = append(messages, fmt.Sprintf("Campaign %s: 生成 %d 个变体 (CTR=%.2f%%)",
			m.CampaignID, len(emotions), m.CTR()*100))
	}

	return model.AgentResult{
		AgentName: a.Name(),
		Summary:   fmt.Sprintf("生成了 %d 个创意变体", len(variants)),
		Data:      map[string]interface{}{"variants": variants},
		Messages:  messages,
	}
}
