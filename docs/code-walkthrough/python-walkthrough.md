# Python 代码讲解 — 逐模块深度解析

> 本文档面向小白，逐个模块讲解 Python 版代码的设计思路和关键实现。

---

## 一、项目结构总览

```
python/
├── requirements.txt          # 依赖清单
├── src/
│   ├── models/schemas.py     # 数据模型（所有Agent共享）
│   ├── data/
│   │   ├── clickhouse_client.py  # ClickHouse数据库操作
│   │   └── mock_data.py          # 模拟数据生成器
│   ├── tools/
│   │   ├── ads_api.py            # 广告平台API封装
│   │   └── analytics.py          # 分析工具（eCPM/异常检测/预算优化）
│   ├── agents/                   # 5个Agent
│   │   ├── creative_agent.py     # 创意生成
│   │   ├── audience_agent.py     # 受众分析
│   │   ├── bidding_agent.py      # 竞价策略
│   │   ├── monitor_agent.py      # 效果监控
│   │   └── optimize_agent.py     # 自动优化
│   ├── orchestrator/
│   │   └── supervisor.py         # LangGraph 编排层（核心）
│   └── dashboard/
│       └── app.py                # Streamlit 仪表板
└── tests/
```

---

## 二、数据模型 `models/schemas.py`

这是整个系统的"数据契约"，所有 Agent 读写的数据都定义在这里。

### 核心类解读

```python
class CampaignMetrics(BaseModel):
    """单个campaign的汇总指标 — 这是Agent之间传递的核心数据"""
    campaign_id: str
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    total_cost: float = 0.0
    total_revenue: float = 0.0

    @property
    def ctr(self) -> float:
        """CTR = 点击数 / 曝光数，用 @property 让调用方像访问属性一样使用"""
        return self.clicks / self.impressions if self.impressions > 0 else 0.0
```

**设计要点：**
- 使用 Pydantic BaseModel，自带数据验证和序列化
- `@property` 装饰器：CTR/CVR/CPA/ROAS 都是计算属性，不存储，避免数据不一致
- 所有字段都有默认值，Agent 可以只传部分字段

### 全局状态 `AdOptimizerState`

```python
class AdOptimizerState(BaseModel):
    """LangGraph Supervisor 管理的全局共享状态"""
    metrics: list[CampaignMetrics] = []       # Monitor → 所有Agent读
    new_creatives: list[CreativeVariant] = []  # Creative → Optimize读
    bidding_decisions: list[BiddingDecision] = []  # Bidding → Optimize读
    alerts: list[str] = []                     # Monitor → Optimize读
    iteration: int = 0                         # 控制循环次数
    is_complete: bool = False                  # 控制是否结束
```

**面试亮点：** State 的设计避免了 Agent 之间直接通信，实现了解耦。每个 Agent 只关心自己需要读写的字段。

---

## 三、Agent 实现详解

### 3.1 Creative Agent

```python
def run(self, state: dict) -> dict:
    """LangGraph 节点入口 — 必须接收 dict 返回 dict"""
    metrics = state.get("metrics", [])  # 从共享State读取指标
    new_creatives = []

    for m_data in metrics:
        m = CampaignMetrics(**m_data)   # dict → Pydantic对象
        variants = self._generate_variants(m)  # 生成文案变体
        new_creatives.extend([v.model_dump() for v in variants])

    return {
        "new_creatives": new_creatives,  # 写回State
        "current_agent": "creative",
    }
```

**关键设计：**
1. `run(state: dict) -> dict`：LangGraph 要求节点函数的签名是 dict→dict
2. `self._generate_variants(m)` 根据 `self.llm` 是否存在决定走 LLM 还是 mock
3. mock 模式根据 CTR 高低选择不同情感方向的文案（紧迫/好奇/信任/利益）

### 3.2 Bidding Agent 核心算法

```python
def _compute_bid(self, metrics, audience):
    pred_ctr = self._predict_ctr(metrics)  # 预估CTR
    pred_cvr = self._predict_cvr(metrics)  # 预估CVR
    target_cpa = metrics.cpa if metrics.cpa < float("inf") else 100.0

    # eCPM公式：这是广告系统的核心排序依据
    ecpm = calculate_ecpm(pred_ctr, pred_cvr, target_cpa)

    # 动态出价倍率：ROAS好→提价争量，差→降价控本
    multiplier = self._calculate_multiplier(metrics)
    recommended_bid = ecpm / 1000 * multiplier

    # 出价上限：不超过目标CPA的80%
    recommended_bid = max(0.01, min(recommended_bid, target_cpa * 0.8))
```

**面试怎么说：** eCPM = pCTR × pCVR × TargetCPA × 1000。出价倍率根据当前ROAS和目标ROAS的比值动态调整。ROAS超过目标1.5倍就提价20%争取更多流量，低于0.5倍就降价40%控制成本。

### 3.3 Optimize Agent — 闭环核心

```python
def run(self, state):
    # 1. 评估素材表现 → 暂停低效素材
    pause_actions = self._evaluate_creatives(metrics)

    # 2. CVXPY凸优化 → 预算再分配
    budget_allocs = optimize_budget_allocation(metrics)

    # 3. 处理Monitor告警 → 应急响应
    alert_actions = self._handle_alerts(alerts, metrics)

    # 4. 管理A/B测试 → 如果有新素材就启动测试
    ab_actions = self._manage_ab_tests(new_creatives, metrics)

    # 5. 判断是否继续迭代
    is_complete = iteration >= max_iterations or not alerts
```

**面试亮点：** Optimize Agent 是整个闭环的"大脑"。它不只是执行优化，还做"决策"——通过 `is_complete` 字段控制整个 pipeline 是继续还是结束。

---

## 四、Supervisor 编排层

```python
class AdOptimizerSupervisor:
    def _build_graph(self):
        graph = StateGraph(dict)

        # 注册5个Agent为图的节点
        graph.add_node("monitor", self.monitor.run)
        graph.add_node("audience", self.audience.run)
        graph.add_node("creative", self.creative.run)
        graph.add_node("bidding", self.bidding.run)
        graph.add_node("optimize", self.optimize.run)

        # 固定边：Monitor → Audience → Creative → Bidding → Optimize
        graph.set_entry_point("monitor")
        graph.add_edge("monitor", "audience")
        graph.add_edge("audience", "creative")
        graph.add_edge("creative", "bidding")
        graph.add_edge("bidding", "optimize")

        # 条件边：Optimize完成后，有告警就继续，没有就结束
        graph.add_conditional_edges(
            "optimize",
            self._should_continue,
            {"continue": "monitor", "end": END},
        )

        return graph.compile()

    @staticmethod
    def _should_continue(state):
        """条件路由函数 — 这就是"闭环"的关键"""
        if state.get("is_complete"):
            return "end"
        if state.get("alerts"):
            return "continue"  # 还有告警，再来一轮
        return "end"
```

**面试怎么说：** 不是简单的 A→B→C→D→E 顺序执行。Optimize 完成后有条件分支——如果 Monitor 发现了异常告警且还没到最大迭代次数，整个 pipeline 会回到 Monitor 开始新一轮优化。这就形成了"监控→分析→优化→再监控"的闭环。

---

## 五、分析工具 `tools/analytics.py`

### CVXPY 预算优化

```python
def optimize_budget_allocation(metrics_list, total_budget=None, max_change_pct=0.5):
    n = len(active_metrics)
    current_budgets = np.array([m.total_cost for m in active])  # 当前预算
    roas_scores = np.array([m.roas for m in active])            # 各campaign的ROAS

    x = cp.Variable(n, nonneg=True)                    # 决策变量：新预算
    objective = cp.Maximize(roas_scores @ x)            # 目标：最大化加权ROAS
    constraints = [
        cp.sum(x) == total_budget,                      # 总预算不变
        x >= current_budgets * (1 - max_change_pct),    # 最多减50%
        x <= current_budgets * (1 + max_change_pct),    # 最多加50%
    ]
    prob = cp.Problem(objective, constraints)
    prob.solve(solver=cp.SCS)
```

**面试亮点：** 这不是拍脑袋分预算，而是数学上可证明的最优解。约束条件确保不会出现某个 campaign 预算归零的极端情况。

---

## 六、仪表板 `dashboard/app.py`

关键技术点：
- `@st.cache_data`：缓存数据生成，避免每次刷新重新计算
- `plotly.express`：交互式图表（散点图、柱状图、饼图）
- `st.columns`：多列布局实现仪表板效果
- `st.session_state`：存储 Agent 优化结果，点击按钮后展示

---

## 七、面试被问到某段代码时的回答策略

1. **先说设计目的**：这段代码解决什么问题
2. **再说技术选择**：为什么这么实现（有什么替代方案）
3. **最后说数据效果**：这样做带来了什么效果
