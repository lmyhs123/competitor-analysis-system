# Claude API + LangChain + Python 环境搭建报告

> 完成时间：2026-07-06  
> 项目路径：`D:\WorkStation\claude_competitor`

---

## 一、环境概览

| 项目 | 值 |
|------|-----|
| 操作系统 | Windows |
| Python 版本 | 3.12.10（虚拟环境内） |
| 虚拟环境路径 | `venv/` |
| 激活方式 | `venv\Scripts\activate` |

---

## 二、已安装依赖清单

### 核心基础包（步骤三.1）
| 包名 | 版本 | 用途 |
|------|------|------|
| python-dotenv | 1.2.2 | 读取 .env 中的 API 密钥 |
| pydantic | 2.13.4 | 结构化 Schema 定义 |
| jsonschema | 4.26.0 | 工具输出格式校验 |
| pandas | 3.0.3 | CSV 报表读写 |

### Anthropic 官方 SDK（步骤三.2）
| 包名 | 版本 | 用途 |
|------|------|------|
| anthropic | 0.116.0 | Claude API 官方客户端 |

### LangChain 全套组件（步骤三.3）
| 包名 | 版本 | 用途 |
|------|------|------|
| langchain | 1.3.11 | Agent / 执行器 / 提示词框架 |
| langchain-anthropic | 1.4.8 | Claude 专用对接封装 |
| langchain-core | 1.4.8 | 消息 / 工具 / 流式基础组件 |
| langgraph | 1.2.7 | LangChain 依赖（自动安装） |
| langsmith | 0.9.7 | LangChain 可观测性（自动安装） |

### 拓展开发配套（步骤七）
| 包名 | 版本 | 用途 |
|------|------|------|
| aiohttp | 3.14.1 | 流式输出 / 异步请求 |
| numpy | 2.5.1 | 数据处理增强 |

### 传递依赖（节选）
httpx, httpcore, anyio, pydantic-core, requests, urllib3, PyYAML, tenacity, orjson, websockets, yarl, multidict 等共 49 个包。

---

## 三、项目文件结构

```
D:\WorkStation\claude_competitor\
├── .env                  # API 配置（占位符，需替换为真实密钥）
├── .env.example          # 配置示例（可安全提交到仓库）
├── .gitignore            # 忽略 .env / venv / 缓存等
├── test_claude.py        # 连通性测试脚本
├── SETUP_REPORT.md       # 本报告
└── venv/                 # Python 虚拟环境
```

---

## 四、配置说明（步骤四）

### `.env` 文件说明
项目根目录已创建 `.env`，包含以下字段：

```env
# 必填：Anthropic API 密钥
ANTHROPIC_API_KEY=sk-ant-你的密钥

# 可选：中转平台地址（官方直连请保持注释）
# ANTHROPIC_BASE_URL=https://你的中转网关地址
```

### 安全规范
- `.env` 已加入 `.gitignore`，不会被提交到代码仓库
- 同时提供 `.env.example` 作为配置模板，可安全提交

---

## 五、连通性测试（步骤五）

### 测试脚本
`test_claude.py` 已创建，支持：
- 自动加载 `.env` 配置
- 自动检测中转平台（配置了 `ANTHROPIC_BASE_URL` 则启用）
- 密钥脱敏显示
- 友好的错误提示（密钥未配置 / 网络错误 / 余额不足等排查建议）

### 运行方式
```bash
# 1. 激活虚拟环境
venv\Scripts\activate

# 2. 编辑 .env，填入真实 API Key
#    （将 ANTHROPIC_API_KEY=sk-ant-你的密钥 改为真实密钥）

# 3. 运行测试
python test_claude.py
```

### 预期输出
- ✅ 配置正确：输出 Claude 对"竞品情报分析作用"的回复
- ❌ 密钥未配置：提示在 `.env` 中填写真实密钥
- ❌ 网络/余额问题：输出错误类型及排查建议

### 当前状态
脚本已通过语法检查与配置校验逻辑测试。**待填入真实 API Key 后即可完成端到端连通性验证。**

---

## 六、后续使用建议

### 1. VS Code 集成（步骤六）
- 打开 VS Code → 文件 → 打开文件夹 → 选择 `D:\WorkStation\claude_competitor`
- `Ctrl + Shift + P` → `Python: Select Interpreter` → 选择 `venv\Scripts\python.exe`
- 推荐插件：Python、Pylint、black-formatter

### 2. 模型选择
`test_claude.py` 默认使用 `claude-3-sonnet-20240229`。可通过 `.env` 中追加 `ANTHROPIC_MODEL=xxx` 切换，例如：
- `claude-sonnet-4-20250514`
- `claude-3-5-sonnet-20241022`

### 3. 依赖冻结（推荐）
后续可用以下命令导出依赖快照，便于环境复现：
```bash
venv\Scripts\pip.exe freeze > requirements.txt
```
