# -*- coding: utf-8 -*-
"""
============================================================
 api_server.py — FastAPI 后端接口服务
============================================================
 职责（对应业务模块七「服务化接口与可视化看板」）：
   - 将 LangChain 智能分析链路封装为标准 RESTful API
   - 支持异步流式输出
   - 自动生成 Swagger / OpenAPI 文档（/docs）
   - 适配前后端分离架构

 启动：
     uvicorn modules.api_server:app --reload --port 8000
 或：
     python -m modules.api_server

 主要端点：
     GET  /health               健康检查
     GET  /api/agents            列出已注册 Agent 插件
     POST /api/collect           触发舆情增量采集
     POST /api/analyze           触发多 Agent 并行分析
     POST /api/analyze/stream    流式分析输出
     POST /api/report            生成竞品分析简报
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .agent_core import AGENT_REGISTRY, AgentOrchestrator
from .data_loader import DataLoader
from .llm_client import get_llm
from .rag_chain import build_rag_chain
from . import prompts

logger = logging.getLogger(__name__)

# ============================================================
# FastAPI 应用实例
# ============================================================
app = FastAPI(
    title="竞品动态追踪与智能对标分析系统 API",
    description="基于 Claude Skill 的多 Agent 竞品情报分析服务",
    version="0.1.0",
)

# 跨域支持（前后端分离）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 请求 / 响应模型
# ============================================================
class CollectRequest(BaseModel):
    competitors: list[str] = Field(..., example=["竞品A", "竞品B"])


class AnalyzeRequest(BaseModel):
    competitors: list[str] = Field(..., example=["竞品A"])
    agents: Optional[list[str]] = Field(None, example=["price", "product", "sentiment"])


class ReportRequest(BaseModel):
    competitors: list[str] = Field(..., example=["竞品A"])
    report_type: str = Field("day", description="day|week|month")
    tier: str = Field("opus", description="报告生成使用 opus 深度推理")


# ============================================================
# 基础端点
# ============================================================
@app.get("/health")
def health() -> dict:
    """健康检查"""
    return {
        "status": "ok",
        "agents": AGENT_REGISTRY.list_names(),
    }


@app.get("/api/agents")
def list_agents() -> dict:
    """列出已注册 Agent 插件"""
    return {"agents": AGENT_REGISTRY.list_names()}


# ============================================================
# 舆情采集
# ============================================================
@app.post("/api/collect")
def collect(req: CollectRequest) -> dict:
    """触发舆情增量采集并写入向量库"""
    loader = DataLoader()
    docs = loader.collect_incremental(req.competitors)
    if docs:
        rag = build_rag_chain()
        rag.add_documents(docs)
    return {
        "new_count": len(docs),
        "competitors": req.competitors,
    }


# ============================================================
# 多 Agent 分析
# ============================================================
@app.post("/api/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    """触发多 Agent 并行分析"""
    if not AGENT_REGISTRY.list_names():
        raise HTTPException(500, "无已注册 Agent")
    # 先从向量库检索相关情报，作为分析素材
    rag = build_rag_chain()
    docs = []
    for comp in req.competitors:
        docs.extend(rag.retrieve(f"{comp} 最新动态", competitor=comp, k=5))

    orchestrator = AgentOrchestrator(req.agents) if req.agents else AgentOrchestrator()
    results = orchestrator.run(docs)
    return {"competitors": req.competitors, "results": results}


@app.post("/api/analyze/stream")
async def analyze_stream(req: AnalyzeRequest) -> StreamingResponse:
    """流式分析输出（SSE 风格）"""
    async def event_gen():
        orchestrator = AgentOrchestrator(req.agents) if req.agents else AgentOrchestrator()
        rag = build_rag_chain()
        docs = []
        for comp in req.competitors:
            docs.extend(rag.retrieve(f"{comp} 最新动态", competitor=comp, k=5))
        for agent in orchestrator._agents:  # noqa: SLF001
            yield f"event: start\ndata: {json.dumps({'agent': agent.name}, ensure_ascii=False)}\n\n"
            try:
                result = agent.analyze(docs)
                yield f"event: result\ndata: {json.dumps({'agent': agent.name, 'result': result}, ensure_ascii=False)}\n\n"
            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'agent': agent.name, 'error': str(e)}, ensure_ascii=False)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


# ============================================================
# 智能简报生成
# ============================================================
@app.post("/api/report")
def generate_report(req: ReportRequest) -> dict:
    """生成竞品分析简报（使用 Opus 深度推理）"""
    rag = build_rag_chain()
    orchestrator = AgentOrchestrator()
    docs = []
    for comp in req.competitors:
        docs.extend(rag.retrieve(f"{comp} 全维度动态", competitor=comp, k=8))
    results = orchestrator.run(docs)

    # 汇总多 Agent 结果，交给 Opus 生成简报
    import datetime as _dt
    context = json.dumps(results, ensure_ascii=False, indent=2)
    llm = get_llm(req.tier)
    from langchain_core.messages import SystemMessage, HumanMessage
    filled = prompts.REPORT_TEMPLATE.format(
        report_type={"day": "日", "week": "周", "month": "月"}.get(req.report_type, req.report_type),
        start_date=_dt.date.today().isoformat(),
        end_date=_dt.date.today().isoformat(),
        competitors="、".join(req.competitors),
        executive_summary="(见下文各维度结论)",
        price_section=json.dumps(results.get("price", {}), ensure_ascii=False, indent=2),
        product_section=json.dumps(results.get("product", {}), ensure_ascii=False, indent=2),
        sentiment_section=json.dumps(results.get("sentiment", {}), ensure_ascii=False, indent=2),
        alerts_section="(基于各维度 alerts 字段聚合)",
        recommendations="(基于各维度 recommendations 聚合)",
        generated_at=_dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    res = llm.invoke([
        SystemMessage(content=prompts.REPORT_SYSTEM),
        HumanMessage(content=f"多 Agent 分析结果：\n{context}\n\n请据此完善报告：\n{filled}"),
    ])
    return {
        "report": getattr(res, "content", str(res)),
        "tier": req.tier,
        "raw_results": results,
    }


# ============================================================
# 启动入口
# ============================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "modules.api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
