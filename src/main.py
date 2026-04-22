import logging
from contextlib import asynccontextmanager
from typing import Any

import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

from src.storage.db import init_db
from src.storage.qdrant_store import QdrantStore
from src.crawler.crawl import Crawler
from src.processor.preprocess import Preprocessor, PreprocessStats
from src.analyzer.analyze import (
    Analyzer,
    AnalysisReport,
    KeywordEntry,
    ClusterReport,
    ClusterArticle,
    HighlightedArticle,
    TopicDistribution,
    DailyCount,
)

log = logging.getLogger(__name__)

SBERT_MODEL_NAME = "keepitreal/vietnamese-sbert"
QDRANT_HOST = "qdrant"
QDRANT_PORT = 6333

_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    init_db()
    sbert = SentenceTransformer(SBERT_MODEL_NAME)
    qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    qdrant_store = QdrantStore(qdrant)

    _state["sbert"] = sbert
    _state["qdrant"] = qdrant
    _state["qdrant_store"] = qdrant_store
    _state["analyzer"] = Analyzer(sbert=sbert, qdrant_store=qdrant_store)
    _state["preprocessor"] = Preprocessor(sbert=sbert, qdrant_store=qdrant_store)
    log.info("App ready: SBERT + Qdrant initialized")
    yield
    _state.clear()


app = FastAPI(title="News Gathering Assistant", lifespan=lifespan)


class CrawlResult(BaseModel):
    crawled: int
    saved: int
    sources: list[str]


class PreprocessResult(BaseModel):
    raw_total: int
    past_window: int
    after_filter: int
    after_token_filter: int
    tech_articles: int
    upserted_qdrant: int


class KeywordResponse(BaseModel):
    rank: int
    keyword: str
    tfidf_score: float
    semantic_score: float
    combined_score: float


class ClusterKeyword(BaseModel):
    keyword: str
    score: float


class ClusterArticleResponse(BaseModel):
    rank: int
    title: str
    source: str
    url: str
    published_at: str
    tech_score: float
    content_snippet: str


class ClusterResponse(BaseModel):
    cluster_id: int
    topic: str
    article_count: int
    avg_tech_score: float
    cohesion_score: float
    combined_score: float
    top_keywords: list[ClusterKeyword]
    top_articles: list[ClusterArticleResponse]


class HighlightResponse(BaseModel):
    rank: int
    title: str
    source: str
    url: str
    published_at: str
    topic: str
    tech_score: float
    content_snippet: str


class TopicDistributionResponse(BaseModel):
    topic: str
    count: int
    percentage: float


class DailyCountResponse(BaseModel):
    date: str
    count: int


class ReportResponse(BaseModel):
    generated_at: str
    week_start: str
    week_end: str
    stats: dict
    executive_summary: dict
    trending_keywords: list[KeywordResponse]
    topic_distribution: list[TopicDistributionResponse]
    daily_counts: list[DailyCountResponse]
    clusters: list[ClusterResponse]
    highlighted_articles: list[HighlightResponse]


def _report_to_response(report: AnalysisReport) -> ReportResponse:
    return ReportResponse(
        generated_at=report.generated_at,
        week_start=report.week_start,
        week_end=report.week_end,
        stats=report.stats,
        executive_summary=report.executive_summary,
        trending_keywords=[
            KeywordResponse(
                rank=k.rank,
                keyword=k.keyword,
                tfidf_score=k.tfidf_score,
                semantic_score=k.semantic_score,
                combined_score=k.combined_score,
            )
            for k in report.trending_keywords
        ],
        topic_distribution=[
            TopicDistributionResponse(topic=t.topic, count=t.count, percentage=t.percentage)
            for t in report.topic_distribution
        ],
        daily_counts=[
            DailyCountResponse(date=d.date, count=d.count)
            for d in report.daily_counts
        ],
        clusters=[
            ClusterResponse(
                cluster_id=c.cluster_id,
                topic=c.topic,
                article_count=c.article_count,
                avg_tech_score=c.avg_tech_score,
                cohesion_score=c.cohesion_score,
                combined_score=c.combined_score,
                top_keywords=[
                    ClusterKeyword(keyword=kw, score=sc)
                    for kw, sc in c.top_keywords
                ],
                top_articles=[
                    ClusterArticleResponse(
                        rank=a.rank,
                        title=a.title,
                        source=a.source,
                        url=a.url,
                        published_at=a.published_at,
                        tech_score=a.tech_score,
                        content_snippet=a.content_snippet,
                    )
                    for a in c.top_articles
                ],
            )
            for c in report.clusters
        ],
        highlighted_articles=[
            HighlightResponse(
                rank=a.rank,
                title=a.title,
                source=a.source,
                url=a.url,
                published_at=a.published_at,
                topic=a.topic,
                tech_score=a.tech_score,
                content_snippet=a.content_snippet,
            )
            for a in report.highlighted_articles
        ],
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "sbert_loaded": "sbert" in _state,
        "qdrant_connected": "qdrant" in _state,
    }


@app.post("/crawl", response_model=CrawlResult)
async def crawl():
    try:
        crawler = Crawler()
        result = await crawler.run()
        return CrawlResult(
            crawled=result["inserted"],
            saved=result["inserted"],
            sources=list(crawler.sources.keys()),
        )
    except Exception as e:
        log.exception("Crawl failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/preprocess", response_model=PreprocessResult)
async def preprocess():
    try:
        preprocessor: Preprocessor = _state["preprocessor"]
        stats: PreprocessStats = await asyncio.to_thread(preprocessor.run)
        return PreprocessResult(
            raw_total=stats.raw_total,
            past_window=stats.past_window,
            after_filter=stats.after_filter,
            after_token_filter=stats.after_token_filter,
            tech_articles=stats.tech_articles,
            upserted_qdrant=stats.upserted_qdrant,
        )
    except Exception as e:
        log.exception("Preprocess failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/report", response_model=ReportResponse)
async def report():
    try:
        analyzer: Analyzer = _state["analyzer"]
        result: AnalysisReport = await asyncio.to_thread(analyzer.run)
        return _report_to_response(result)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.exception("Report generation failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pipeline", response_model=ReportResponse)
async def pipeline(skip_crawl: bool = False):
    try:
        if not skip_crawl:
            crawler = Crawler()
            await crawler.run()
            log.info("Pipeline: crawl done")

        preprocessor: Preprocessor = _state["preprocessor"]
        await asyncio.to_thread(preprocessor.run)
        log.info("Pipeline: preprocess done")

        analyzer: Analyzer = _state["analyzer"]
        result: AnalysisReport = await asyncio.to_thread(analyzer.run)
        log.info("Pipeline: analysis done")

        return _report_to_response(result)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.exception("Pipeline failed")
        raise HTTPException(status_code=500, detail=str(e))