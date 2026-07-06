# -*- coding: utf-8 -*-
"""
============================================================
 rag_chain.py — RAG 检索增强固定流水线
============================================================
 职责（对应技术架构「LangChain 工程框架层 + 向量数据持久层」）：
   - DocumentLoader 加载多源舆情 → TextSplitter 语义分块
   - 向量化存储至 Chroma（持久化目录 chroma_db/）
   - LCEL 声明式组装：retriever | prompt | llm | parser
   - 时序检索：按 竞品 / 维度 / 时间段 过滤历史数据

 Embedding 说明：
   Anthropic 暂不提供官方 embedding 模型，本项目默认使用占位
   StubEmbeddings；正式环境请在 .env 配置 EMBEDDING_PROVIDER，并
   替换为 OpenAI text-embedding-3-small 或本地 sentence-transformers。

 使用：
     from modules.rag_chain import build_rag_chain
     rag = build_rag_chain()
     rag.add_documents(docs)
     answer = rag.analyze("竞品A近一个月价格变化")
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from langchain_core.documents import Document as LCDocument
from langchain_core.embeddings import Embeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .llm_client import get_llm
from .data_loader import Document

load_dotenv()
logger = logging.getLogger(__name__)

CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")


# ============================================================
# 占位 Embedding（框架阶段，避免无 API key 时报错）
# TODO: 正式环境替换为真实 embedding 实现
# ============================================================
class StubEmbeddings(Embeddings):
    """占位 embedding：返回固定维度的零向量，仅用于框架跑通"""

    dim = 384  # 兼容 sentence-transformers 默认维度

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self.dim for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.0] * self.dim


def _get_embeddings() -> Embeddings:
    """根据 .env 选择 embedding 实现，未配置则用 stub"""
    provider = os.getenv("EMBEDDING_PROVIDER", "").strip().lower()
    if provider == "openai":
        try:
            from langchain_openai import OpenAIEmbeddings  # type: ignore
            return OpenAIEmbeddings(model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))
        except Exception as e:
            logger.warning("OpenAI Embeddings 加载失败，回退 stub: %s", e)
    elif provider == "local":
        try:
            from langchain_huggingface import HuggingFaceEmbeddings  # type: ignore
            return HuggingFaceEmbeddings(model_name=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
        except Exception as e:
            logger.warning("本地 Embeddings 加载失败，回退 stub: %s", e)
    return StubEmbeddings()


# ============================================================
# RAG 流水线
# ============================================================
class RAGChain:
    """Chroma 向量库 + LCEL 检索生成链路"""

    def __init__(self, collection_name: str = "competitor_intel") -> None:
        self.collection_name = collection_name
        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=120,
            separators=["\n\n", "\n", "。", "！", "？", " "],
        )
        self._embeddings: Optional[Embeddings] = None
        self._vectorstore = None

    # ---- 懒加载向量库（chromadb 未安装时报清晰错误）----
    def _ensure_vectorstore(self):
        if self._vectorstore is not None:
            return self._vectorstore
        try:
            from langchain_chroma import Chroma  # type: ignore
        except ImportError as e:
            raise ImportError(
                "未安装 langchain-chroma / chromadb，请运行："
                "venv\\Scripts\\pip install langchain-chroma chromadb"
            ) from e
        if self._embeddings is None:
            self._embeddings = _get_embeddings()
        self._vectorstore = Chroma(
            collection_name=self.collection_name,
            embedding_function=self._embeddings,
            persist_directory=CHROMA_DIR,
        )
        logger.info("Chroma 向量库已初始化: collection=%s dir=%s", self.collection_name, CHROMA_DIR)
        return self._vectorstore

    # ---- 写入 ----
    def add_documents(self, documents: list[Document]) -> list[str]:
        """将采集文档分块后写入向量库，返回写入的 chunk id 列表"""
        vs = self._ensure_vectorstore()
        lc_docs: list[LCDocument] = []
        for d in documents:
            chunks = self._text_splitter.split_text(d.content)
            for i, chunk in enumerate(chunks):
                lc_docs.append(LCDocument(
                    page_content=chunk,
                    metadata={**d.to_metadata_dict(), "chunk_idx": i},
                ))
        if not lc_docs:
            return []
        ids = vs.add_documents(lc_docs)
        logger.info("写入向量库 %d 条分块（来自 %d 篇文档）", len(lc_docs), len(documents))
        return ids

    # ---- 检索 ----
    def retrieve(
        self,
        query: str,
        *,
        competitor: Optional[str] = None,
        category: Optional[str] = None,
        k: int = 5,
    ) -> list[LCDocument]:
        """时序检索：支持按竞品 / 维度 过滤"""
        vs = self._ensure_vectorstore()
        filter_dict: dict = {}
        if competitor:
            filter_dict["competitor"] = competitor
        if category:
            filter_dict["category"] = category
        return vs.similarity_search(
            query,
            k=k,
            filter=filter_dict or None,
        )

    # ---- 完整 LCEL 生成链路 ----
    def analyze(self, question: str, tier: str = "sonnet", **filter_kwargs) -> str:
        """retriever | prompt | llm | parser 完整 RAG 生成"""
        docs = self.retrieve(question, **filter_kwargs)
        context = "\n\n".join(d.page_content for d in docs)
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是竞品情报分析师，基于以下检索素材回答问题，结论必须可溯源。"),
            ("human", "检索素材：\n{context}\n\n问题：{question}"),
        ])
        chain = (
            {"context": lambda _: context, "question": RunnablePassthrough()}
            | prompt
            | get_llm(tier)  # type: ignore[arg-type]
            | StrOutputParser()
        )
        return chain.invoke(question)


# ---- 单例 ----
_instance: Optional[RAGChain] = None


def build_rag_chain() -> RAGChain:
    """全局快捷入口：获取 RAG 流水线单例"""
    global _instance
    if _instance is None:
        _instance = RAGChain()
    return _instance
