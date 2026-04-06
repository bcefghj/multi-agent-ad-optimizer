# 面试问答集 — 50+ 高频面试题及参考答案

> 每个问题配有【考察点】和【参考答案】，答案力求简洁+有深度。

---

## 一、项目设计类（15题）

### Q1: 为什么要用多Agent而不是单个大模型？
**考察点：** 架构决策能力

**答：** 三个原因：
1. **上下文隔离**：5个职能域各自的prompt和工具集不同，硬塞一个Agent会导致上下文污染，工具选择准确率下降
2. **并行执行**：Audience和Creative没有依赖关系，多Agent可以并行，单Agent只能串行
3. **独立迭代**：每个Agent可以独立升级优化，不影响其他Agent

### Q2: 5个Agent的执行顺序是固定的吗？
**答：** 不完全固定。核心流程是 Monitor→Audience+Creative(并行)→Bidding→Optimize，但有两个动态路由：
1. Optimize完成后，如果有未解决的告警，会回到Monitor开始新一轮
2. 如果Monitor没有检测到异常，可以跳过Optimize直接结束

### Q3: Agent之间怎么通信？
**答：** 通过LangGraph的共享State字典。不是Agent之间直接发消息，而是每个Agent读取State、处理后写回State。好处是解耦——Agent不需要知道其他Agent的存在。

### Q4: 如果某个Agent执行失败怎么办？
**答：** 三层防护：
1. **try-catch + mock回退**：LLM调用失败时回退到规则引擎
2. **LangGraph Checkpoint**：支持从失败点恢复，不用重跑整个pipeline
3. **超时机制**：每个Agent设置最大执行时间，超时后返回默认结果

### Q5: 为什么选择LangGraph而不是CrewAI或AutoGen？
**答：** 
- CrewAI：适合快速原型，但对复杂的条件路由和循环支持不好
- AutoGen：偏向Agent对话/辩论，不适合我们的pipeline场景
- LangGraph：提供底层的StateGraph控制，支持条件分支、循环、并行、checkpoint，最灵活

### Q6: 怎么评估整个系统的效果？
**答：** A/B测试对比：
- 实验组：Agent自动优化
- 对照组：人工优化
- 对比核心指标：CTR、CVR、CPA、ROAS
- 至少跑2周消除波动

### Q7: 生产环境怎么部署？
**答：** Docker Compose开发环境 → K8s生产环境。每个Agent可以独立扩缩容。ClickHouse用分布式集群。Redis用Sentinel保证高可用。

---

## 二、技术实现类（15题）

### Q8: eCPM预估怎么做的？
**答：** `eCPM = pCTR × pCVR × Bid × 1000`。当前版本pCTR和pCVR用历史均值+高斯噪声模拟预估。生产环境应该训练CTR预估模型（如DeepFM/DIN）和CVR预估模型（如ESMM）。

### Q9: CVXPY预算优化的目标函数和约束是什么？
**答：**
- 目标：`maximize(roas_vector @ budget_vector)`
- 约束1：`sum(budget) == total_budget`（总预算守恒）
- 约束2：`budget_i >= current_i * 0.5`（单campaign最多减半）
- 约束3：`budget_i <= current_i * 1.5`（单campaign最多加50%）
- 约束4：`budget >= 0`（非负）

### Q10: ClickHouse物化视图怎么工作的？
**答：** 数据写入base表时，MergeTree引擎自动触发物化视图的增量计算，把聚合结果写入目标表（SummingMergeTree）。注意：物化视图只处理新写入的数据，不会回溯历史数据。

### Q11: 如何检测广告创意疲劳？
**答：** 规则引擎：CTR连续3天环比下降>10%，或者CTR低于该campaign历史均值的60%。触发后自动暂停该creative并通知Creative Agent生成替代素材。

### Q12: Redis在系统中的作用？
**答：** 四个用途：
1. **配置缓存**：campaign/creative信息，避免频繁查ClickHouse
2. **实时指标**：用Sorted Set存储最近1小时的实时指标
3. **去重**：用SETNX对event_id去重，防止重复计费
4. **Agent通信缓冲**：临时存储Agent间的中间结果

### Q13: 怎么保证广告扣费不重复？
**答：** 幂等设计：
1. 每个事件有唯一event_id
2. 写入前先Redis SETNX检查（O(1)，TTL 24小时）
3. ClickHouse用ReplacingMergeTree按event_id最终去重

### Q14: 高并发写入ClickHouse的策略？
**答：** 不能逐条insert，要batch写入。流程：
事件→Kafka→消费者batch聚合（1000条或10秒）→批量insert到ClickHouse
每次insert几千到几万行，吞吐可达百万行/秒。

### Q15: 怎么处理LLM的不确定性输出？
**答：** 
1. 结构化输出：Pydantic模型约束JSON格式
2. 重试机制：解析失败最多重试3次
3. 回退机制：LLM失败时用规则模板生成
4. 人工审核：高置信度自动执行，低置信度发起人工审批

---

## 三、架构设计类（10题）

### Q16: 这个系统的QPS能到多少？
**答：** 取决于瓶颈：
- LLM调用：受API限制，约50-100 QPS
- ClickHouse查询：百级并发
- 如果用mock模式跑优化，Go版单机可达1000+ QPS
- 生产环境通常按campaign数量而非QPS衡量：支持同时优化500+个campaign

### Q17: 如何水平扩展？
**答：** 
- Agent层：无状态，可任意水平扩展
- ClickHouse：Distributed表引擎+ReplicatedMergeTree
- Redis：Cluster模式分片
- Kafka：增加partition数量

### Q18: 有没有考虑过微服务拆分？
**答：** 当前是单体（适合初期），可以按以下维度拆：
- 数据采集服务（事件写入）
- 分析查询服务（ClickHouse读取）
- Agent编排服务（LangGraph）
- 广告平台适配服务（Google/Meta API）

### Q19: 怎么做灰度发布？
**答：** 按campaign维度灰度：
1. 选10%的campaign走新版Agent
2. 对比指标无回归后扩大到50%
3. 全量上线

### Q20: 系统的监控和可观测性？
**答：** 三层监控：
1. **基础设施**：Prometheus + Grafana（CPU/内存/QPS）
2. **业务指标**：ClickHouse物化视图+Streamlit仪表板（CTR/CPA/ROAS）
3. **Agent层**：每个Agent的执行耗时、成功率、token消耗（structlog结构化日志）

---

## 四、广告业务类（10题）

### Q21: 什么是ROAS？多少算好？
**答：** ROAS = Revenue / Ad Spend。行业标准通常>2算及格（花1块赚2块），>4算优秀。但因行业而异，品牌广告可能ROAS<1但有长期品牌价值。

### Q22: CPA和CPC的区别？
**答：** CPC是每次点击成本，CPA是每次转化（购买/注册）成本。CPA = CPC / CVR。优化师通常更关注CPA因为直接关联获客成本。

### Q23: 什么是Lookalike人群扩展？
**答：** 基于种子人群（如已购买用户）的特征，在全量用户中找相似用户。技术实现：把种子人群转为特征向量，用ANN（近似最近邻）在全量用户中检索。Meta的1%扩展≈覆盖200万人。

### Q24: 二价竞价（GSP）vs 一价竞价
**答：** 
- 一价：出多少付多少 → 鼓励压价，价格发现不充分
- 二价（GSP）：付第二高价+0.01 → 鼓励真实出价（接近VCG机制），是Google Ads的标准
- 趋势：Google在2019年转向一价竞价（first-price），但保留了Bid Shading（出价遮蔽）机制

### Q25: 怎么防止广告欺诈（fraud）？
**答：** 多维度检测：
1. IP频率异常（同一IP短时间大量点击）
2. 设备指纹异常（模拟器/改机工具）
3. 行为模式异常（点击后无后续行为）
4. 地域异常（IP地域与用户画像不匹配）

---

## 五、编码和算法类（5题）

### Q26: 手写一个简单的eCPM排序
```python
def rank_ads(ads):
    for ad in ads:
        ad['ecpm'] = ad['pred_ctr'] * ad['pred_cvr'] * ad['bid'] * 1000
    return sorted(ads, key=lambda x: x['ecpm'], reverse=True)
```

### Q27: 手写异常检测函数
```python
def detect_anomaly(metrics, ctr_min=0.005, cpa_max=200):
    alerts = []
    for m in metrics:
        if m['impressions'] > 100 and m['clicks']/m['impressions'] < ctr_min:
            alerts.append(f"Low CTR: {m['campaign_id']}")
    return alerts
```

### Q28: 手写预算优化（不用CVXPY）
```python
def allocate_budget(metrics, total_budget):
    roas_scores = [max(m.roas, 0.01) for m in metrics]
    total_score = sum(roas_scores)
    return [total_budget * s / total_score for s in roas_scores]
```

### Q29: 设计一个A/B测试框架的核心接口
```python
class ABTest:
    def assign_group(self, user_id: str) -> str:
        """一致性哈希，同一用户始终分到同一组"""
        return "control" if hash(user_id) % 100 < 50 else "treatment"

    def is_significant(self, control_cvr, treatment_cvr, sample_size):
        """Z检验判断统计显著性"""
        pass
```

### Q30: Go并发模型中如何避免data race？
```go
// 方案1: sync.Mutex
var mu sync.Mutex
mu.Lock()
shared_state["key"] = value
mu.Unlock()

// 方案2: channel (推荐)
ch := make(chan AgentResult, 2)
go func() { ch <- agent1.Execute() }()
go func() { ch <- agent2.Execute() }()
r1, r2 := <-ch, <-ch
```
