import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from src.storage.db import init_db, fetch_articles_for_analysis
from src.crawler.crawl import Crawler
from src.processor.process import (
    build_dataframe,
    filter_articles,
    tokenize_articles,
    score_articles,
    compute_trending_keywords,
)
from src.analyzer.analyze import cluster_articles, select_highlights, build_report, WINDOW_DAYS

log = logging.getLogger(__name__)

SBERT_MODEL_NAME = "keepitreal/vietnamese-sbert"

_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    log.info("Initializing database...")
    init_db()

    log.info(f"Loading SBERT model: {SBERT_MODEL_NAME}")
    _state["sbert"] = SentenceTransformer(SBERT_MODEL_NAME)
    log.info("Model loaded.")

    yield

    _state.clear()


app = FastAPI(title="News Gathering Assistant", lifespan=lifespan)


class CrawlResult(BaseModel):
    inserted: int
    skipped: int


class ReportResponse(BaseModel):
    week: str
    generated_at: str
    stats: dict
    executive_summary: dict
    trending_keywords: list[dict]
    highlighted_news: list[dict]


def _run_analysis(window_days: int = WINDOW_DAYS) -> dict:
    sbert = _state.get("sbert")
    if sbert is None:
        raise RuntimeError("SBERT model not loaded")

    rows = fetch_articles_for_analysis(window_days)
    if not rows:
        raise ValueError("No articles found in the given window")

    df_raw = build_dataframe(rows)
    df_filtered = filter_articles(df_raw)
    df_tokenized = tokenize_articles(df_filtered)
    df_tech, tech_embeddings, query_embeddings = score_articles(df_tokenized, sbert)

    if df_tech.empty:
        raise ValueError("No tech articles passed the relevance threshold")

    kw_df = compute_trending_keywords(df_tech, sbert, query_embeddings)
    df_tech, cluster_centers, _ = cluster_articles(df_tech, tech_embeddings)
    df_highlights = select_highlights(df_tech, tech_embeddings, cluster_centers)

    return build_report(df_tech, kw_df, df_highlights)


@app.post("/crawl", response_model=CrawlResult)
def crawl():
    crawler = Crawler()
    stats = crawler.run()
    return stats


@app.get("/report", response_model=ReportResponse)
def get_report(window_days: int = WINDOW_DAYS):
    try:
        report = _run_analysis(window_days)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return report


@app.post("/crawl-and-report", response_model=ReportResponse)
def crawl_and_report(window_days: int = WINDOW_DAYS):
    crawler = Crawler()
    crawler.run()
    try:
        report = _run_analysis(window_days)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return report


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": "sbert" in _state}