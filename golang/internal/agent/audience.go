package agent

import (
	"fmt"

	"github.com/bcefghj/multi-agent-ad-optimizer/internal/model"
)

// AudienceAgent 受众分析Agent
type AudienceAgent struct{}

func NewAudienceAgent() *AudienceAgent { return &AudienceAgent{} }
func (a *AudienceAgent) Name() string  { return "Audience Agent" }

func (a *AudienceAgent) Execute(metrics []model.CampaignMetrics, ctx map[string]interface{}) model.AgentResult {
	segments := []map[string]interface{}{
		{"name": "高价值白领25-34", "score": 92, "est_ctr": 0.045, "recommendation": "核心人群，建议加大投放"},
		{"name": "年轻女性18-24", "score": 85, "est_ctr": 0.055, "recommendation": "CTR高CVR偏低，优化落地页"},
		{"name": "家庭决策者35-44", "score": 88, "est_ctr": 0.032, "recommendation": "CVR极高，适合高客单价"},
	}

	return model.AgentResult{
		AgentName: a.Name(),
		Summary:   fmt.Sprintf("识别出 %d 个高价值人群段", len(segments)),
		Data:      map[string]interface{}{"segments": segments},
		Messages:  []string{"受众分析完成，推荐定向: 高价值白领25-34, 家庭决策者35-44"},
	}
}
