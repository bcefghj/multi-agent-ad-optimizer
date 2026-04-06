package orchestrator

import (
	"fmt"
	"log"
	"strings"
	"sync"

	"github.com/bcefghj/multi-agent-ad-optimizer/internal/agent"
	"github.com/bcefghj/multi-agent-ad-optimizer/internal/model"
)

// Supervisor 编排层：Supervisor Pattern + goroutine 并发
type Supervisor struct {
	monitor  agent.Agent
	audience agent.Agent
	creative agent.Agent
	bidding  agent.Agent
	optimize agent.Agent
}

func NewSupervisor() *Supervisor {
	return &Supervisor{
		monitor:  agent.NewMonitorAgent(),
		audience: agent.NewAudienceAgent(),
		creative: agent.NewCreativeAgent(),
		bidding:  agent.NewBiddingAgent(),
		optimize: agent.NewOptimizeAgent(),
	}
}

// RunPipeline 运行完整的优化闭环
func (s *Supervisor) RunPipeline(metrics []model.CampaignMetrics, maxIter int) model.PipelineResult {
	log.Printf("Supervisor启动: %d campaigns, maxIter=%d", len(metrics), maxIter)

	var allResults []model.AgentResult
	var allMessages []string
	ctx := make(map[string]interface{})

	for i := 0; i < maxIter; i++ {
		log.Printf("=== 迭代 %d ===", i+1)

		// Step 1: Monitor
		monitorResult := s.monitor.Execute(metrics, ctx)
		allResults = append(allResults, monitorResult)
		allMessages = append(allMessages, monitorResult.Messages...)
		ctx["monitor"] = monitorResult

		// Step 2: Audience + Creative 并行（goroutine + WaitGroup）
		var audienceResult, creativeResult model.AgentResult
		var wg sync.WaitGroup
		wg.Add(2)

		go func() {
			defer wg.Done()
			audienceResult = s.audience.Execute(metrics, ctx)
		}()
		go func() {
			defer wg.Done()
			creativeResult = s.creative.Execute(metrics, ctx)
		}()
		wg.Wait()

		allResults = append(allResults, audienceResult, creativeResult)
		allMessages = append(allMessages, audienceResult.Messages...)
		allMessages = append(allMessages, creativeResult.Messages...)
		ctx["audience"] = audienceResult
		ctx["creative"] = creativeResult

		// Step 3: Bidding
		biddingResult := s.bidding.Execute(metrics, ctx)
		allResults = append(allResults, biddingResult)
		allMessages = append(allMessages, biddingResult.Messages...)
		ctx["bidding"] = biddingResult

		// Step 4: Optimize
		optimizeResult := s.optimize.Execute(metrics, ctx)
		allResults = append(allResults, optimizeResult)
		allMessages = append(allMessages, optimizeResult.Messages...)
		ctx["optimize"] = optimizeResult

		// 检查是否继续
		alerts, _ := monitorResult.Data["alerts"].([]string)
		if len(alerts) == 0 {
			log.Println("无告警，结束迭代")
			break
		}
	}

	return model.PipelineResult{
		Iterations: len(allResults) / 5,
		Results:    allResults,
		Messages:   allMessages,
		Summary:    s.buildSummary(allResults),
	}
}

func (s *Supervisor) buildSummary(results []model.AgentResult) string {
	var sb strings.Builder
	sb.WriteString("=== 多Agent广告优化执行报告 (Go) ===\n")
	for _, r := range results {
		sb.WriteString(fmt.Sprintf("[%s] %s\n", r.AgentName, r.Summary))
	}
	return sb.String()
}
