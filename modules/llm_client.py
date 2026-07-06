# -*- coding: utf-8 -*-
"""
============================================================
 llm_client.py — ChatAnthropic 模型适配器统一封装
============================================================
 职责（对应技术架构「大模型基础层」）：
   - 分层调用策略：Haiku / Sonnet / Opus 按场景自动匹配
   - 统一从 .env 读取密钥与模型名，禁止硬编码
   - 透传中转平台 base_url（ANTHROPIC_BASE_URL）
   - 低温度默认值抑制幻觉（temperature=0.0）

 使用：
     from modules.llm_client import get_llm
     llm = get_llm("sonnet")          # 快速获取对应层级客户端
     res = llm.invoke("...")
"""
from __future__ import annotations

import os
import logging
from functools import lru_cache
from typing import Literal, Optional

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

load_dotenv()
logger = logging.getLogger(__name__)

# ---- 任务层级 → 模型名映射（从 .env 读取，可热替换）----
ModelTier = Literal["haiku", "sonnet", "opus"]

_DEFAULT_MODELS: dict[str, str] = {
    # DeepSeek：三层统一映射到 deepseek-v4-flash（可通过 .env 覆盖）
    "haiku": "deepseek-v4-flash",
    "sonnet": "deepseek-v4-flash",
    "opus": "deepseek-v4-flash",
}

# ---- 各层级默认温度（业务规范：低温度抑制幻觉）----
_DEFAULT_TEMP: dict[str, float] = {
    "haiku": 0.0,   # 抓取/清洗/分类，严格确定性
    "sonnet": 0.0,  # 结构化分析，需稳定可复现
    "opus": 0.3,    # 战略研判，保留适度发散
}

# ---- 各层级默认最大输出 token ----
_DEFAULT_MAX_TOKENS: dict[str, int] = {
    "haiku": 1024,
    "sonnet": 4096,
    "opus": 8192,
}


class LLMClient:
    """ChatAnthropic 分层模型适配器（单例，懒加载）"""

    def __init__(self) -> None:
        self._api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
        self._base_url: Optional[str] = os.getenv("ANTHROPIC_BASE_URL") or None
        self._models: dict[str, str] = {
            tier: os.getenv(f"MODEL_{tier.upper()}", _DEFAULT_MODELS[tier])
            for tier in _DEFAULT_MODELS
        }
        self._instances: dict[str, BaseChatModel] = {}
        if not self._api_key or "你的" in self._api_key or "your_key" in (self._api_key or "").lower():
            logger.warning("ANTHROPIC_API_KEY 未配置或仍为占位符，调用 LLM 时将失败")

    def get(
        self,
        tier: ModelTier = "sonnet",
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        streaming: bool = False,
    ) -> BaseChatModel:
        """获取指定层级的 ChatAnthropic 客户端（带 LRU 缓存）"""
        if tier not in _DEFAULT_MODELS:
            raise ValueError(f"未知模型层级: {tier}，可选: {list(_DEFAULT_MODELS)}")

        cache_key = f"{tier}|{temperature}|{max_tokens}|{streaming}"
        if cache_key in self._instances:
            return self._instances[cache_key]

        kwargs = dict(
            model=self._models[tier],
            api_key=self._api_key,
            temperature=temperature if temperature is not None else _DEFAULT_TEMP[tier],
            max_tokens=max_tokens or _DEFAULT_MAX_TOKENS[tier],
            streaming=streaming,
        )
        if self._base_url:
            # 中转平台：透传给 anthropic SDK
            kwargs["base_url"] = self._base_url

        logger.info("初始化 LLM 客户端 tier=%s model=%s", tier, kwargs["model"])
        client = ChatAnthropic(**kwargs)
        self._instances[cache_key] = client
        return client

    def invoke(
        self,
        prompt: str,
        tier: ModelTier = "sonnet",
        **kwargs,
    ) -> str:
        """便捷调用：直接返回文本内容"""
        client = self.get(tier)
        res = client.invoke(prompt, **kwargs)
        return getattr(res, "content", str(res))


@lru_cache(maxsize=1)
def _singleton() -> LLMClient:
    return LLMClient()


def get_llm(tier: ModelTier = "sonnet", **kwargs) -> BaseChatModel:
    """全局快捷入口：获取分层模型客户端"""
    return _singleton().get(tier, **kwargs)


def get_client() -> LLMClient:
    """获取 LLMClient 单例"""
    return _singleton()
