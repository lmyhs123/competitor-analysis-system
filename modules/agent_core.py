# -*- coding: utf-8 -*-
"""
============================================================
 agent_core.py — 插件化多 Agent 智能体核心
============================================================
 职责（对应业务模块三「插件化多Agent智能对标分析」）：
   - 统一抽象基类 + 抽象属性 name（全局唯一插件标识）
   - 全局注册表 + 装饰器自动注册（支持热插拔扩展）
   - 三类内置智能体：价格监控 / 新品迭代 / 负面舆情
   - 调度器并行编排多 Agent 协作分析
   - 基于 Claude Function Calling 实现工具自主调用

 扩展规范（新增分析维度）：
     @AGENT_REGISTRY.register
     class MyAgent(AbstractAgent):
         name = "my_agent"
         def analyze(self, docs): ...

     # 无需修改核心调度代码即可被系统调用
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, ClassVar, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from .data_loader import Document
from .llm_client import get_llm
from . import prompts

logger = logging.getLogger(__name__)


# ============================================================
# 抽象基类：统一插件接口
# ============================================================
class AbstractAgent(ABC):
    """所有竞品分析智能体的统一抽象基类。

    子类必须：
      1. 定义类属性 `name`（全局唯一插件标识）
      2. 实现 `analyze()` 方法
    """

    # 抽象属性：插件唯一标识（子类必须覆写为非空字符串）
    name: ClassVar[str] = ""

    # 该 Agent 偏好的模型层级，子类可覆盖
    model_tier: ClassVar[str] = "sonnet"

    def __init__(self) -> None:
        if not type(self).name:
            raise TypeError(f"{type(self).__name__} 必须定义非空类属性 `name` 作为插件标识")

    @abstractmethod
    def analyze(self, documents: list[Document]) -> dict:
        """对该 Agent 负责维度执行分析，返回结构化结果（dict）。"""

    # ---- 公共辅助：调用 LLM 并解析 JSON ----
    def _invoke_json(self, system_prompt: str, schema: dict, context: str, few_shot: str = "") -> dict:
        full_prompt = prompts.build_analysis_prompt(
            system=system_prompt, schema=schema, few_shot=few_shot, context=context
        )
        llm = get_llm(self.model_tier)
        res = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=full_prompt)])
        text = getattr(res, "content", str(res)).strip()
        # 容错：剥离可能的 ```json 代码块标记
        if text.startswith("```"):
            text = text.strip("`").lstrip("json").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Agent %s 输出非合法 JSON，返回原始文本", self.name)
            return {"raw_output": text, "parse_error": True}


# ============================================================
# 全局注册表：装饰器自动注册 + 统一管理 + 动态调度
# ============================================================
class AgentRegistry:
    """插件注册表：通过装饰器自动完成插件注册"""

    def __init__(self) -> None:
        self._agents: dict[str, type[AbstractAgent]] = {}

    def register(self, agent_cls: type[AbstractAgent]) -> type[AbstractAgent]:
        """类装饰器：注册 Agent 插件"""
        if not issubclass(agent_cls, AbstractAgent):
            raise TypeError(f"{agent_cls.__name__} 必须继承 AbstractAgent")
        name = getattr(agent_cls, "name", "")
        if not name:
            raise TypeError(f"{agent_cls.__name__} 缺少类属性 name")
        if name in self._agents:
            logger.warning("Agent '%s' 已存在，被 %s 覆盖", name, agent_cls.__name__)
        self._agents[name] = agent_cls
        logger.info("注册 Agent 插件: %s -> %s", name, agent_cls.__name__)
        return agent_cls

    def list_names(self) -> list[str]:
        return list(self._agents.keys())

    def get(self, name: str) -> Optional[type[AbstractAgent]]:
        return self._agents.get(name)

    def instantiate(self, name: str) -> Optional[AbstractAgent]:
        cls = self._agents.get(name)
        return cls() if cls else None

    def instantiate_all(self) -> list[AbstractAgent]:
        return [cls() for cls in self._agents.values()]


# 全局唯一注册表实例
AGENT_REGISTRY = AgentRegistry()


# ============================================================
# 内置 Agent 一：价格监控智能体
# ============================================================
@AGENT_REGISTRY.register
class PriceAgent(AbstractAgent):
    name = "price"
    model_tier = "sonnet"

    def analyze(self, documents: list[Document]) -> dict:
        if not documents:
            return {"competitor": "", "price_items": [], "summary": "无可用素材", "alerts": []}
        context = "\n".join(f"[{d.source}] {d.content[:500]}" for d in documents)
        return self._invoke_json(
            system_prompt=prompts.PRICE_SYSTEM,
            schema=prompts.PRICE_SCHEMA,
            few_shot=prompts.PRICE_FEW_SHOT,
            context=context,
        )


# ============================================================
# 内置 Agent 二：新品迭代智能体
# ============================================================
@AGENT_REGISTRY.register
class ProductAgent(AbstractAgent):
    name = "product"
    model_tier = "sonnet"

    def analyze(self, documents: list[Document]) -> dict:
        if not documents:
            return {"competitor": "", "changes": [], "summary": "无可用素材", "recommendations": []}
        context = "\n".join(f"[{d.source}] {d.content[:500]}" for d in documents)
        return self._invoke_json(
            system_prompt=prompts.PRODUCT_SYSTEM,
            schema=prompts.PRODUCT_SCHEMA,
            few_shot="",
            context=context,
        )


# ============================================================
# 内置 Agent 三：负面舆情智能体
# ============================================================
@AGENT_REGISTRY.register
class SentimentAgent(AbstractAgent):
    name = "sentiment"
    model_tier = "sonnet"

    def analyze(self, documents: list[Document]) -> dict:
        if not documents:
            return {"competitor": "", "issues": [], "overall_sentiment": "neutral", "summary": "无可用素材"}
        context = "\n".join(f"[{d.source}] {d.content[:500]}" for d in documents)
        return self._invoke_json(
            system_prompt=prompts.SENTIMENT_SYSTEM,
            schema=prompts.SENTIMENT_SCHEMA,
            few_shot="",
            context=context,
        )


# ============================================================
# 调度器：并行编排多 Agent
# ============================================================
class AgentOrchestrator:
    """多 Agent 并行调度 + 结果聚合"""

    def __init__(self, agent_names: Optional[list[str]] = None) -> None:
        if agent_names:
            self._agents = [AGENT_REGISTRY.instantiate(n) for n in agent_names if AGENT_REGISTRY.get(n)]
        else:
            self._agents = AGENT_REGISTRY.instantiate_all()
        if not self._agents:
            raise RuntimeError("无可用 Agent 插件，请先注册")

    def run(self, documents: list[Document]) -> dict[str, dict]:
        """并行执行所有 Agent，返回 {agent_name: result}"""
        results: dict[str, dict] = {}
        with ThreadPoolExecutor(max_workers=min(4, len(self._agents))) as pool:
            future_map = {pool.submit(agent.analyze, documents): agent.name for agent in self._agents}
            for fut in as_completed(future_map):
                name = future_map[fut]
                try:
                    results[name] = fut.result()
                except Exception as e:
                    logger.error("Agent %s 执行失败: %s", name, e)
                    results[name] = {"error": str(e)}
        return results
