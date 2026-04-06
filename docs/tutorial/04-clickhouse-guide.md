# ClickHouse 实战教程（零基础版）

本教程介绍 **ClickHouse** 是什么、如何用 Docker 运行、常用 SQL、MergeTree 家族与物化视图，并详细说明**本仓库**中的表设计与查询思路，最后给出优化技巧及与 MySQL 的对比。建议已能使用 Docker Compose 启动本项目中的 ClickHouse（见环境搭建教程）。

---

## 1. ClickHouse 是什么

**ClickHouse** 是一款面向**在线分析（OLAP）**的列式数据库管理系统，由俄罗斯 Yandex 开源，现由社区与公司共同维护。它擅长：

- **海量事件数据**的快速聚合（曝光、点击、转化日志等）。
- **多维分析**（按 Campaign、创意、国家、设备分组统计）。
- **近实时**写入与查询（具体取决于集群规模与表设计）。

### 1.1 列式 vs 行式（用例子理解）

**行式数据库（如 MySQL InnoDB）**：一行是一条完整记录，适合「按主键读一整行」的事务型业务。

**列式数据库（ClickHouse）**：同一列的数据物理上靠在一起，适合「只读少数几列并对大量行做聚合」。

举例：表有 100 列，你只查 `sum(cost)` 和 `count()`：

- 行式库往往要扫整行或大量页。
- 列式库**只读 cost 列**，IO 更少，压缩比更高。

广告曝光/点击日志正是「列多、行数巨大、查询多为聚合」的典型场景。

---

## 2. 安装（Docker 方式）

本项目已在根目录提供 `docker-compose.yml`，其中定义了官方镜像：

```yaml
image: clickhouse/clickhouse-server:24.3
```

启动（在项目根目录）：

```bash
docker compose up -d
```

初始化 SQL 会挂载到容器的 `/docker-entrypoint-initdb.d`，首次启动会执行 `init-scripts/clickhouse/01_create_tables.sql`，自动建库建表。

### 2.1 验证服务

HTTP 接口（默认 8123）：

```bash
curl "http://localhost:8123/ping"
```

期望返回 `Ok.`。

在容器内用客户端：

```bash
docker exec -it ad-optimizer-clickhouse clickhouse-client --query "SELECT version()"
```

---

## 3. 基本 SQL 操作

下列示例默认数据库为 `ad_optimizer`（由初始化脚本创建）。

### 3.1 查看库与表

```sql
SHOW DATABASES;
USE ad_optimizer;
SHOW TABLES;
```

### 3.2 查询示例

```sql
SELECT campaign_id, count() AS cnt
FROM ad_events
GROUP BY campaign_id
ORDER BY cnt DESC
LIMIT 10;
```

### 3.3 插入示例（MergeTree 家族表）

ClickHouse 的 `INSERT` 常用批量形式：

```sql
INSERT INTO ad_events (
  event_id, campaign_id, creative_id, event_type,
  cost, revenue, platform, device, country, age_group, gender, event_time
) VALUES (
  'evt-001', 'cmp-1', 'cr-1', 'click',
  0.5, 0, 'google', 'mobile', 'CN', '25-34', 'male', now()
);
```

生产环境更推荐**批量插入**（多行 VALUES 或文件导入），以降低开销。

### 3.4 常见数据类型（本项目中出现的）

- `String`、`Float64`、`UInt64`、`UInt8`、`Date`、`DateTime`
- `Nullable(Date)`：可为空的日期
- `Enum8(...)`：枚举，节省存储
- `Array(String)`：字符串数组（如兴趣标签）

---

## 4. MergeTree 引擎家族介绍

ClickHouse 的核心存储引擎是 **MergeTree** 及其变种。本项目的 `01_create_tables.sql` 使用了多种引擎。

### 4.1 MergeTree()

**特点**：支持分区、排序键、主键稀疏索引；适合**追加型事实表**。

本项目中 **`ad_events`**、**`bid_logs`** 使用 `MergeTree()`，并按时间分区：

```sql
PARTITION BY toYYYYMM(event_time)
ORDER BY (campaign_id, creative_id, event_time);
```

含义简述：

- **分区**：按月份拆分数据目录，便于删除旧分区、提升查询剪枝效果。
- **排序键**：同类 `campaign_id` 的数据物理上更接近，按 Campaign 查时更快。

### 4.2 ReplacingMergeTree

**特点**：后台合并时，按排序键「保留一条」，通常配合**版本列**处理**更新语义**（最终一致）。

本项目中 **`campaigns`**、**`creatives`**、**`audience_profiles`** 使用 `ReplacingMergeTree(updated_at)` 或 `ReplacingMergeTree(created_at)`，适合「同一实体多次写入，保留最新快照」的场景。

**注意**：查询时若未处理重复行，可能仍看到旧版本，直到合并完成；严谨场景可用 `FINAL` 或自行聚合（有性能代价）。

### 4.3 SummingMergeTree

**特点**：合并时**对数值列自动求和**，适合**预聚合**。

本项目中两个**物化视图**的目标表使用 `SummingMergeTree()`，用于按天/按小时累加曝光、点击、消耗等。

---

## 5. 物化视图原理和使用

### 5.1 原理（直观版）

**普通视图**：保存的是查询定义，每次查询现算。

**物化视图（Materialized View）**：在**源表有数据写入时**，ClickHouse **自动**把计算结果写入另一张表（目标表）。查询时直接读目标表，速度更快。

可以理解为：**写入路径上的增量预计算**。

### 5.2 本项目中的物化视图

在 `init-scripts/clickhouse/01_create_tables.sql` 中：

1. **`campaign_creative_stats_mv`**  
   - 源：`ad_events`  
   - 聚合维度：`campaign_id`, `creative_id`, `stat_date`（按天）  
   - 指标：曝光、点击、转化、成本、收入等

2. **`hourly_stats_mv`**  
   - 源：`ad_events`  
   - 聚合维度：`campaign_id`, `stat_hour`（按小时）  
   - 用途：实时监控、趋势图

### 5.3 查询物化视图示例

```sql
SELECT
    campaign_id,
    sum(impressions) AS impressions,
    sum(clicks)      AS clicks
FROM ad_optimizer.campaign_creative_stats_mv
GROUP BY campaign_id;
```

因底层是 `SummingMergeTree`，合并前后结果在极端情况下可能有细微差别，生产上常再包一层 `sum()` 保证稳定。

---

## 6. 在本项目中的表设计说明

下表与 `01_create_tables.sql` 一致，便于对照。

| 表名 | 引擎 | 作用 |
|------|------|------|
| `campaigns` | ReplacingMergeTree | 广告活动主数据：预算、状态、平台等 |
| `creatives` | ReplacingMergeTree | 创意素材：标题、类型、A/B 组 |
| `ad_events` | MergeTree | 核心事实表：曝光/点击/转化事件 |
| `campaign_creative_stats_mv` | 物化视图 → SummingMergeTree | 按天聚合 Campaign×Creative |
| `hourly_stats_mv` | 物化视图 → SummingMergeTree | 按小时聚合 Campaign |
| `audience_profiles` | ReplacingMergeTree | 受众画像与预估规模 |
| `bid_logs` | MergeTree | 竞价日志：出价、是否竞得、eCPM 等 |
| `optimization_logs` | MergeTree | Agent/系统优化动作审计 |

**设计思路一句话**：  
「明细进 `ad_events`，常用报表走物化视图；配置类实体用 ReplacingMergeTree 表达最新状态。」

### 6.1 Python 如何查这些表

见 `python/src/data/clickhouse_client.py`：

- `get_campaign_metrics`：读 `campaign_creative_stats_mv`
- `get_creative_metrics`：同一视图按 `campaign_id` 过滤
- `get_hourly_trend`：读 `hourly_stats_mv`
- `get_audience_breakdown`：直接扫 `ad_events` 做细分（数据量大时要注意时间范围）

使用前提是 **`RUN_MODE=live`** 且已安装 `clickhouse-connect`。

---

## 7. 查询优化技巧（入门向）

1. **尽量带时间条件**：`ad_events` 按 `toYYYYMM(event_time)` 分区，用 `event_time` 范围可剪枝分区。  
2. **优先查物化视图**：日报、看板类查询用 `campaign_creative_stats_mv` / `hourly_stats_mv`。  
3. **避免 `SELECT *`**：列式存储下只选需要的列。  
4. **大结果集分页**：用 `LIMIT` + 排序键有序分页；深度分页可改用「上次最大值」游标。  
5. **预聚合与宽表**：复杂报表可再建物化视图或定时任务落表。  
6. **慎用 `FINAL`**：会强制合并语义，数据量大时成本高。  
7. **批量写入**：小批量高频插入会影响合并压力；尽量批量。

---

## 8. 与 MySQL 的对比

| 维度 | MySQL（典型 OLTP） | ClickHouse（OLAP） |
|------|-------------------|---------------------|
| 典型场景 | 订单、用户、权限、事务 | 日志、埋点、报表、监控 |
| 事务 ACID | 强 | 弱（不适合强事务） |
| 更新删除 | 行级更新常见 | 更偏向追加；更新需专门模式 |
| JOIN | 复杂 JOIN 常见 | 大 JOIN 需谨慎优化 |
| 聚合性能 | 数据量大时吃力 | 强项 |
| 生态工具 | 极成熟 | 在分析栈中成熟 |

**结论**：广告事件明细与报表适合 ClickHouse；用户账户、权限、订单等仍常放在 MySQL/PostgreSQL。实际架构中二者**共存**很常见。

---

## 9. 动手练习建议

1. 用 `clickhouse-client` 对 `ad_events` 插入若干行测试数据。  
2. 等待或触发合并后，查询两个物化视图是否有汇总行。  
3. 打开 `clickhouse_client.py`，把 SQL 复制到客户端执行，对比 Python 返回结果。

---

## 10. 小结

- ClickHouse 是**列式 OLAP**数据库，适合广告**事件明细 + 聚合分析**。  
- 本项目用 **MergeTree / ReplacingMergeTree / SummingMergeTree** 与**物化视图**完成分层存储。  
- Python 侧在 live 模式下通过 `clickhouse-connect` 查询物化视图与明细表。  
- 与 MySQL 互补而非替代。

下一篇：《部署指南》。
