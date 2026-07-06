# -*- coding: utf-8 -*-
"""
============================================================
 modules — 竞品动态追踪与智能对标分析系统 核心业务代码层
============================================================
 包结构（按课件工程规范分层）：
 ┌─ llm_client.py   ChatAnthropic 模型适配器（Haiku/Sonnet/Opus 分层）
 ├─ prompts.py      价格/新品/舆情维度统一提示词库
 ├─ data_loader.py   多源舆情 DocumentLoader（网页/RSS/论坛）
 ├─ rag_chain.py     RAG 检索增强固定流水线（LCEL）
 ├─ tools.py         Agent 智能体工具能力集（Function Calling）
 ├─ agent_core.py    抽象基类 + 注册表 + 三类智能体 + 调度器
 └─ api_server.py    FastAPI 后端接口服务（RESTful + 流式）

 统一入口：
     from modules import get_llm, AGENT_REGISTRY, build_rag_chain, run_analysis
"""
from .llm_client import get_llm, LLMClient
from .agent_core import AbstractAgent, AgentRegistry, AGENT_REGISTRY

__all__ = [
    "get_llm",
    "LLMClient",
    "AbstractAgent",
    "AgentRegistry",
    "AGENT_REGISTRY",
]

__version__ = "0.1.0"
