# 架构设计文档

## 一、系统架构

### 1.1 整体架构

本系统采用 **Supervisor Pattern**（监督者模式），由一个中央 Orchestrator 协调 5 个专业 Agent 的执行。

### 1.2 数据流

```
广告平台(Google/Meta) → 事件采集 → Kafka → ClickHouse
                                               ↓
                              Monitor Agent → 指标计算/异常检测
                                               ↓
                              Audience Agent → 受众画像分析
                              Creative Agent → 素材生成（并行）
                                               ↓
                              Bidding Agent → 竞价策略优化
                                               ↓
                              Optimize Agent → 预算分配/素材管理
                                               ↓
                              广告平台API → 执行操作
```

### 1.3 Agent 通信机制

所有 Agent 通过 **共享 State** 通信，不直接互相调用。

State 中的字段和读写权限：

| 字段 | 写入者 | 读取者 |
|------|--------|--------|
| metrics | Mock/ClickHouse | 所有Agent |
| alerts | Monitor | Optimize |
| audience_insights | Audience | Creative, Bidding |
| new_creatives | Creative | Optimize |
| bidding_decisions | Bidding | Optimize |
| optimization_actions | Optimize | Supervisor |
| budget_allocations | Optimize | Supervisor |
| is_complete | Optimize | Supervisor（条件路由） |

## 二、技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| Agent编排 | LangGraph | 支持条件路由+循环+checkpoint |
| 数据仓库 | ClickHouse | 列式OLAP、物化视图秒级聚合 |
| 缓存 | Redis | 配置缓存+实时指标+去重 |
| 优化算法 | CVXPY | 数学可证明的最优预算分配 |
| 仪表板 | Streamlit | 快速构建Python数据应用 |

## 三、扩展性设计

### 3.1 新增 Agent

1. 实现 `run(state: dict) -> dict` 方法
2. 在 Supervisor 的 `_build_graph()` 中注册为新节点
3. 添加相应的边（依赖关系）

### 3.2 新增广告平台

1. 在 `AdsAPIClient` 中添加新平台的 API 调用
2. 在 `Platform` 枚举中添加新平台
3. Mock数据生成器中添加新平台的数据

### 3.3 切换到真实环境

1. 将 `RUN_MODE=mock` 改为 `RUN_MODE=live`
2. 填写真实的 API Key
3. 确保 ClickHouse 和 Redis 服务可用
