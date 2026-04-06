# 部署与运行指南（零基础版）

本教程说明如何在**本地**运行本仓库的 **Docker Compose 基础设施**、**Python 版**（含 LangGraph Supervisor 与 Streamlit）、**Java 版（Maven + Spring Boot）**、**Go 版**，并简要介绍**生产环境 Kubernetes**思路与常见问题排查。路径以你本机克隆目录为准，下文用 `multi-agent-ad-optimizer` 表示项目根目录。

---

## 1. 本地开发环境（Docker Compose）

### 1.1 启动 ClickHouse 与 Redis

```bash
cd /path/to/multi-agent-ad-optimizer
cp .env.example .env
docker compose up -d
docker compose ps
```

确认 `ad-optimizer-clickhouse` 与 `ad-optimizer-redis` 健康。

### 1.2 端口与配置

默认端口见 `.env.example`：

- ClickHouse HTTP：`8123`，Native：`9000`
- Redis：`6379`

Java 的 `application.yml` 使用 `CLICKHOUSE_HTTP_PORT` 连接 JDBC（8123），与 Python `clickhouse-connect` 一致。

---

## 2. Python 版运行方式

### 2.1 环境准备

```bash
cd /path/to/multi-agent-ad-optimizer
python3 -m venv .venv
source .venv/bin/activate
pip install -r python/requirements.txt
```

（Windows 使用 `.venv\Scripts\activate`。）

### 2.2 环境变量

确保项目根目录有 `.env`，或手动 `export` 所需变量。入门阶段保持：

```bash
RUN_MODE=mock
```

可不连真实 ClickHouse/广告 API，便于先理解 Agent 流程。

### 2.3 运行 Supervisor（LangGraph 编排）

`AdOptimizerSupervisor` 的命令行入口在：

`python/src/orchestrator/supervisor.py`

由于包内使用相对导入（`from ..agents`），**不要**随意移动文件。推荐从 **`python` 目录** 以模块方式运行，并设置 `PYTHONPATH`：

```bash
cd /path/to/multi-agent-ad-optimizer/python
export PYTHONPATH=.
python -m src.orchestrator.supervisor
```

或在项目根目录：

```bash
cd /path/to/multi-agent-ad-optimizer
export PYTHONPATH=python
python -m src.orchestrator.supervisor
```

若已配置有效的 `OPENAI_API_KEY`，程序会尝试初始化 `ChatOpenAI`；否则仍可能以模拟/降级逻辑运行（以当前代码为准）。

### 2.4 连接真实 ClickHouse（可选）

1. `docker compose up -d` 已启动。  
2. `.env` 中设置：

```bash
RUN_MODE=live
CLICKHOUSE_HOST=localhost
CLICKHOUSE_HTTP_PORT=8123
CLICKHOUSE_DATABASE=ad_optimizer
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=
```

3. 再次运行 Supervisor 或仪表板；若库表未初始化，检查容器日志与 `init-scripts/clickhouse`。

---

## 3. Java 版运行方式（Maven）

### 3.1 前置条件

- **JDK 21**（`pom.xml` 中 `<java.version>21</java.version>`）
- **Maven 3.8+**

### 3.2 编译与启动

```bash
cd /path/to/multi-agent-ad-optimizer/java
mvn -q -DskipTests package
mvn spring-boot:run
```

默认 Web 端口在 `application.yml`：

```yaml
server:
  port: 8080
```

### 3.3 配置说明

`java/src/main/resources/application.yml` 引用环境变量：

- `CLICKHOUSE_HOST`、`CLICKHOUSE_HTTP_PORT`、`CLICKHOUSE_DATABASE` 等
- `REDIS_HOST`、`REDIS_PORT`
- `OPENAI_API_KEY`、`OPENAI_MODEL`
- `RUN_MODE`（mock / live）

在 IDE 中运行时，可将 `.env` 内容转为 Run Configuration 的环境变量，或在 shell 中 `export` 后启动 Maven。

### 3.4 验证

启动成功后访问（控制器基路径为 `/api/v1`，见 `AdOptimizerController`）：

```bash
curl -s http://localhost:8080/api/v1/health
```

触发一次优化流水线（POST，参数可省略，使用默认值）：

```bash
curl -s -X POST "http://localhost:8080/api/v1/optimize?campaignCount=5&maxIterations=2"
```

拉取模拟指标列表：

```bash
curl -s "http://localhost:8080/api/v1/metrics?count=3"
```

---

## 4. Go 版运行方式

### 4.1 前置条件

- **Go 1.22+**（见 `golang/go.mod` 中 `go 1.22`）

### 4.2 运行 HTTP 服务

```bash
cd /path/to/multi-agent-ad-optimizer/golang
go run ./cmd/server
```

日志中会显示监听端口 **`:8081`**（见 `cmd/server/main.go`）。

### 4.3 API 示例

```bash
curl -s "http://localhost:8081/api/v1/health"
```

优化流水线（示例）：

```bash
curl -s -X POST "http://localhost:8081/api/v1/optimize?campaigns=5&maxIterations=2"
```

指标列表：

```bash
curl -s "http://localhost:8081/api/v1/metrics?count=3"
```

Go 版侧重 HTTP API 演示；Redis 等依赖可在后续扩展中接入。

---

## 5. Streamlit 仪表板启动

仪表板源码：`python/src/dashboard/app.py`。文档内注释的启动方式为：

```bash
cd /path/to/multi-agent-ad-optimizer
streamlit run python/src/dashboard/app.py
```

若报模块找不到，可尝试设置 `PYTHONPATH`：

```bash
export PYTHONPATH=/path/to/multi-agent-ad-optimizer/python
streamlit run python/src/dashboard/app.py
```

浏览器默认打开 `http://localhost:8501`（可在 `.env` 中配置 `DASHBOARD_PORT`，具体是否被 Streamlit 读取取决于代码是否使用该变量；若未使用，仍以命令行参数为准）：

```bash
streamlit run python/src/dashboard/app.py --server.port 8501
```

仪表板包含模拟数据加载、图表与「运行优化 Agent」按钮，适合演示多 Agent 效果。

---

## 6. 生产环境部署方案（Kubernetes 简介）

生产环境通常不会只在单机上 `docker compose`，而是使用 **Kubernetes（K8s）** 编排容器。

### 6.1 为什么用 K8s

- **弹性伸缩**：流量高时自动扩容 Pod。
- **自愈**：容器崩溃自动重启。
- **滚动发布**：新版本逐步替换旧版本。
- **配置与密钥**：ConfigMap / Secret 管理环境变量。

### 6.2 与本项目相关的典型拆分

| 组件 | K8s 资源类型（常见） |
|------|----------------------|
| ClickHouse | StatefulSet + PVC（或使用云厂商托管 ClickHouse） |
| Redis | Deployment 或托管 Redis |
| Python API / Streamlit | Deployment + Service |
| Java / Go 服务 | Deployment + Service + Ingress |

### 6.3 最小概念清单

- **Pod**：一组容器的最小调度单元。  
- **Deployment**：声明期望副本数与镜像版本。  
- **Service**：为 Pod 提供稳定访问入口（ClusterIP / LoadBalancer）。  
- **Ingress**：HTTP/HTTPS 路由与 TLS。  
- **Helm**：打包模板化 K8s 清单，便于复用。

### 6.4 生产注意点（广告类系统）

- **密钥管理**：API Key、数据库密码用 Secret，勿写进镜像。  
- **网络策略**：限制 Redis/ClickHouse 仅内网可达。  
- **可观测性**：日志（ELK/Loki）、指标（Prometheus）、链路追踪。  
- **成本与 SLA**：ClickHouse 集群规格与副本策略需单独规划。

本仓库未附带完整 Helm Chart，以上为**方向性说明**，落地需按云环境与合规要求设计。

---

## 7. 常见部署问题排查

### 7.1 `ModuleNotFoundError: src` 或相对导入失败

- 确认 `PYTHONPATH` 包含 `python` 目录。  
- 优先使用 `python -m src.orchestrator.supervisor` 方式运行。

### 7.2 Streamlit 找不到 `src.data.mock_data`

- `app.py` 会通过 `Path` 调整 `sys.path`；若仍失败，从项目根目录启动并设置 `PYTHONPATH=python`。

### 7.3 Docker 端口冲突

- 修改 `.env` 中端口映射，并同步修改应用连接配置。

### 7.4 ClickHouse 连接拒绝

- `docker compose ps` 是否 healthy。  
- 防火墙是否放行 8123。  
- `CLICKHOUSE_HOST` 在容器内/容器外不同时：本机应用用 `localhost`，另一个容器内应用用服务名 `clickhouse`。

### 7.5 Java 启动报 JDBC 或 Redis 错

- `RUN_MODE=mock` 时部分逻辑可能不连外部依赖；若代码路径仍访问，检查 `application.yml` 与 profile。  
- Redis 未启动时，Spring Data Redis 可能阻塞启动，需起 Redis 或调整自动配置。

### 7.6 Go `go run` 下载依赖失败

- 配置 `GOPROXY`，例如：

```bash
export GOPROXY=https://goproxy.cn,direct
go run ./cmd/server
```

### 7.7 LLM 调用超时或 401

- 检查 `OPENAI_API_KEY` 是否有效、网络是否可达；必要时降低 `temperature` 或重试策略（代码层）。

---

## 8. 一键对照表

| 组件 | 目录/入口 | 典型命令 |
|------|-----------|----------|
| 基础设施 | 根目录 `docker-compose.yml` | `docker compose up -d` |
| Python Supervisor | `python/src/orchestrator/supervisor.py` | `PYTHONPATH=python python -m src.orchestrator.supervisor` |
| Streamlit | `python/src/dashboard/app.py` | `streamlit run python/src/dashboard/app.py` |
| Java | `java/` | `mvn spring-boot:run` → `http://localhost:8080` |
| Go | `golang/cmd/server` | `go run ./cmd/server` → `http://localhost:8081` |

---

## 9. 小结

- 本地开发：**Docker Compose** 提供 ClickHouse + Redis。  
- **Python** 是 Agent 与仪表板的主力入口；注意 **PYTHONPATH** 与 **RUN_MODE**。  
- **Java 21 + Maven**、**Go 1.22** 可分别启动 REST 服务用于对照学习。  
- 生产环境可考虑 **Kubernetes** 与托管中间件，并加强**安全与可观测性**。

建议结合《环境搭建教程》与《ClickHouse 实战教程》反复演练，直到各端口与健康检查均通过。
