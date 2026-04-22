import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
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
    load_latest_report,
)

log = logging.getLogger(__name__)

SBERT_MODEL_NAME = "keepitreal/vietnamese-sbert"
QDRANT_HOST = "qdrant"
QDRANT_PORT = 6333
REPORTS_DIR = Path("/reports")

_state: dict[str, Any] = {}
_ready: bool = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ready
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    sbert = SentenceTransformer(SBERT_MODEL_NAME)
    qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    qdrant_store = QdrantStore(qdrant)
    _state["sbert"] = sbert
    _state["qdrant"] = qdrant
    _state["qdrant_store"] = qdrant_store
    _state["analyzer"] = Analyzer(sbert=sbert, qdrant_store=qdrant_store)
    _state["preprocessor"] = Preprocessor(sbert=sbert, qdrant_store=qdrant_store)
    _ready = True
    log.info("App ready: SBERT + Qdrant initialized")
    yield
    _state.clear()
    _ready = False


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


class ReportMeta(BaseModel):
    filename: str
    generated_at: str
    week_start: str
    week_end: str
    total_articles: int


def _report_to_response(report: AnalysisReport) -> ReportResponse:
    return ReportResponse(
        generated_at=report.generated_at,
        week_start=report.week_start,
        week_end=report.week_end,
        stats=report.stats,
        executive_summary=report.executive_summary,
        trending_keywords=[KeywordResponse(rank=k.rank, keyword=k.keyword, tfidf_score=k.tfidf_score,
                                            semantic_score=k.semantic_score, combined_score=k.combined_score)
                           for k in report.trending_keywords],
        topic_distribution=[TopicDistributionResponse(topic=t.topic, count=t.count, percentage=t.percentage)
                            for t in report.topic_distribution],
        daily_counts=[DailyCountResponse(date=d.date, count=d.count) for d in report.daily_counts],
        clusters=[
            ClusterResponse(
                cluster_id=c.cluster_id, topic=c.topic, article_count=c.article_count,
                avg_tech_score=c.avg_tech_score, cohesion_score=c.cohesion_score, combined_score=c.combined_score,
                top_keywords=[ClusterKeyword(keyword=kw, score=sc) for kw, sc in c.top_keywords],
                top_articles=[ClusterArticleResponse(rank=a.rank, title=a.title, source=a.source,
                                                      url=a.url, published_at=a.published_at,
                                                      tech_score=a.tech_score, content_snippet=a.content_snippet)
                              for a in c.top_articles],
            )
            for c in report.clusters
        ],
        highlighted_articles=[HighlightResponse(rank=a.rank, title=a.title, source=a.source,
                                                  url=a.url, published_at=a.published_at,
                                                  topic=a.topic, tech_score=a.tech_score,
                                                  content_snippet=a.content_snippet)
                               for a in report.highlighted_articles],
    )


def _dict_to_response(data: dict) -> ReportResponse:
    return ReportResponse(
        generated_at=data["generated_at"],
        week_start=data["week_start"],
        week_end=data["week_end"],
        stats=data["stats"],
        executive_summary=data["executive_summary"],
        trending_keywords=[KeywordResponse(**k) for k in data["trending_keywords"]],
        topic_distribution=[TopicDistributionResponse(**t) for t in data["topic_distribution"]],
        daily_counts=[DailyCountResponse(**d) for d in data["daily_counts"]],
        clusters=[
            ClusterResponse(
                cluster_id=c["cluster_id"], topic=c["topic"], article_count=c["article_count"],
                avg_tech_score=c["avg_tech_score"], cohesion_score=c["cohesion_score"],
                combined_score=c["combined_score"],
                top_keywords=[ClusterKeyword(keyword=kw, score=sc) for kw, sc in c["top_keywords"]],
                top_articles=[ClusterArticleResponse(**a) for a in c["top_articles"]],
            )
            for c in data["clusters"]
        ],
        highlighted_articles=[HighlightResponse(**a) for a in data["highlighted_articles"]],
    )


@app.get("/health")
def health():
    return {"status": "ok" if _ready else "starting", "ready": _ready,
            "sbert_loaded": "sbert" in _state, "qdrant_connected": "qdrant" in _state}


@app.get("/reports", response_model=list[ReportMeta])
def list_reports():
    files = sorted(REPORTS_DIR.glob("report_*.json"), reverse=True)
    result = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            result.append(ReportMeta(
                filename=f.name, generated_at=data.get("generated_at", ""),
                week_start=data.get("week_start", ""), week_end=data.get("week_end", ""),
                total_articles=data.get("stats", {}).get("total_tech_articles", 0),
            ))
        except Exception:
            continue
    return result


@app.get("/reports/{filename}")
def get_report_file(filename: str):
    path = REPORTS_DIR / filename
    if not path.exists() or not path.name.startswith("report_"):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(path, media_type="application/json")


@app.get("/report", response_model=ReportResponse)
async def report():
    cached = await asyncio.to_thread(load_latest_report)
    if cached:
        return _dict_to_response(cached)
    raise HTTPException(status_code=404, detail="no_report")


@app.post("/analyze", response_model=ReportResponse)
async def analyze():
    try:
        analyzer: Analyzer = _state["analyzer"]
        result: AnalysisReport = await asyncio.to_thread(analyzer.run)
        return _report_to_response(result)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.exception("Analysis failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/crawl", response_model=CrawlResult)
async def crawl():
    try:
        crawler = Crawler()
        result = await crawler.run()
        return CrawlResult(crawled=result["inserted"], saved=result["inserted"],
                           sources=list(crawler.sources.keys()))
    except Exception as e:
        log.exception("Crawl failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/preprocess", response_model=PreprocessResult)
async def preprocess():
    try:
        preprocessor: Preprocessor = _state["preprocessor"]
        stats: PreprocessStats = await asyncio.to_thread(preprocessor.run)
        return PreprocessResult(raw_total=stats.raw_total, past_window=stats.past_window,
                                after_filter=stats.after_filter, after_token_filter=stats.after_token_filter,
                                tech_articles=stats.tech_articles, upserted_qdrant=stats.upserted_qdrant)
    except Exception as e:
        log.exception("Preprocess failed")
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