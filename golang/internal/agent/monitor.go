package agent

import (
	"fmt"

	"github.com/bcefghj/multi-agent-ad-optimizer/internal/model"
)

// MonitorAgent 监控Agent
type MonitorAgent struct {
	CTRThreshold float64
	CPACeiling   float64
	ROASFloor    float64
}

func NewMonitorAgent() *MonitorAgent {
	return &MonitorAgent{CTRThreshold: 0.005, CPACeiling: 200.0, ROASFloor: 1.0}
}
func (a *MonitorAgent) Name() string { return "Monitor Agent" }

func (a *MonitorAgent) Execute(metrics []model.CampaignMetrics, ctx map[string]interface{}) model.AgentResult {
	var alerts []string

	for _, m := range metrics {
		if m.Impressions > 100 && m.CTR() < a.CTRThreshold {
			alerts = append(alerts, fmt.Sprintf("Campaign %s CTR (%.2f%%) 低于阈值",
				m.CampaignID, m.CTR()*100))
		}
		if m.Conversions > 0 && m.CPA() > a.CPACeiling {
			alerts = append(alerts, fmt.Sprintf("Campaign %s CPA (¥%.2f) 超过上限",
				m.CampaignID, m.CPA()))
		}
		if m.TotalCost > 100 && m.ROAS() < a.ROASFloor {
			alerts = append(alerts, fmt.Sprintf("Campaign %s ROAS (%.2f) 低于目标",
				m.CampaignID, m.ROAS()))
		}
	}

	status := "健康"
	if len(alerts) > 0 {
		status = "异常"
	}

	return model.AgentResult{
		AgentName: a.Name(),
		Summary:   fmt.Sprintf("状态: %s, %d个告警", status, len(alerts)),
		Data:      map[string]interface{}{"alerts": alerts, "status": status},
		Messages:  []string{fmt.Sprintf("监控 %d 个Campaign, 发现 %d 个异常", len(metrics), len(alerts))},
	}
}
