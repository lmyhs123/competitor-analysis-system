# -*- coding: utf-8 -*-
"""
============================================================
 data_loader.py — 多源舆情 DocumentLoader
============================================================
 职责（对应业务模块二「多源舆情自动采集与清洗」）：
   - 网页 / RSS / 论坛 等多源舆情抓取
   - 保留来源、采集时间、原始内容等元数据（可追溯数据链路）
   - 文本分块预处理，保障语义完整性
   - 增量采集：仅返回新增动态，避免重复计算

 使用：
     from modules.data_loader import DataLoader
     docs = DataLoader().collect_incremental(["竞品A"])
"""
from __future__ import annotations

import hashlib
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

try:
    import feedparser  # type: ignore
except ImportError:  # pragma: no cover
    feedparser = None  # type: ignore

logger = logging.getLogger(__name__)


# ============================================================
# 统一文档结构（保留可追溯元数据）
# ============================================================
@dataclass
class Document:
    """标准化舆情文档：原始内容 + 可追溯元数据"""
    content: str
    source: str               # 来源渠道（官网/RSS/论坛/媒体）
    source_url: str
    competitor: str           # 关联竞品
    category: str = "general" # 价格/新品/舆情
    publish_date: Optional[str] = None
    collect_time: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    raw_text: str = ""
    doc_id: str = ""

    def __post_init__(self) -> None:
        if not self.doc_id:
            # 基于内容 + url 生成稳定 ID，用于增量去重
            key = f"{self.source_url}|{self.content[:200]}"
            self.doc_id = hashlib.md5(key.encode("utf-8")).hexdigest()[:16]

    def to_metadata_dict(self) -> dict:
        """向量库存储所需元数据"""
        return {
            "doc_id": self.doc_id,
            "source": self.source,
            "source_url": self.source_url,
            "competitor": self.competitor,
            "category": self.category,
            "publish_date": self.publish_date or "",
            "collect_time": self.collect_time,
        }


# ============================================================
# 抽象基类：统一采集接口
# ============================================================
class BaseLoader(ABC):
    """所有舆情采集器必须实现的统一接口"""

    source_name: str = "base"

    @abstractmethod
    def fetch(self, competitor: str, **kwargs) -> list[Document]:
        """采集指定竞品的舆情文档"""

    def _safe_get(self, url: str, timeout: int = 15) -> Optional[str]:
        """带异常捕获的 HTTP GET"""
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; CompetitorBot/0.1)"}
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            logger.warning("抓取失败 %s: %s", url, e)
            return None


# ============================================================
# 网页采集器：requests + BeautifulSoup
# ============================================================
class WebLoader(BaseLoader):
    source_name = "web"

    def fetch(self, competitor: str, urls: Optional[list[str]] = None, **kwargs) -> list[Document]:
        if not urls:
            logger.info("WebLoader 无目标 URL，跳过")
            return []
        docs: list[Document] = []
        for url in urls:
            html = self._safe_get(url)
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")
            # 移除脚本/样式噪声
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            docs.append(Document(
                content=text,
                source=self.source_name,
                source_url=url,
                competitor=competitor,
                category=kwargs.get("category", "general"),
            ))
            time.sleep(0.5)  # 礼貌限速
        return docs


# ============================================================
# RSS 采集器：feedparser
# ============================================================
class RSSLoader(BaseLoader):
    source_name = "rss"

    def fetch(self, competitor: str, feed_urls: Optional[list[str]] = None, **kwargs) -> list[Document]:
        if feedparser is None:
            logger.error("feedparser 未安装，无法采集 RSS")
            return []
        if not feed_urls:
            return []
        docs: list[Document] = []
        for feed_url in feed_urls:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:20]:  # 每源最多20条
                    docs.append(Document(
                        content=entry.get("summary", entry.get("title", "")),
                        source=self.source_name,
                        source_url=entry.get("link", feed_url),
                        competitor=competitor,
                        publish_date=entry.get("published", ""),
                        raw_text=entry.get("summary", ""),
                    ))
            except Exception as e:
                logger.warning("RSS 解析失败 %s: %s", feed_url, e)
        return docs


# ============================================================
# 统一调度入口
# ============================================================
class DataLoader:
    """多源舆情统一采集 + 增量去重"""

    def __init__(self) -> None:
        self._loaders: list[BaseLoader] = [WebLoader(), RSSLoader()]
        self._seen_ids: set[str] = set()

    def collect_incremental(
        self,
        competitors: Iterable[str],
        targets: Optional[dict[str, dict]] = None,
    ) -> list[Document]:
        """
        增量采集：仅返回新增文档
        targets 形如 {"竞品A": {"web": ["url1"], "rss": ["feed1"]}}
        """
        new_docs: list[Document] = []
        for comp in competitors:
            cfg = (targets or {}).get(comp, {})
            for loader in self._loaders:
                kind = loader.source_name
                kw = cfg.get(kind, {})
                docs = loader.fetch(competitor=comp, **kw) if kw else []
                for d in docs:
                    if d.doc_id in self._seen_ids:
                        continue
                    self._seen_ids.add(d.doc_id)
                    new_docs.append(d)
        logger.info("增量采集完成：新增 %d 条，累计已见 %d 条", len(new_docs), len(self._seen_ids))
        return new_docs

    def reset_seen(self) -> None:
        """清空去重缓存（用于全量重采）"""
        self._seen_ids.clear()
