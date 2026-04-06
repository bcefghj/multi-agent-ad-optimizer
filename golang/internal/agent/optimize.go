package agent

import (
	"fmt"
	"math"

	"github.com/bcefghj/multi-agent-ad-optimizer/internal/model"
)

// OptimizeAgent 优化Agent
type OptimizeAgent struct {
	ScoreThreshold float64
}

func NewOptimizeAgent() *OptimizeAgent { return &OptimizeAgent{ScoreThreshold: 40.0} }
func (a *OptimizeAgent) Name() string  { return "Optimize Agent" }

func (a *OptimizeAgent) Execute(metrics []model.CampaignMetrics, ctx map[string]interface{}) model.AgentResult {
	var actions []model.OptimizationAction
	var allocations []model.BudgetAllocation

	for _, m := range metrics {
		score := a.scoreCreative(m)
		if score < a.ScoreThreshold && m.Impressions > 500 {
			actions = append(actions, model.OptimizationAction{
				ActionType: "pause_creative",
				CampaignID: m.CampaignID,
				Reason:     fmt.Sprintf("素材得分 %.1f 低于阈值 %.1f", score, a.ScoreThreshold),
				Confidence: math.Min(score/100, 0.95),
			})
		}
	}

	var totalBudget, totalROAS float64
	for _, m := range metrics {
		totalBudget += m.TotalCost
		totalROAS += m.ROAS()
	}

	for _, m := range metrics {
		if m.TotalCost <= 0 {
			continue
		}
		weight := m.ROAS() / totalROAS
		if totalROAS == 0 {
			weight = 1.0 / float64(len(metrics))
		}
		recommended := totalBudget * weight
		changePct := (recommended - m.TotalCost) / m.TotalCost * 100

		reason := "预算维持不变"
		if changePct > 5 {
			reason = "ROAS较高，建议增加预算"
		} else if changePct < -5 {
			reason = "ROAS较低，建议减少预算"
		}

		allocations = append(allocations, model.BudgetAllocation{
			CampaignID:        m.CampaignID,
			CampaignName:      m.CampaignName,
			CurrentBudget:     m.TotalCost,
			RecommendedBudget: math.Round(recommended*100) / 100,
			ChangePct:         math.Round(changePct*10) / 10,
			Reason:            reason,
		})

		if math.Abs(changePct) > 5 {
			actions = append(actions, model.OptimizationAction{
				ActionType:  "adjust_budget",
				CampaignID:  m.CampaignID,
				BeforeValue: fmt.Sprintf("¥%.2f", m.TotalCost),
				AfterValue:  fmt.Sprintf("¥%.2f", recommended),
				Reason:      reason,
				Confidence:  0.85,
			})
		}
	}

	return model.AgentResult{
		AgentName: a.Name(),
		Summary:   fmt.Sprintf("优化方案: %d项操作, %d个预算调整", len(actions), len(allocations)),
		Data:      map[string]interface{}{"allocations": allocations},
		Actions:   actions,
		Messages:  []string{fmt.Sprintf("生成 %d 项优化操作", len(actions))},
	}
}

func (a *OptimizeAgent) scoreCreative(m model.CampaignMetrics) float64 {
	ctrScore := math.Min(m.CTR()/0.05, 1.0) * 40
	cvrScore := math.Min(m.CVR()/0.1, 1.0) * 35
	var cpaScore float64
	if m.CPA() < math.MaxFloat64 {
		cpaScore = math.Max(1-m.CPA()/200, 0) * 25
	}
	return ctrScore + cvrScore + cpaScore
}
