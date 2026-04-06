# LangGraph 入门教程（零基础版）

本教程介绍 **LangGraph** 是什么、核心概念有哪些，并给出**可直接运行**的最小示例；最后说明**在本项目**中 LangGraph 如何编排多 Agent 广告优化流程。阅读前建议已读完《AI Agent 基础知识》并装好 Python 依赖（见环境搭建教程）。

---

## 1. LangGraph 是什么

**LangGraph** 是 LangChain 生态里用于构建 **有状态、多步、可循环** Agent 工作流的库。你可以把它理解成：

- 用 **图（Graph）** 表示业务流程：圆点是步骤，箭头是流转方向。
- 每一步可以是一个 Python 函数（或可调用的 Agent），读入**共享状态**，返回**状态更新**。
- 支持 **条件分支**（根据状态走不同路径）和 **循环**（例如优化未达标则再来一轮）。

与「单次调用 LLM」相比，LangGraph 更适合 **Supervisor 模式**、**审批流**、**重试与人工介入** 等工程场景。

官方文档（英文）：可在搜索引擎中查找 `LangGraph documentation` 获取最新版。

---

## 2. 核心概念

### 2.1 StateGraph（状态图）

**StateGraph** 是你创建的「工作流画布」类。你要向它：

- `add_node`：添加节点（每一步做什么）。
- `add_edge`：添加普通边（这一步做完必定去下一步）。
- `set_entry_point`：指定从哪个节点开始。
- `add_conditional_edges`：在某节点后根据函数返回值选路径。
- `compile()`：编译成可执行的 `CompiledGraph`，再 `invoke` 运行。

状态类型常见为 `dict` 或 `TypedDict` / Pydantic 模型（视版本与项目习惯而定）。

### 2.2 Node（节点）

**节点**本质上是一个**函数**，签名类似：

```python
def my_node(state: dict) -> dict:
    # 读取 state["foo"]
    # 做计算或调用 LLM
    return {"bar": 123}  # 返回的键值会合并进状态（策略可配置）
```

在广告项目里，每个 **Agent 的 `run` 方法** 往往就是一个节点。

### 2.3 Edge（边）

**普通边**：`graph.add_edge("a", "b")` 表示 `a` 执行完后**总是**进入 `b`。

### 2.4 State（状态）

**状态**是在整个图执行过程中传递的「共享黑板」。例如：

```python
{
    "task": "optimize_campaigns",
    "campaign_ids": ["c1", "c2"],
    "alerts": [...],
    "iteration": 0,
    "max_iterations": 3,
}
```

各节点读取上一节点的结果，并写入新字段或更新列表。列表如何合并（追加还是覆盖）需要在 reducer 或节点内自行约定；本项目在 Supervisor 里对列表合并有辅助函数。

### 2.5 Conditional Edge（条件边）

在某节点结束后，调用一个**路由函数**，根据其返回值（字符串）选择下一个节点名或 `END`。

```python
graph.add_conditional_edges(
    "optimize",
    route_fn,
    {"continue": "monitor", "end": END},
)
```

其中 `route_fn(state)` 返回 `"continue"` 或 `"end"`。这是实现 **循环优化** 的关键。

### 2.6 END

**END** 是 LangGraph 提供的**终止符**，表示图执行结束。

---

## 3. 安装和配置

在本项目里，依赖已写在 `python/requirements.txt`：

```text
langgraph>=0.2.0
langchain>=0.3.0
langchain-openai>=0.2.0
langchain-core>=0.3.0
```

安装：

```bash
pip install -r requirements.txt
```

若仅用下面**不调用真实 API** 的示例，理论上可不配置 `OPENAI_API_KEY`；若节点内使用 `ChatOpenAI`，则需有效 Key 与网络。下面示例**刻意不用 LLM**，保证离线可跑。

---

## 4. 最简单的两节点图（完整可运行代码）

将下面保存为 `demo_two_nodes.py`，在已安装 `langgraph` 的环境中执行：`python demo_two_nodes.py`。

```python
"""LangGraph 最小示例：两个节点串联，无 LLM，仅演示状态传递。"""

from langgraph.graph import END, StateGraph


def node_load(state: dict) -> dict:
    """模拟：加载任务描述。"""
    return {
        "message": state.get("message", "") + " [加载完成]",
        "step": state.get("step", 0) + 1,
    }


def node_summarize(state: dict) -> dict:
    """模拟：生成总结。"""
    return {
        "summary": f"步骤计数={state.get('step')}, 内容={state.get('message')}",
        "step": state.get("step", 0) + 1,
    }


def build_graph():
    graph = StateGraph(dict)
    graph.add_node("load", node_load)
    graph.add_node("summarize", node_summarize)

    graph.set_entry_point("load")
    graph.add_edge("load", "summarize")
    graph.add_edge("summarize", END)

    return graph.compile()


if __name__ == "__main__":
    app = build_graph()
    initial = {"message": "Hello", "step": 0}
    result = app.invoke(initial)
    print("最终状态:", result)
```

**运行结果应类似**：

```text
最终状态: {'message': 'Hello [加载完成]', 'step': 2, 'summary': '步骤计数=2, 内容=Hello [加载完成]'}
```

**你学到了什么**：

- `StateGraph(dict)` 用字典做状态。
- `set_entry_point` + `add_edge` 形成线性流水线。
- `invoke(initial_state)` 一次性跑完（也有流式 API，进阶再用）。

---

## 5. Supervisor Pattern 详解

**Supervisor（监督者）模式** 指：有一个**中心编排者**（或一张**中心图**）决定调用哪些「专家」Agent、顺序如何、是否重试。

在 LangGraph 里，Supervisor 常体现为：

1. 多个节点 = 多个专家步骤（监控、创意、竞价……）。
2. 普通边构成**主流程**。
3. 在**汇总节点**后接 **条件边**：若仍有问题且未超限 → 回到早期节点；否则 `END`。

**优点**：

- 流程对工程师**可读、可测**。
- 比「完全由 LLM 自由决定下一步」更**稳定**。

**缺点**：

- 图复杂后要注意**状态体积**和**无限循环**（务必设 `max_iterations` 等）。

---

## 6. 条件路由和循环示例（扩展）

在上一节两节点示例基础上，可增加「是否重试」的条件边。下面为**独立小例子**（保存为 `demo_loop.py`）：

```python
from langgraph.graph import END, StateGraph


def work(state: dict) -> dict:
    n = state.get("n", 0) + 1
    return {"n": n, "log": state.get("log", []) + [f"第{n}次工作"]}


def should_retry(state: dict) -> str:
    if state.get("n", 0) < 3:
        return "again"
    return "stop"


def build_loop_graph():
    g = StateGraph(dict)
    g.add_node("work", work)
    g.set_entry_point("work")
    g.add_conditional_edges(
        "work",
        should_retry,
        {"again": "work", "stop": END},
    )
    return g.compile()


if __name__ == "__main__":
    print(build_loop_graph().invoke({"n": 0, "log": []}))
```

这里 `work` 节点执行后，根据 `should_retry` 要么**再回到自己**，要么结束。真实项目里「再次进入」通常是回到**监控**或**第一个 Agent**，而不是空转。

---

## 7. 在本项目中 LangGraph 是怎么用的

下面内容与仓库 `python/src/orchestrator/supervisor.py` 一致，便于你对照源码阅读。

### 7.1 状态字典里有什么

包含 `task`、`campaign_ids`、`metrics`、`alerts`、`iteration`、`max_iterations`、`is_complete`、`agent_messages` 等字段，用于在 **Monitor → Audience → Creative → Bidding → Optimize** 之间传递上下文。

### 7.2 图的拓扑

- **入口**：`monitor`。
- **固定顺序边**：`monitor → audience → creative → bidding → optimize`。
- **条件边**：从 `optimize` 出发，由 `_should_continue(state)` 决定：
  - 若 `is_complete` 为真 → `end`（结束）。
  - 若迭代次数达到 `max_iterations` → `end`。
  - 若仍存在 `alerts` → `continue`（回到 `monitor`，形成闭环）。
  - 否则 → `end`。

### 7.3 可选依赖与回退

若未安装 LangGraph，`HAS_LANGGRAPH` 为 `False`，`AdOptimizerSupervisor` 会使用 `_run_sequential` **顺序执行**同一套 Agent，保证环境不全时仍能学习流程。

### 7.4 建议阅读源码的顺序

1. `AdOptimizerSupervisor._build_graph`
2. `_should_continue`
3. 任意一个 `agents/*_agent.py` 里的 `run(state)` 返回值如何更新 `state`

---

## 8. 调试小贴士

- 用 `print` 或 `structlog` 在节点入口打印 `state.keys()`，确认字段是否符合预期。
- 循环不停止时，检查 `alerts` 是否被清空、`iteration` 是否递增、`max_iterations` 是否合理。
- 版本升级后若 API 变更，以官方迁移文档为准。

---

## 9. 小结

- LangGraph 用 **StateGraph + 节点 + 边 + 条件边** 表达 **有状态、可循环** 的 Agent 流程。
- **Supervisor Pattern** 在本项目中体现为 **固定流水线 + optimize 后的条件回路**。
- 本文提供了**无 LLM** 的可运行最小示例，你可以在此基础上逐步接入 `ChatOpenAI` 与工具调用。

下一篇建议阅读：《ClickHouse 实战教程》（数据侧）或《部署指南》（运行整个项目）。
