# 八股文 — 多Agent系统 + 广告系统 + 分布式 核心知识点

> 面试前把这份文档背熟，覆盖90%以上的追问。

---

## 第一章：Agent 架构八股

### 1.1 什么是AI Agent？和传统程序有什么区别？

AI Agent = LLM + Memory + Tools + Planning

| 维度 | 传统程序 | AI Agent |
|------|---------|---------|
| 决策方式 | 预设规则/if-else | LLM推理+动态决策 |
| 适应性 | 固定逻辑 | 可根据反馈调整策略 |
| 工具使用 | 硬编码调用 | 动态选择工具 |
| 错误处理 | 预设异常路径 | 自我反思和重试 |

### 1.2 单Agent vs 多Agent，什么时候用多Agent？

**用多Agent的场景：**
1. **上下文污染**：多个独立子问题，每个子问题信息量大，单Agent的context window不够
2. **并行任务**：可拆分的独立方向，如受众分析和创意生成可以并行
3. **工具膨胀**：工具数量>20个时，单Agent的工具选择准确率下降

**不用多Agent的场景：**
- 简单查询（成本不匹配，多Agent成本是单Agent的10倍以上）
- 高度耦合的代码任务（需要完整上下文）
- 按组织架构拆Agent（增加不必要的通信开销）

### 1.3 Supervisor Pattern vs Swarm Pattern

| 维度 | Supervisor | Swarm |
|------|-----------|-------|
| 控制方式 | 中心化编排 | 去中心化对等通信 |
| 路由决策 | Supervisor决定下一个Agent | Agent之间互相handoff |
| 全局视角 | 有 | 无 |
| 复杂度 | 中等 | 较高 |
| 适用场景 | 有明确流程的pipeline | 灵活的探索性任务 |
| 单点故障 | Supervisor是单点 | 无单点 |

### 1.4 LangGraph 核心概念

- **StateGraph**：有限状态机，节点是Agent，边是转换条件
- **State**：全局共享状态字典，所有Agent读写同一个State
- **Node**：处理函数，接收State返回State更新
- **Edge**：节点间的转换，分为固定边和条件边
- **Conditional Edge**：根据State值动态决定下一个节点
- **Checkpoint**：状态快照，支持断点恢复和human-in-the-loop
- **Handoff**：Agent控制权转移，会传递完整会话历史

### 1.5 Agent记忆机制

| 类型 | 作用 | 实现 |
|------|------|------|
| 短期记忆 | 当前对话上下文 | LangGraph State |
| 长期记忆 | 历史经验/知识 | 向量数据库 (FAISS/Chroma) |
| 工作记忆 | 中间推理步骤 | Scratchpad / Chain-of-Thought |

---

## 第二章：广告系统八股

### 2.1 RTB（Real-Time Bidding）竞价流程

```
用户访问网页 → 广告位请求 → SSP（供给方平台）
    → Ad Exchange（广告交易所）发出竞价请求
    → DSP1/DSP2/DSP3（需求方平台）各自出价
    → Ad Exchange 选出最高价（二价竞价：付第二高价+0.01）
    → 胜出DSP的广告素材展示给用户
    → 整个过程 < 100ms
```

### 2.2 核心指标公式

| 指标 | 公式 | 含义 |
|------|------|------|
| CTR | clicks / impressions | 点击率 |
| CVR | conversions / clicks | 转化率 |
| CPA | cost / conversions | 单次获客成本 |
| CPC | cost / clicks | 单次点击成本 |
| CPM | cost / impressions × 1000 | 千次展示成本 |
| ROAS | revenue / cost | 广告支出回报率 |
| eCPM | pCTR × pCVR × bid × 1000 | 预估千次展示收入 |
| LTV | 用户全生命周期价值 | 长期ROI评估 |

### 2.3 eCPM排序公式

广告平台对竞争广告的排序依据：
```
eCPM = pCTR × pCVR × Bid × 1000
```
- pCTR：预估点击率（CTR预估模型输出）
- pCVR：预估转化率（CVR预估模型输出）
- Bid：广告主出价

eCPM最高的广告胜出，但实际扣费用的是第二名的eCPM+0.01（GSP二价竞价机制）。

### 2.4 归因模型

| 模型 | 逻辑 | 优缺点 |
|------|------|--------|
| 末次点击 | 转化归给最后一次点击 | 简单但忽略前序触点 |
| 首次点击 | 归给第一次触点 | 重视拉新但忽略后续 |
| 线性归因 | 平均分配给所有触点 | 公平但无差异 |
| 时间衰减 | 越近的触点权重越高 | 较合理 |
| 数据驱动 | 机器学习建模 | 最准确但需要大量数据 |

### 2.5 广告素材优化策略

1. **A/B测试**：控制组vs实验组，统计显著性检验(p<0.05)
2. **多臂老虎机(MAB)**：Thompson Sampling动态分配流量
3. **创意疲劳检测**：CTR连续3天下降>10%触发素材替换
4. **动态创意优化(DCO)**：根据用户特征实时组合标题+图片+CTA

---

## 第三章：ClickHouse 八股

### 3.1 为什么选ClickHouse？

| 维度 | MySQL | ClickHouse |
|------|-------|-----------|
| 存储模型 | 行式 | 列式 |
| 适用场景 | OLTP（事务） | OLAP（分析） |
| 写入模式 | 单行insert | 批量append |
| 查询特点 | 点查/小范围 | 全表扫描/聚合 |
| 压缩率 | 1:1~1:3 | 1:10~1:20 |
| 并发 | 高（万级QPS） | 低（百级并发） |

### 3.2 MergeTree引擎家族

| 引擎 | 特点 | 场景 |
|------|------|------|
| MergeTree | 基础引擎，主键排序 | 通用 |
| ReplacingMergeTree | 按主键去重 | 维度表(campaign/creative) |
| SummingMergeTree | 按主键自动聚合求和 | 预聚合指标 |
| AggregatingMergeTree | 支持任意聚合函数 | 复杂聚合 |
| CollapsingMergeTree | 通过正负标记实现更新/删除 | 需要更新的场景 |

### 3.3 物化视图原理

```sql
CREATE MATERIALIZED VIEW stats_mv
ENGINE = SummingMergeTree()
ORDER BY (campaign_id, date)
AS SELECT
    campaign_id,
    toDate(event_time) AS date,
    count() AS impressions,
    sumIf(cost, event_type='click') AS click_cost
FROM events
GROUP BY campaign_id, date;
```

原理：数据写入events表时，自动触发物化视图的增量计算并写入stats_mv表。
查询物化视图而非原始表，性能提升100-1000倍。

### 3.4 ClickHouse查询优化

1. **主键顺序**：ORDER BY的第一个字段应该是查询中最常用的过滤条件
2. **分区键**：PARTITION BY toYYYYMM(date)，方便按月裁剪
3. **跳数索引**：SET INDEX为低基数列加速过滤
4. **Projection**：预计算不同排序顺序的数据视图
5. **避免分布式表写入**：写本地表，通过分布式表读

---

## 第四章：分布式系统八股

### 4.1 消息队列在广告系统中的作用

- **解耦**：广告事件采集和分析处理解耦
- **削峰**：高峰期广告事件积压在Kafka，ClickHouse按节奏消费
- **异步**：竞价结果异步回传，不阻塞主流程

### 4.2 限流算法

| 算法 | 原理 | 优缺点 |
|------|------|--------|
| 固定窗口 | 时间窗口内计数 | 简单但有临界突刺 |
| 滑动窗口 | 滑动时间窗口计数 | 更平滑 |
| 令牌桶 | 固定速率放入令牌 | 允许突发流量 |
| 漏桶 | 固定速率流出 | 严格平滑 |

### 4.3 幂等性设计

广告扣费必须幂等！同一次点击不能重复扣费。
- **方案**：event_id + Redis SETNX去重
- **数据库层**：ReplacingMergeTree按event_id去重

### 4.4 缓存策略

```
广告配置（campaign/creative）→ Redis缓存，TTL 5分钟
实时指标 → Redis Sorted Set，按score排序
人群包 → Redis BitMap，O(1)判断用户是否在人群中
```

---

## 第五章：Python / Java / Go 语言八股

### 5.1 Python — 异步编程

```python
# LangGraph中Agent并行执行底层是asyncio
import asyncio

async def run_agents():
    results = await asyncio.gather(
        audience_agent.arun(state),
        creative_agent.arun(state),
    )
```

### 5.2 Java — CompletableFuture

```java
// Java版Supervisor中Audience+Creative并行
CompletableFuture<AgentResult> f1 = CompletableFuture.supplyAsync(
    () -> audienceAgent.execute(metrics, ctx), executor);
CompletableFuture<AgentResult> f2 = CompletableFuture.supplyAsync(
    () -> creativeAgent.execute(metrics, ctx), executor);
// 等待两者完成
CompletableFuture.allOf(f1, f2).join();
```

### 5.3 Go — goroutine + WaitGroup

```go
// Go版Supervisor中Audience+Creative并行
var wg sync.WaitGroup
wg.Add(2)
go func() { defer wg.Done(); audienceResult = audience.Execute(metrics, ctx) }()
go func() { defer wg.Done(); creativeResult = creative.Execute(metrics, ctx) }()
wg.Wait()
```

| 维度 | Python asyncio | Java CompletableFuture | Go goroutine |
|------|---------------|----------------------|-------------|
| 并发模型 | 协程(单线程) | 线程池 | 轻量级协程(M:N调度) |
| 调度器 | 事件循环 | ForkJoinPool | Go runtime |
| 内存开销 | 每协程~KB | 每线程~MB | 每goroutine~2KB |
| CPU密集型 | 不适合(GIL) | 适合 | 适合 |
| IO密集型 | 非常适合 | 适合 | 非常适合 |
