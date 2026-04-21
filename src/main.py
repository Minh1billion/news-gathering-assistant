import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from src.storage.db import init_db
from src.crawler.crawl import Crawler
from src.analyzer.analyze import Analyzer
from src.analyzer.constants import WINDOW_DAYS

log = logging.getLogger(__name__)

SBERT_MODEL_NAME = "keepitreal/vietnamese-sbert"

_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    init_db()
    sbert = SentenceTransformer(SBERT_MODEL_NAME)
    _state["analyzer"] = Analyzer(sbert)
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


def _get_analyzer() -> Analyzer:
    analyzer = _state.get("analyzer")
    if analyzer is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    return analyzer


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": "analyzer" in _state}


@app.post("/crawl", response_model=CrawlResult)
def crawl():
    return Crawler().run()


@app.get("/report", response_model=ReportResponse)
def get_report(window_days: int = WINDOW_DAYS):
    try:
        return _get_analyzer().run(window_days)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/pipeline", response_model=ReportResponse)
def pipeline(window_days: int = WINDOW_DAYS):
    Crawler().run()
    try:
        return _get_analyzer().run(window_days)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))