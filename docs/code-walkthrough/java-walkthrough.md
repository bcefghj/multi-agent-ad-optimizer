# Java 代码讲解 — Spring Boot + LangChain4j 版深度解析

> 面向 Java 开发者，讲解如何用 Spring Boot 实现多 Agent 广告优化系统。

---

## 一、项目结构

```
java/
├── pom.xml                                    # Maven 依赖管理
├── src/main/java/com/adoptimizer/
│   ├── AdOptimizerApplication.java           # Spring Boot 启动类
│   ├── model/
│   │   ├── CampaignMetrics.java              # 核心指标模型
│   │   ├── AgentResult.java                  # Agent统一返回
│   │   ├── OptimizationAction.java           # 优化操作
│   │   └── BudgetAllocation.java             # 预算分配
│   ├── agent/
│   │   ├── BaseAgent.java                    # 抽象基类
│   │   ├── CreativeAgent.java                # 创意生成
│   │   ├── AudienceAgent.java                # 受众分析
│   │   ├── BiddingAgent.java                 # 竞价策略
│   │   ├── MonitorAgent.java                 # 效果监控
│   │   └── OptimizeAgent.java                # 自动优化
│   ├── orchestrator/
│   │   └── AgentSupervisor.java              # 编排层（核心）
│   ├── service/
│   │   └── MockDataService.java              # 模拟数据
│   └── config/
│       └── AdOptimizerController.java        # REST API
└── src/main/resources/application.yml        # 配置文件
```

---

## 二、核心模型 `CampaignMetrics.java`

```java
@Data @Builder @NoArgsConstructor @AllArgsConstructor
public class CampaignMetrics {
    private String campaignId;
    private long impressions;
    private long clicks;
    private long conversions;
    private double totalCost;
    private double totalRevenue;

    // 计算属性（和Python的@property等价）
    public double getCtr() {
        return impressions > 0 ? (double) clicks / impressions : 0.0;
    }
    public double getRoas() {
        return totalCost > 0 ? totalRevenue / totalCost : 0.0;
    }
}
```

**和Python的对比：**
- Python 用 `@property`，Java 用 getter 方法
- Python 用 Pydantic，Java 用 Lombok `@Data` 自动生成 getter/setter/toString
- Python 字段有默认值，Java 用 `@Builder` 模式

---

## 三、Agent 设计模式

### 抽象基类

```java
public abstract class BaseAgent {
    protected final String name;

    protected BaseAgent(String name) {
        this.name = name;
    }

    // 模板方法模式：子类实现具体逻辑
    public abstract AgentResult execute(
        List<CampaignMetrics> metrics,
        Map<String, Object> context
    );
}
```

**设计思路：**
- 所有 Agent 继承 BaseAgent，统一接口
- 参数是 `List<CampaignMetrics>` + `Map<String, Object> context`
- 返回统一的 `AgentResult`
- 使用 `@Component` 注解让 Spring 自动管理 Agent 实例

### Bidding Agent 实现

```java
@Component
public class BiddingAgent extends BaseAgent {
    private static final double TARGET_ROAS = 2.0;

    @Override
    public AgentResult execute(List<CampaignMetrics> metrics, Map<String, Object> context) {
        List<Map<String, Object>> decisions = new ArrayList<>();

        for (CampaignMetrics m : metrics) {
            // eCPM = pCTR × pCVR × TargetCPA × 1000
            double ecpm = predCtr * predCvr * targetCpa * 1000;

            // 动态出价倍率
            double multiplier = calculateMultiplier(m.getRoas());

            // 推荐出价 = eCPM / 1000 × 倍率，但不超过CPA的80%
            double bid = Math.max(0.01, Math.min(ecpm / 1000 * multiplier, targetCpa * 0.8));
        }
        return AgentResult.builder()
            .agentName(name)
            .data(Map.of("decisions", decisions))
            .build();
    }
}
```

---

## 四、Supervisor 编排层 — 核心亮点

```java
@Service
public class AgentSupervisor {
    // Spring 自动注入5个Agent
    private final MonitorAgent monitorAgent;
    private final AudienceAgent audienceAgent;
    private final CreativeAgent creativeAgent;
    private final BiddingAgent biddingAgent;
    private final OptimizeAgent optimizeAgent;

    private final ExecutorService executor = Executors.newFixedThreadPool(4);

    public Map<String, Object> runPipeline(List<CampaignMetrics> metrics, int maxIterations) {
        for (int i = 0; i < maxIterations; i++) {
            // Step 1: Monitor（串行）
            AgentResult monitorResult = monitorAgent.execute(metrics, context);

            // Step 2: Audience + Creative 并行！
            CompletableFuture<AgentResult> audienceFuture =
                CompletableFuture.supplyAsync(
                    () -> audienceAgent.execute(metrics, context), executor);
            CompletableFuture<AgentResult> creativeFuture =
                CompletableFuture.supplyAsync(
                    () -> creativeAgent.execute(metrics, context), executor);

            AgentResult audienceResult = audienceFuture.join();
            AgentResult creativeResult = creativeFuture.join();

            // Step 3-4: Bidding → Optimize（串行）
            AgentResult biddingResult = biddingAgent.execute(metrics, context);
            AgentResult optimizeResult = optimizeAgent.execute(metrics, context);

            // 检查是否继续迭代
            List<String> alerts = (List<String>) monitorResult.getData().get("alerts");
            if (alerts.isEmpty()) break;
        }
    }
}
```

**面试亮点：**
1. **CompletableFuture 并行**：Audience 和 Creative 没有依赖关系，用 `supplyAsync` 并行执行
2. **ExecutorService**：固定线程池控制并发度，避免创建过多线程
3. **Spring DI**：通过构造器注入，方便测试和替换

---

## 五、REST API

```java
@RestController
@RequestMapping("/api/v1")
public class AdOptimizerController {

    @PostMapping("/optimize")
    public Map<String, Object> runOptimization(
        @RequestParam(defaultValue = "5") int campaignCount,
        @RequestParam(defaultValue = "2") int maxIterations
    ) {
        List<CampaignMetrics> metrics = mockDataService.generateMetrics(campaignCount);
        return supervisor.runPipeline(metrics, maxIterations);
    }
}
```

**测试方法：**
```bash
# 启动服务
cd java && mvn spring-boot:run

# 调用优化接口
curl -X POST "http://localhost:8080/api/v1/optimize?campaignCount=5&maxIterations=2"

# 查看指标
curl http://localhost:8080/api/v1/metrics?count=5
```

---

## 六、Java vs Python 关键差异

| 维度 | Python 版 | Java 版 |
|------|----------|--------|
| Agent通信 | LangGraph State (dict) | Map<String, Object> context |
| 并行方式 | asyncio / LangGraph内置 | CompletableFuture + 线程池 |
| 数据模型 | Pydantic BaseModel | Lombok @Data + @Builder |
| DI容器 | 手动实例化 | Spring @Component自动管理 |
| 序列化 | model_dump() | Jackson自动序列化 |
| 配置管理 | python-dotenv | Spring application.yml |

---

## 七、面试中 Java 版的加分话术

> "Java 版使用 Spring Boot 的依赖注入管理 Agent 生命周期，通过 CompletableFuture
> 实现 Audience 和 Creative Agent 的并行执行。相比 Python 版用 LangGraph 的内置
> 编排，Java 版更接近企业级微服务的实际架构——可以方便地集成 Spring Security 做
> 鉴权、Spring Actuator 做健康检查、Micrometer 做指标监控。"
