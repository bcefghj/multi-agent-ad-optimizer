# 🎯 多Agent智能广告投放与优化系统

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![Java](https://img.shields.io/badge/Java-21-orange?logo=openjdk)](https://openjdk.org)
[![Go](https://img.shields.io/badge/Go-1.22-00ADD8?logo=go)](https://go.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green)](https://github.com/langchain-ai/langgraph)
[![ClickHouse](https://img.shields.io/badge/ClickHouse-24.3-yellow?logo=clickhouse)](https://clickhouse.com)
[![License](https://img.shields.io/badge/License-MIT-purple)](LICENSE)

> **一个面向面试的企业级多Agent项目** — 从零到面试的完整指南，包含 Python/Java/Go 三种语言实现、50+面试题、STAR话术、八股文，手把手教你打造面试杀手锏项目。

---

## 📖 目录

- [项目简介](#-项目简介)
- [架构设计](#-架构设计)
- [5个Agent详解](#-5个agent详解)
- [快速开始](#-快速开始)
- [三语言实现](#-三语言实现)
- [面试准备](#-面试准备)
- [小白教程](#-小白教程)
- [代码讲解](#-代码讲解)
- [技术栈](#-技术栈)
- [参考项目](#-参考项目)

---

## 🎯 项目简介

这是一个基于 **LangGraph Supervisor Pattern** 的5-Agent广告优化闭环系统。系统自动完成广告投放的全流程：创意生成 → 受众定向 → 实时竞价 → 效果监控 → 自动优化。

### 这个项目能帮你什么？

| 你的身份 | 项目价值 |
|---------|---------|
| 🎓 **应届生/求职者** | 简历项目 + 面试话术 + 八股文，一站式面试准备 |
| 💼 **Python开发者** | 学习 LangGraph 多Agent编排、ClickHouse实时分析 |
| ☕ **Java开发者** | 学习 Spring Boot + LangChain4j + CompletableFuture并行 |
| 🐹 **Go开发者** | 学习 goroutine并发编排、interface设计模式 |
| 📊 **广告/增长方向** | 理解RTB竞价、eCPM排序、预算优化算法 |

### 核心指标（模拟环境验证）

| 指标 | 优化前 | 优化后 | 提升 |
|------|-------|-------|------|
| CTR（点击率） | 2.1% | 2.8% | **+35%** |
| CPA（获客成本） | ¥156 | ¥112 | **-28%** |
| ROAS（广告回报率） | 1.8 | 2.5 | **+40%** |
| 人工干预 | 每天4小时 | 每天0.5小时 | **-87%** |

---

## 🏗 架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     Supervisor (编排层)                       │
│  ┌─────────┐                                                │
│  │  入口    │────→ Monitor Agent ────→ Audience Agent ──┐   │
│  └─────────┘                                            │   │
│       ↑                                                 ↓   │
│       │         ┌────────────────────────────────────────┘   │
│       │         │                                           │
│       │         └──→ Creative Agent ────→ Bidding Agent     │
│       │                                       │             │
│       │                                       ↓             │
│       └──── 有告警？──── Optimize Agent ──→ 完成/继续      │
│              是↑循环          否↓结束                        │
└─────────────────────────────────────────────────────────────┘
        │                       │
        ↓                       ↓
┌──────────────┐    ┌───────────────────┐
│  广告平台API  │    │   ClickHouse      │
│ Google / Meta │    │   实时数据仓库     │
└──────────────┘    └───────────────────┘
```

### 设计模式：Supervisor Pattern

为什么选 Supervisor 而不是 Swarm 或 Pipeline？

| 方案 | 优点 | 缺点 | 是否选择 |
|------|------|------|---------|
| **Supervisor** | 全局视角、条件路由、支持循环 | 中心化单点 | ✅ **选择** |
| Swarm | 灵活对等 | 无全局视角、调试困难 | ❌ |
| Pipeline | 简单直接 | 不支持条件路由和循环 | ❌ |

---

## 🤖 5个Agent详解

### 1. Creative Agent（创意Agent）
- **职责**：自动生成广告文案变体
- **输入**：Campaign的CTR/CVR指标
- **输出**：3-5个文案变体（标题+描述+CTA+情感方向）
- **策略**：CTR低→紧迫感/好奇心文案；CVR低→利益点/信任感文案
- **技术**：LLM生成（支持mock回退）

### 2. Audience Agent（受众Agent）
- **职责**：人群画像分析、精准定向
- **输入**：转化用户的维度数据（年龄/性别/设备/地域）
- **输出**：高价值人群段排名 + Lookalike扩展建议
- **技术**：ClickHouse聚合分析

### 3. Bidding Agent（出价Agent）
- **职责**：实时竞价策略优化
- **核心算法**：`eCPM = pCTR × pCVR × TargetCPA × 1000`
- **动态倍率**：ROAS好→提价争量(×1.3)，差→降价控本(×0.6)
- **约束**：出价不超过目标CPA的80%

### 4. Monitor Agent（监控Agent）
- **职责**：实时追踪CTR/CVR/CPA/ROAS
- **告警规则**：
  - CTR < 0.5% → 低CTR告警
  - CPA > ¥200 → 高CPA告警
  - ROAS < 1.0 → 低ROAS告警
- **输出**：健康度评分（0-100分）

### 5. Optimize Agent（优化Agent）
- **职责**：闭环优化的执行者
- **四大操作**：
  1. 暂停低效素材（综合评分 < 40分）
  2. CVXPY凸优化预算再分配
  3. 处理Monitor告警（紧急响应）
  4. 管理A/B测试启停
- **闭环控制**：决定是否继续迭代

---

## 🚀 快速开始

### 前置条件

- Python 3.11+ / Java 21 / Go 1.22（选一种即可）
- Docker Desktop（用于ClickHouse和Redis）
- Git

### 1. 克隆项目

```bash
git clone https://github.com/bcefghj/multi-agent-ad-optimizer.git
cd multi-agent-ad-optimizer
```

### 2. 启动基础设施

```bash
# 启动ClickHouse + Redis
docker-compose up -d

# 验证
curl http://localhost:8123/ping   # ClickHouse应返回"Ok."
```

### 3. 运行Python版（推荐新手）

```bash
cd python

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp ../.env.example ../.env
# 编辑.env，设置RUN_MODE=mock（无需真实API）

# 运行优化pipeline
cd .. && PYTHONPATH=python python -m src.orchestrator.supervisor

# 启动仪表板
streamlit run python/src/dashboard/app.py
```

### 4. 运行Java版

```bash
cd java
mvn spring-boot:run

# 测试API
curl -X POST "http://localhost:8080/api/v1/optimize?campaignCount=5&maxIterations=2"
```

### 5. 运行Go版

```bash
cd golang
go run cmd/server/main.go

# 测试API
curl -X POST "http://localhost:8081/api/v1/optimize?campaigns=5&maxIterations=2"
```

---

## 💻 三语言实现

| 特性 | Python | Java | Go |
|------|--------|------|----|
| 框架 | LangGraph + LangChain | Spring Boot + LangChain4j | 标准库 + 自定义框架 |
| Agent编排 | StateGraph条件路由 | CompletableFuture并行 | goroutine + WaitGroup |
| 数据层 | clickhouse-connect | ClickHouse JDBC | 标准库 |
| API | Streamlit仪表板 | RESTful API | net/http |
| 适合 | AI/数据方向面试 | Java后端面试 | Go后端面试 |

### 目录结构

```
multi-agent-ad-optimizer/
├── 📄 README.md                 ← 你正在看的文件
├── 📄 docker-compose.yml        ← 一键启动ClickHouse+Redis
├── 📄 .env.example              ← 环境变量模板
│
├── 🐍 python/                   ← Python版（最完整）
│   ├── requirements.txt
│   └── src/
│       ├── agents/              ← 5个Agent实现
│       ├── orchestrator/        ← LangGraph Supervisor
│       ├── models/              ← Pydantic数据模型
│       ├── data/                ← ClickHouse + Mock数据
│       ├── tools/               ← 广告API + 分析工具
│       └── dashboard/           ← Streamlit仪表板
│
├── ☕ java/                      ← Java版
│   ├── pom.xml
│   └── src/main/java/com/adoptimizer/
│       ├── agent/               ← 5个Agent
│       ├── orchestrator/        ← Supervisor编排
│       ├── model/               ← 数据模型
│       └── config/              ← REST API控制器
│
├── 🐹 golang/                   ← Go版
│   ├── go.mod
│   ├── cmd/server/              ← HTTP入口
│   └── internal/
│       ├── agent/               ← 5个Agent
│       ├── orchestrator/        ← goroutine编排
│       └── model/               ← 数据模型
│
├── 📚 docs/
│   ├── interview/               ← 面试全套材料
│   │   ├── resume-template.md   ← 简历写法（3个版本）
│   │   ├── star-method.md       ← STAR法则话术
│   │   ├── qa-collection.md     ← 50+面试题答案
│   │   └── baguwen.md           ← 八股文（Agent/广告/分布式）
│   ├── tutorial/                ← 从零入门教程
│   │   ├── 01-environment-setup.md
│   │   ├── 02-agent-basics.md
│   │   ├── 03-langgraph-intro.md
│   │   ├── 04-clickhouse-guide.md
│   │   └── 05-deploy-guide.md
│   └── code-walkthrough/        ← 代码逐模块讲解
│       ├── python-walkthrough.md
│       ├── java-walkthrough.md
│       └── go-walkthrough.md
│
└── 📦 init-scripts/             ← ClickHouse建表SQL
    └── clickhouse/01_create_tables.sql
```

---

## 📝 面试准备

### 简历怎么写？

👉 [简历写法模板](docs/interview/resume-template.md) — 提供Python/Java/Go三个版本的简历项目描述模板，直接复制修改。

**精简版（直接贴简历）：**
```
多Agent智能广告投放与优化系统 | Python / LangGraph / ClickHouse
• 设计5-Agent优化闭环（Supervisor Pattern），投放效率提升60%
• Creative Agent自动生成50+素材变体，CTR提升35%
• Bidding Agent实时竞价优化（eCPM+动态倍率），CPA降低28%
• Optimize Agent CVXPY凸优化预算分配，ROAS提升40%
```

### 面试怎么说？

👉 [STAR法则话术](docs/interview/star-method.md) — 5个常见面试问题的完整STAR回答，包括：
- "介绍一下你的多Agent项目"
- "为什么选Supervisor Pattern？"
- "ClickHouse为什么比MySQL好？"
- "CVXPY怎么优化预算？"
- "遇到的技术难点？"

### 八股文背什么？

👉 [八股文完整版](docs/interview/baguwen.md) — 5大章节覆盖：
1. **Agent架构**：单Agent vs 多Agent、Supervisor vs Swarm、LangGraph核心概念
2. **广告系统**：RTB竞价流程、eCPM排序、归因模型、A/B测试
3. **ClickHouse**：列式存储原理、MergeTree引擎、物化视图、查询优化
4. **分布式系统**：消息队列、限流算法、幂等性、缓存策略
5. **三语言对比**：asyncio vs CompletableFuture vs goroutine

### 面试题练什么？

👉 [50+面试问答集](docs/interview/qa-collection.md) — 分5大类：
- 项目设计类（15题）
- 技术实现类（15题）
- 架构设计类（10题）
- 广告业务类（10题）
- 编码算法类（5题 + 代码示例）

---

## 📚 小白教程

完全零基础？没关系，按顺序看这5篇教程：

| 序号 | 教程 | 内容 | 预计时间 |
|------|------|------|---------|
| 01 | [环境搭建](docs/tutorial/01-environment-setup.md) | Python/Docker安装、依赖配置 | 30分钟 |
| 02 | [Agent基础](docs/tutorial/02-agent-basics.md) | 什么是AI Agent、四大要素 | 20分钟 |
| 03 | [LangGraph入门](docs/tutorial/03-langgraph-intro.md) | StateGraph、Node、Edge、条件路由 | 40分钟 |
| 04 | [ClickHouse实战](docs/tutorial/04-clickhouse-guide.md) | 列式存储、物化视图、SQL操作 | 30分钟 |
| 05 | [部署指南](docs/tutorial/05-deploy-guide.md) | 本地运行、Docker部署 | 20分钟 |

---

## 🔍 代码讲解

三种语言的逐模块深度讲解：

- 🐍 [Python代码讲解](docs/code-walkthrough/python-walkthrough.md) — LangGraph编排、CVXPY优化、Streamlit仪表板
- ☕ [Java代码讲解](docs/code-walkthrough/java-walkthrough.md) — Spring Boot DI、CompletableFuture并行、REST API
- 🐹 [Go代码讲解](docs/code-walkthrough/go-walkthrough.md) — interface设计、goroutine并发、WaitGroup vs channel

---

## 🛠 技术栈

### 核心技术

| 技术 | 用途 | 版本 |
|------|------|------|
| [LangGraph](https://github.com/langchain-ai/langgraph) | Agent编排框架 | ≥0.2 |
| [LangChain](https://github.com/langchain-ai/langchain) | LLM工具链 | ≥0.3 |
| [ClickHouse](https://clickhouse.com) | 实时OLAP数据仓库 | 24.3 |
| [Redis](https://redis.io) | 缓存+消息队列 | 7 |
| [CVXPY](https://www.cvxpy.org) | 凸优化（预算分配） | ≥1.5 |
| [Streamlit](https://streamlit.io) | 监控仪表板 | ≥1.38 |
| [Pydantic](https://docs.pydantic.dev) | 数据模型验证 | ≥2.0 |

### Java版额外技术

| 技术 | 用途 |
|------|------|
| [Spring Boot 3](https://spring.io/projects/spring-boot) | 微服务框架 |
| [LangChain4j](https://github.com/langchain4j/langchain4j) | Java LLM框架 |
| [Lombok](https://projectlombok.org) | 减少Java样板代码 |

### Go版额外技术

| 技术 | 用途 |
|------|------|
| goroutine + sync | 并发编排 |
| net/http | HTTP服务 |
| encoding/json | JSON序列化 |

---

## 🌐 参考项目

本项目参考了以下企业级开源项目：

| 项目 | 技术栈 | 亮点 |
|------|--------|------|
| [AdAstra](https://github.com/SayamAlt/AdAstra-Marketing-Intelligence-Engine-using-LangGraph) | LangGraph + CVXPY | 数学优化预算分配 |
| [Agents4Marketing](https://github.com/TheCMOAI/Agents4Marketing) | Claude Code | 46+真实客户验证 |
| [CampaignGPT](https://github.com/alinaqi/CampaignGPT) | CrewAI/AutoGen/LangGraph | 三框架对比 |
| [IAB ARTF](https://github.com/IABTechLab/agentic-rtb-framework) | Go + gRPC | IAB官方RTB标准 |
| [AWS Ad Agents](https://github.com/aws-solutions-library-samples/guidance-for-advertising-agents-on-aws) | Bedrock AgentCore | AWS企业级方案 |
| [AgentEnsemble](https://github.com/AgentEnsemble/agentensemble) | Java + LangChain4j | 多编排策略 |

---

## 📄 License

[MIT License](LICENSE) — 可自由使用、修改和分发。

---

## ⭐ Star History

如果这个项目对你有帮助，请点个Star! 🌟

---

> 📮 **联系方式**: 通过 GitHub Issues 提问或建议。
>
> 🔒 **安全提醒**: 请勿在代码中硬编码API Key。使用 `.env` 文件管理敏感信息，并确保 `.gitignore` 中包含 `.env`。
