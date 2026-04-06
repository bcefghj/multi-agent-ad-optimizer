# Go 代码讲解 — goroutine + channel 版深度解析

> 面向 Go 开发者，讲解如何用 Go 的并发原语实现多 Agent 广告优化系统。

---

## 一、项目结构

```
golang/
├── go.mod                                # Go模块定义
├── cmd/server/main.go                    # HTTP服务入口
├── internal/
│   ├── model/types.go                    # 数据模型
│   ├── agent/
│   │   ├── agent.go                      # Agent接口定义
│   │   ├── creative.go                   # 创意生成
│   │   ├── audience.go                   # 受众分析
│   │   ├── bidding.go                    # 竞价策略
│   │   ├── monitor.go                    # 效果监控
│   │   └── optimize.go                   # 自动优化
│   ├── orchestrator/supervisor.go        # goroutine编排
│   └── service/mock_data.go             # 模拟数据
└── pkg/utils/                            # 通用工具
```

---

## 二、Agent 接口设计

```go
// agent/agent.go
type Agent interface {
    Name() string
    Execute(metrics []model.CampaignMetrics, ctx map[string]interface{}) model.AgentResult
}
```

**设计要点：**
- Go 通过 interface 定义行为，而非继承基类
- 任何实现了 `Name()` 和 `Execute()` 方法的 struct 都自动满足 `Agent` 接口
- 这就是 Go 的"鸭子类型"——不需要显式声明 `implements Agent`

### 数据模型

```go
type CampaignMetrics struct {
    CampaignID   string  `json:"campaign_id"`
    Impressions  int64   `json:"impressions"`
    // ...
}

// 方法而非属性——Go没有property语法
func (m *CampaignMetrics) CTR() float64 {
    if m.Impressions == 0 { return 0 }
    return float64(m.Clicks) / float64(m.Impressions)
}
```

**和Python/Java的对比：**
- Python: `@property` 装饰器
- Java: `getCtr()` getter方法
- Go: 指针接收者方法 `func (m *CampaignMetrics) CTR()`

---

## 三、各 Agent 实现

### Creative Agent

```go
type CreativeAgent struct{}

func NewCreativeAgent() *CreativeAgent { return &CreativeAgent{} }
func (a *CreativeAgent) Name() string  { return "Creative Agent" }

func (a *CreativeAgent) Execute(metrics []model.CampaignMetrics, ctx map[string]interface{}) model.AgentResult {
    var variants []map[string]interface{}

    for _, m := range metrics {
        // 根据CTR选择不同情感方向
        emotions := []string{"benefit", "trust"}
        if m.CTR() < 0.03 {
            emotions = []string{"urgency", "curiosity"}
        }

        for _, emo := range emotions {
            kws := emotionKeywords[emo]
            kw := kws[rand.Intn(len(kws))]
            variants = append(variants, map[string]interface{}{
                "headline": fmt.Sprintf("%s！%s专属福利", kw, product),
                // ...
            })
        }
    }

    return model.AgentResult{
        AgentName: a.Name(),
        Data:      map[string]interface{}{"variants": variants},
    }
}
```

### Bidding Agent — eCPM 计算

```go
func (a *BiddingAgent) Execute(metrics []model.CampaignMetrics, ctx map[string]interface{}) model.AgentResult {
    for _, m := range metrics {
        // eCPM = pCTR × pCVR × TargetCPA × 1000
        ecpm := predCTR * predCVR * targetCPA * 1000

        // 动态倍率
        mult := a.multiplier(m.ROAS())

        // 出价 = eCPM/1000 × 倍率，上限为CPA的80%
        bid := math.Max(0.01, math.Min(ecpm/1000*mult, targetCPA*0.8))
    }
}

// 出价倍率：switch-case 比 if-else 更清晰
func (a *BiddingAgent) multiplier(roas float64) float64 {
    ratio := roas / a.TargetROAS
    switch {
    case ratio > 2.0:  return 1.3
    case ratio > 1.2:  return 1.1
    case ratio > 0.8:  return 1.0
    case ratio > 0.5:  return 0.8
    default:           return 0.6
    }
}
```

---

## 四、Supervisor 编排 — goroutine 并发核心

```go
func (s *Supervisor) RunPipeline(metrics []model.CampaignMetrics, maxIter int) model.PipelineResult {
    for i := 0; i < maxIter; i++ {
        // Step 1: Monitor（串行）
        monitorResult := s.monitor.Execute(metrics, ctx)

        // Step 2: Audience + Creative 并行
        // 使用 sync.WaitGroup 等待两个goroutine完成
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

        wg.Wait()  // 阻塞直到两个goroutine都完成

        // Step 3-4: Bidding → Optimize（串行）
        biddingResult := s.bidding.Execute(metrics, ctx)
        optimizeResult := s.optimize.Execute(metrics, ctx)

        // 条件路由：无告警则结束
        alerts, _ := monitorResult.Data["alerts"].([]string)
        if len(alerts) == 0 { break }
    }
}
```

### 为什么用 WaitGroup 而不是 channel？

| 方式 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| `sync.WaitGroup` | 简单直接 | 无法传递结果 | 等待一组goroutine完成 |
| `channel` | 可传递数据 | 代码稍复杂 | 需要获取goroutine返回值 |
| `errgroup` | 支持错误处理 | 需要额外依赖 | 需要错误传播 |

当前代码用 WaitGroup + 闭包捕获结果变量。如果要用 channel 实现：

```go
ch := make(chan model.AgentResult, 2)
go func() { ch <- s.audience.Execute(metrics, ctx) }()
go func() { ch <- s.creative.Execute(metrics, ctx) }()
r1, r2 := <-ch, <-ch
```

---

## 五、HTTP Server

```go
func main() {
    supervisor := orchestrator.NewSupervisor()

    // 优化接口
    http.HandleFunc("/api/v1/optimize", func(w http.ResponseWriter, r *http.Request) {
        metrics := service.GenerateMetrics(count)
        result := supervisor.RunPipeline(metrics, maxIter)

        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(result)
    })

    log.Fatal(http.ListenAndServe(":8081", nil))
}
```

**设计选择：** 使用标准库 `net/http` 而非 gin/echo 框架。原因：
1. 接口数量少（3个），不需要框架的路由功能
2. 减少依赖，面试时容易解释
3. 标准库性能已经足够（单机轻松10K QPS）

---

## 六、三语言并发对比

```
Python:   asyncio.gather(agent1.arun(), agent2.arun())
Java:     CompletableFuture.allOf(f1, f2).join()
Go:       var wg sync.WaitGroup; wg.Add(2); go func(){}(); wg.Wait()
```

| 维度 | Python | Java | Go |
|------|--------|------|----|
| 并发单元 | 协程 | 线程 | goroutine |
| 内存开销 | ~KB/协程 | ~1MB/线程 | ~2KB/goroutine |
| CPU密集型 | 差(GIL) | 好 | 好 |
| 创建10万个 | 可以但意义不大 | 内存爆炸 | 轻松 |
| 调度方式 | 协作式 | 抢占式 | M:N混合 |

---

## 七、面试中 Go 版的加分话术

> "Go 版利用 goroutine 的轻量级特性实现 Agent 并行执行，每个 goroutine 只占用约 2KB
> 内存，相比 Java 线程的 1MB 开销有数量级的优势。用 sync.WaitGroup 协调 Audience 和
> Creative Agent 的并行执行，用 interface 定义统一的 Agent 抽象——任何新增的 Agent 只需
> 实现 Name() 和 Execute() 两个方法即可热插拔。这种设计完全符合 Go 的'组合优于继承'哲学。"
