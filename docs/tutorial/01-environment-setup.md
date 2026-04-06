# 环境搭建教程（零基础版）

本教程面向**完全没有编程经验**的读者，一步步带你把「多 Agent 智能广告投放与优化」项目所需的环境装好。建议按顺序阅读，遇到不懂的名词可以搜索或先跳过，完成后再回头看。

---

## 1. 你需要准备什么

- 一台能上网的电脑（Windows / macOS / Linux 均可）。
- 大约 **5～10GB** 可用磁盘空间（含 Docker 镜像、Python 包等）。
- **管理员权限**（安装软件、Docker 时可能需要）。
- 耐心：第一次装环境常见问题较多，属于正常现象。

---

## 2. Python 3.11 及以上安装

Python 是本项目 **Python 版 Agent 与 Streamlit 仪表板** 的运行环境。版本要求是 **3.11 或更高**（例如 3.11.x、3.12.x）。

### 2.1 如何确认是否已安装

打开「终端」或「命令提示符」，输入：

```bash
python3 --version
```

或（Windows 上有时是）：

```bash
python --version
```

若显示 `Python 3.11.x` 或更高，可跳过安装，直接进入下一节。

### 2.2 Windows 安装步骤

1. 打开浏览器，访问 [https://www.python.org/downloads/](https://www.python.org/downloads/)，下载 **Python 3.11+** 的 Windows 安装包。
2. 运行安装程序时，**务必勾选**「Add python.exe to PATH」（添加到环境变量），否则命令行里可能找不到 `python`。
3. 安装完成后，**关闭并重新打开**「命令提示符」或 PowerShell，再执行 `python --version` 验证。

### 2.3 macOS 安装步骤

**方式 A：官网安装包**  
与 Windows 类似，从 python.org 下载 macOS 安装包并安装。

**方式 B：Homebrew（适合习惯用命令行的用户）**

```bash
brew install python@3.11
```

安装后按 `brew` 提示把 `python3` 加入 PATH。

### 2.4 Linux（以 Ubuntu/Debian 为例）

```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
python3.11 --version
```

不同发行版包名可能略有差异，核心是安装 **3.11+** 并确保 `pip` 可用。

### 2.5 虚拟环境（强烈推荐）

虚拟环境可以把本项目的依赖和系统其它 Python 项目隔离开，避免版本冲突。

在项目根目录 `multi-agent-ad-optimizer` 下执行：

```bash
cd /path/to/multi-agent-ad-optimizer
python3 -m venv .venv
```

- **Windows** 激活：`.venv\Scripts\activate`
- **macOS/Linux** 激活：`source .venv/bin/activate`

激活后，命令行前面通常会出现 `(.venv)` 字样。

---

## 3. pip 与 `requirements.txt` 说明

`pip` 是 Python 的包管理器，用来安装第三方库。本项目的 Python 依赖列在 **`python/requirements.txt`** 里。

### 3.1 升级 pip（可选但推荐）

```bash
python -m pip install --upgrade pip
```

### 3.2 安装项目依赖

确保已激活虚拟环境，然后：

```bash
cd python
pip install -r requirements.txt
```

若你从项目根目录执行，路径应为：

```bash
pip install -r python/requirements.txt
```

### 3.3 `requirements.txt` 里主要是什么

简要说明（不必一次全懂）：

| 包名 | 作用简述 |
|------|----------|
| `langgraph` / `langchain` | Agent 编排与 LLM 调用 |
| `clickhouse-connect` | 连接 ClickHouse 数据库 |
| `redis` | 连接 Redis |
| `streamlit` | Web 仪表板 |
| `pydantic` | 数据校验与模型定义 |
| `python-dotenv` | 读取 `.env` 环境变量 |

安装若报错，常见原因是 **网络** 或 **Python 版本过低**。请确认 Python ≥ 3.11，并尝试使用国内镜像（示例）：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 4. Docker Desktop 安装

Docker 用来在本机一键启动 **ClickHouse** 和 **Redis**，与项目根目录的 **`docker-compose.yml`** 配合使用。

### 4.1 为什么用 Docker

- 不用在系统里手动安装 ClickHouse/Redis 二进制。
- 版本与项目一致，减少「我电脑上能跑、你电脑上不行」的问题。

### 4.2 Windows / macOS

1. 访问 [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
2. 下载 **Docker Desktop** 并安装。
3. 安装后启动 Docker Desktop，等待状态变为 **Running**（运行中）。
4. 在终端执行：

```bash
docker --version
docker compose version
```

能显示版本号即基本成功。

### 4.3 Linux

可参考 Docker 官方文档安装 **Docker Engine** 与 **Compose 插件**，各发行版步骤不同，以官方为准。

---

## 5. 使用 docker-compose 启动 ClickHouse 与 Redis

1. 打开终端，进入项目根目录（与 `docker-compose.yml` 同级）：

```bash
cd /path/to/multi-agent-ad-optimizer
```

2. 启动服务（后台运行可加 `-d`）：

```bash
docker compose up -d
```

3. 查看容器状态：

```bash
docker compose ps
```

你应该能看到类似 `ad-optimizer-clickhouse` 和 `ad-optimizer-redis` 的容器，且状态为 **healthy** 或 **running**。

### 5.1 端口说明（默认值）

| 服务 | 用途 | 默认端口 |
|------|------|----------|
| ClickHouse HTTP | HTTP 接口、JDBC 常用 | 8123 |
| ClickHouse Native | 原生协议 | 9000 |
| Redis | 缓存/消息等 | 6379 |

端口可通过 `.env` 中的变量覆盖（见下一节）。

### 5.2 停止服务

```bash
docker compose down
```

数据默认保存在 Docker 卷中；`down` 不删卷则数据一般仍在。若需彻底清空，需额外删除卷（慎用）。

---

## 6. `.env` 配置说明

项目提供了 **`.env.example`**，你需要复制一份为 **`.env`** 并按需修改。

在项目根目录执行：

```bash
cp .env.example .env
```

### 6.1 新手最少要关心什么

- **`OPENAI_API_KEY`**：若要用真实 LLM，填入你的 API Key；占位符 `sk-your-...` 不会被当作有效 Key。
- **`RUN_MODE`**：新手建议保持 **`mock`**，不连真实广告平台 API，也能跑通流程。
- **ClickHouse / Redis 主机与端口**：本机 Docker 默认 **`localhost`** 与 **`8123` / `6379`**，一般不用改。

### 6.2 与 docker-compose 的关系

`docker-compose.yml` 会读取 `.env` 中的变量（如 `CLICKHOUSE_PORT`、`REDIS_PORT`）来映射端口。Python/Java 程序读取的也是 `.env`（或系统环境变量）里的 `CLICKHOUSE_HOST` 等，**两边要一致**。

---

## 7. 验证安装是否成功

按下面顺序检查，全部通过即可认为环境基本 OK。

### 7.1 Python 与依赖

```bash
python --version
pip show langgraph streamlit clickhouse-connect
```

### 7.2 Docker 与服务

```bash
docker compose ps
```

### 7.3 ClickHouse 是否响应（HTTP）

```bash
curl "http://localhost:8123/ping"
```

若返回 `Ok.`（或类似成功响应），说明 ClickHouse HTTP 端口正常。

### 7.4 Redis 是否响应

```bash
redis-cli -h 127.0.0.1 -p 6379 ping
```

若未安装 `redis-cli`，可用：

```bash
docker exec ad-optimizer-redis redis-cli ping
```

应返回 `PONG`。

### 7.5（可选）用 Python 测 ClickHouse

将 `RUN_MODE` 设为 `live` 且驱动已安装时，`python/src/data/clickhouse_client.py` 会尝试连接；新手可先保持 `mock`，用上面 `curl` 即可。

---

## 8. Java 21 与 Go 1.22 安装（简要）

本项目还提供 **Java（Spring Boot）** 与 **Go** 实现，文档其它教程会提到运行方式。这里只给最短指引。

### 8.1 Java 21

- 从 [Eclipse Temurin](https://adoptium.net/) 或 Oracle/OpenJDK 发行版安装 **JDK 21**。
- 验证：`java -version` 应显示 21。
- 构建工具：**Maven 3.8+**，验证：`mvn -version`。

### 8.2 Go 1.22

- 从 [https://go.dev/dl/](https://go.dev/dl/) 下载安装。
- 验证：`go version` 应包含 `go1.22` 或更高兼容版本。

---

## 9. 常见问题 FAQ

### Q1：`pip install` 很慢或超时怎么办？

使用国内 PyPI 镜像（见上文 `-i` 参数），或配置 `pip` 全局镜像源。

### Q2：Docker 启动失败，提示虚拟化未开启（Windows）

在 BIOS/UEFI 中开启 **Intel VT-x** 或 **AMD-V**；Windows 上可能还需安装 WSL2 并保证 Docker Desktop 使用 WSL2 后端。

### Q3：`docker compose up` 提示端口被占用

修改 `.env` 里 `CLICKHOUSE_HTTP_PORT` / `REDIS_PORT` 等为其它未占用端口，并同步修改应用配置中的连接端口。

### Q4：执行 Python 脚本报 `ModuleNotFoundError`

确认已激活虚拟环境，且从正确的工作目录运行（有时需要设置 `PYTHONPATH` 指向 `python` 目录）。详见部署教程。

### Q5：`.env` 里有中文或空格可以吗？

建议 Key 与路径类值避免奇怪空格；API Key 直接粘贴一行即可。

### Q6：没有 OpenAI Key 能学习本项目吗？

可以。`RUN_MODE=mock` 时大量逻辑使用模拟数据；LLM 相关在 Key 无效时也会走降级/模拟路径（具体以代码为准）。

---

## 10. 小结

你已完成：**Python 3.11+**、**pip 安装 requirements**、**Docker Desktop**、**docker-compose 启动 ClickHouse/Redis**、**`.env` 配置** 与 **基本验证**。下一步建议阅读《AI Agent 基础知识》与《LangGraph 入门教程》，再结合《部署指南》运行各语言版本。

如有报错，请把**完整错误信息**、操作系统版本、Python/Docker 版本一并记录，便于排查。
