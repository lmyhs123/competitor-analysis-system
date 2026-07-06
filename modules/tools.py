# -*- coding: utf-8 -*-
"""
============================================================
 tools.py — Agent 智能体工具能力集
============================================================
 职责（对应「Multi-Agent 多智能体插件层」的工具调用能力）：
   - 基于 LangChain @tool 装饰器声明工具 schema
   - 让 Agent 自主选择 检索 / 对比 / 总结 等工具
   - 与 Claude Function Calling 对接

 已内置工具：
   - search_intel        检索竞品历史情报（走 RAG 向量库）
   - compare_price       价格对比工具
   - fetch_latest_news   获取竞品最新动态（走 DataLoader）
   - summarize           文本摘要工具
"""
from __future__ import annotations

import logging
from typing import Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def search_intel(query: str, competitor: Optional[str] = None, category: Optional[str] = None) -> str:
    """检索竞品历史情报。用于查询价格、新品、舆情等历史动态。

    Args:
        query: 检索问题，如「竞品A近一个月价格变化」
        competitor: 限定竞品名称，为空则全库检索
        category: 限定维度 price|product|sentiment，为空则不限
    """
    from .rag_chain import build_rag_chain  # 延迟导入避免循环依赖

    rag = build_rag_chain()
    docs = rag.retrieve(query, competitor=competitor, category=category, k=5)
    if not docs:
        return "未检索到相关历史情报。"
    lines = []
    for i, d in enumerate(docs, 1):
        meta = d.metadata
        lines.append(
            f"[{i}] {meta.get('competitor','?')} | {meta.get('source','?')} "
            f"| {meta.get('collect_time','?')}\n{d.page_content[:300]}"
        )
    return "\n\n".join(lines)


@tool
def compare_price(our_price: str, competitor_price: str) -> str:
    """对比我方与竞品价格，输出价差百分比与风险等级。

    Args:
        our_price: 我方价格，如「299元/月」
        competitor_price: 竞品价格，如「254元/月」
    """
    import re

    def _to_float(s: str) -> Optional[float]:
        m = re.search(r"(\d+(?:\.\d+)?)", s)
        return float(m.group(1)) if m else None

    o, c = _to_float(our_price), _to_float(competitor_price)
    if o is None or c is None:
        return "价格格式无法解析，请使用「数字+单位」格式。"
    gap_pct = (c - o) / o * 100
    risk = "high" if abs(gap_pct) >= 15 else ("medium" if abs(gap_pct) >= 8 else "low")
    direction = "更贵" if gap_pct > 0 else "更便宜"
    return f"价差 {gap_pct:+.1f}%（竞品{direction}），风险等级 {risk}。"


@tool
def fetch_latest_news(competitor: str) -> str:
    """获取指定竞品的最新舆情动态（增量采集）。

    Args:
        competitor: 竞品名称
    """
    from .data_loader import DataLoader

    docs = DataLoader().collect_incremental([competitor])
    if not docs:
        return f"未发现 {competitor} 的新增动态。"
    return "\n".join(f"- [{d.source}] {d.content[:80]}" for d in docs[:10])


@tool
def summarize(text: str, max_words: int = 200) -> str:
    """对长文本生成摘要。

    Args:
        text: 待摘要文本
        max_words: 摘要最大字数
    """
    from .llm_client import get_llm

    llm = get_llm("haiku")  # 摘要用快速模型
    res = llm.invoke(f"用不超过{max_words}字概括以下内容：\n{text}")
    return getattr(res, "content", str(res))


# 工具注册表：供 Agent 按需绑定
ALL_TOOLS = [search_intel, compare_price, fetch_latest_news, summarize]
