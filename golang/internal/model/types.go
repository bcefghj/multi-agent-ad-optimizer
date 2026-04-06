package model

import "math"

// CampaignMetrics 广告活动聚合指标
type CampaignMetrics struct {
	CampaignID   string  `json:"campaign_id"`
	CampaignName string  `json:"campaign_name"`
	Impressions  int64   `json:"impressions"`
	Clicks       int64   `json:"clicks"`
	Conversions  int64   `json:"conversions"`
	TotalCost    float64 `json:"total_cost"`
	TotalRevenue float64 `json:"total_revenue"`
}

func (m *CampaignMetrics) CTR() float64 {
	if m.Impressions == 0 {
		return 0
	}
	return float64(m.Clicks) / float64(m.Impressions)
}

func (m *CampaignMetrics) CVR() float64 {
	if m.Clicks == 0 {
		return 0
	}
	return float64(m.Conversions) / float64(m.Clicks)
}

func (m *CampaignMetrics) CPA() float64 {
	if m.Conversions == 0 {
		return math.MaxFloat64
	}
	return m.TotalCost / float64(m.Conversions)
}

func (m *CampaignMetrics) ROAS() float64 {
	if m.TotalCost == 0 {
		return 0
	}
	return m.TotalRevenue / m.TotalCost
}

// AgentResult Agent执行结果
type AgentResult struct {
	AgentName string                 `json:"agent_name"`
	Summary   string                 `json:"summary"`
	Data      map[string]interface{} `json:"data"`
	Messages  []string               `json:"messages"`
	Actions   []OptimizationAction   `json:"actions,omitempty"`
}

// OptimizationAction 优化操作
type OptimizationAction struct {
	ActionType  string  `json:"action_type"`
	CampaignID  string  `json:"campaign_id"`
	TargetID    string  `json:"target_id,omitempty"`
	BeforeValue string  `json:"before_value,omitempty"`
	AfterValue  string  `json:"after_value,omitempty"`
	Reason      string  `json:"reason"`
	Confidence  float64 `json:"confidence"`
}

// BudgetAllocation 预算分配
type BudgetAllocation struct {
	CampaignID        string  `json:"campaign_id"`
	CampaignName      string  `json:"campaign_name"`
	CurrentBudget     float64 `json:"current_budget"`
	RecommendedBudget float64 `json:"recommended_budget"`
	ChangePct         float64 `json:"change_pct"`
	Reason            string  `json:"reason"`
}

// BiddingDecision 竞价决策
type BiddingDecision struct {
	CampaignID     string  `json:"campaign_id"`
	RecommendedBid float64 `json:"recommended_bid"`
	Multiplier     float64 `json:"multiplier"`
	ECPM           float64 `json:"ecpm"`
	Reasoning      string  `json:"reasoning"`
}

// PipelineResult 完整管道执行结果
type PipelineResult struct {
	Iterations int           `json:"iterations"`
	Results    []AgentResult `json:"results"`
	Messages   []string      `json:"messages"`
	Summary    string        `json:"summary"`
}
