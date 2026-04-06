package agent

import "github.com/bcefghj/multi-agent-ad-optimizer/internal/model"

// Agent 接口 — 所有Agent必须实现
type Agent interface {
	Name() string
	Execute(metrics []model.CampaignMetrics, ctx map[string]interface{}) model.AgentResult
}
