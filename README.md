# 竞品动态追踪与智能对标分析系统

> 基于 Claude Skill 的插件化多 Agent 竞品情报分析平台
> 技术栈：Anthropic Claude + LangChain + Multi-Agent + RAG + FastAPI

---

## 项目简介

本系统以 Anthropic Claude 大模型为智能内核，结合 LangChain 框架、Multi-Agent 多智能体协作与 RAG 检索增强技术，聚焦**价格战、新品发布、负面舆情**三大核心监控维度，实现竞品情报**采集 → 清洗 → 结构化解析 → 横向对标 → 时序分析 → 风险预警 → 智能报告生成**的全链路自动化。

采用插件化 Agent 架构，支持业务模块热插拔扩展，可长期沉淀竞品数据，为产品迭代、定价策略、市场运营及风险防控提供标准化、可落地的智能决策支撑。

---

## 目录结构

```
claude_competitor/
├── .env                       密钥、模型参数、全局配置（禁止硬编码）
├── .env.example               配置示例文件
├── .gitignore                 Git 忽略规则
├── requirements.txt           项目统一依赖清单
├── venv/                      Python 虚拟环境
├── data/raw/                  原始舆情数据目录
│   └── news.csv               舆情原始文件（示例占位）
├── chroma_db/                 向量数据库持久化存储目录
├── memory/                    历史分析记忆持久化目录
├── modules/                   项目核心业务代码层
│   ├── __init__.py            包入口
│   ├── llm_client.py          ChatAnthropic 模型适配器（Haiku/Sonnet/Opus 分层）
│   ├── prompts.py            价格/新品/舆情维度统一提示词库
│   ├── data_loader.py         多源舆情 DocumentLoader（网页/RSS）
│   ├── rag_chain.py           RAG 检索增强固定流水线
│   ├── tools.py               Agent 智能体工具能力集
│   ├── agent_core.py          抽象基类 + 注册表 + 三类智能体 + 调度器
│   └── api_server.py          FastAPI 后端接口服务
├── test_claude.py             Claude API 连通性测试（增强版）
├── test_anthropic.py          课件标准测试脚本
├── docs/                      项目全套交付文档
│   ├── 业务功能说明.md
│   └── 架构分析说明.md
└── README.md                  本文件
```

---

## 环境搭建

### 1. 前置条件
- Python 3.10 / 3.11 / 3.12（本项目使用 3.12.10）
- 已激活项目虚拟环境 `venv`

### 2. 激活虚拟环境
```bash
# Windows CMD
venv\Scripts\activate

# Windows PowerShell
venv\Scripts\Activate.ps1

# Mac / Linux
source venv/bin/activate
```

### 3. 安装依赖
```bash
venv\Scripts\pip install -r requirements.txt
```

### 4. 配置 API 密钥
编辑项目根目录 `.env`，填入你的真实 Claude API 密钥：
```env
ANTHROPIC_API_KEY=sk-ant-你的真实密钥
```
如使用中转平台，取消 `ANTHROPIC_BASE_URL` 注释并填入网关地址。

### 5. 验证连通性
```bash
python test_anthropic.py
# 或增强版测试
python test_claude.py
```

---

## 快速开始

### 启动 API 服务
```bash
# 方式一：uvicorn
uvicorn modules.api_server:app --reload --port 8000

# 方式二：直接运行模块
python -m modules.api_server
```

启动后访问 Swagger 文档：http://localhost:8000/docs

### 核心代码调用
```python
from modules.agent_core import AGENT_REGISTRY, AgentOrchestrator
from modules.data_loader import DataLoader, Document

# 1. 采集舆情
docs = DataLoader().collect_incremental(["竞品A"])

# 2. 写入向量库
from modules.rag_chain import build_rag_chain
rag = build_rag_chain()
rag.add_documents(docs)

# 3. 多 Agent 并行分析
results = AgentOrchestrator().run(rag.retrieve("竞品A 最新动态", competitor="竞品A"))
print(results)
```

---

## API 接口概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/health` | 健康检查 |
| GET  | `/api/agents` | 列出已注册 Agent 插件 |
| POST | `/api/collect` | 触发舆情增量采集 |
| POST | `/api/analyze` | 多 Agent 并行分析 |
| POST | `/api/analyze/stream` | 流式分析输出（SSE） |
| POST | `/api/report` | 生成竞品分析简报 |

完整接口文档见 Swagger UI：`/docs`

---

## 模型分层调用

| 层级 | 环境变量 | 适用场景 |
|------|---------|---------|
| Haiku | `MODEL_HAIKU` | 高速抓取 / 清洗 / 轻量分类 |
| Sonnet | `MODEL_SONNET` | 结构化分析 / 维度对比 / 工具调用 |
| Opus | `MODEL_OPUS` | 战略研判 / 报告生成 / 深度分析 |

均可在 `.env` 中修改，无需改动代码。

---

## 插件扩展指南

新增一个分析维度只需 3 步：

```python
# 1. 在 modules/agent_core.py 末尾添加
@AGENT_REGISTRY.register
class MarketShareAgent(AbstractAgent):
    name = "market_share"           # 唯一标识
    model_tier = "sonnet"           # 模型层级

    def analyze(self, documents: list[Document]) -> dict:
        # 2. 实现分析逻辑（复用 prompts + LLM）
        ...

# 3. 重启服务，新 Agent 自动被调度器识别
```

无需修改任何核心调度代码，即实现热插拔扩展。

---

## 工程规范

本项目严格遵循六大工程规范（详见 `docs/`）：
1. **目录分层规范** — 数据 / 模型 / 提示词 / 工具 / 接口 完全解耦
2. **安全开发规范** — 敏感信息统一存放 `.env`，禁止硬编码
3. **AI 智能开发规范** — Prompt 集中管理，低温度抑制幻觉，结论可溯源
4. **舆情数据规范** — 保留来源 / 时间 / 原始内容元数据
5. **代码开发规范** — 公共方法封装，标准异常捕获与日志
6. **项目文档规范** — 全流程文档留存，符合工程化交付要求

---

## 常见问题

| 问题 | 解决方案 |
|------|---------|
| 调用报 401 | 检查 `.env` 密钥完整、无空格 |
| 网络超时（官方直连） | 使用中转平台并配置 `ANTHROPIC_BASE_URL` |
| 导入模块报错 | 确认已激活 venv，依赖全部安装 |
| PowerShell 无法激活 | 管理员执行 `Set-ExecutionPolicy RemoteSigned` |
| Chroma 初始化失败 | 确认 `chromadb` 与 `langchain-chroma` 已安装 |
