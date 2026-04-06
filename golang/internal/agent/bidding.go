package agent

import (
	"fmt"
	"math"

	"github.com/bcefghj/multi-agent-ad-optimizer/internal/model"
)

// BiddingAgent 竞价策略Agent
type BiddingAgent struct {
	TargetROAS float64
}

func NewBiddingAgent() *BiddingAgent { return &BiddingAgent{TargetROAS: 2.0} }
func (a *BiddingAgent) Name() string { return "Bidding Agent" }

func (a *BiddingAgent) Execute(metrics []model.CampaignMetrics, ctx map[string]interface{}) model.AgentResult {
	var decisions []model.BiddingDecision
	var messages []string

	for _, m := range metrics {
		predCTR := m.CTR()
		if predCTR == 0 {
			predCTR = 0.03
		}
		predCVR := m.CVR()
		if predCVR == 0 {
			predCVR = 0.05
		}
		targetCPA := m.CPA()
		if targetCPA >= math.MaxFloat64 {
			targetCPA = 100.0
		}

		ecpm := predCTR * predCVR * targetCPA * 1000
		mult := a.multiplier(m.ROAS())
		bid := math.Max(0.01, math.Min(ecpm/1000*mult, targetCPA*0.8))

		reasoning := "ROAS合理，维持策略"
		if m.ROAS() > a.TargetROAS*1.5 {
			reasoning = "ROAS优秀，适当提价争量"
		} else if m.ROAS() < a.TargetROAS*0.5 {
			reasoning = "ROAS偏低，降价控成本"
		}

		decisions = append(decisions, model.BiddingDecision{
			CampaignID:     m.CampaignID,
			RecommendedBid: math.Round(bid*100) / 100,
			Multiplier:     math.Round(mult*100) / 100,
			ECPM:           math.Round(ecpm*100) / 100,
			Reasoning:      reasoning,
		})

		messages = append(messages, fmt.Sprintf("Campaign %s: bid=¥%.2f, eCPM=%.2f",
			m.CampaignID, bid, ecpm))
	}

	return model.AgentResult{
		AgentName: a.Name(),
		Summary:   fmt.Sprintf("优化了 %d 个Campaign出价", len(decisions)),
		Data:      map[string]interface{}{"decisions": decisions},
		Messages:  messages,
	}
}

func (a *BiddingAgent) multiplier(roas float64) float64 {
	ratio := roas / a.TargetROAS
	switch {
	case ratio > 2.0:
		return 1.3
	case ratio > 1.2:
		return 1.1
	case ratio > 0.8:
		return 1.0
	case ratio > 0.5:
		return 0.8
	default:
		return 0.6
	}
}
