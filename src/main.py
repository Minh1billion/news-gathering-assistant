import asyncio
import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from src.api.routes import router
from src.pipeline.analyzer.config import REPORTS_DIR
from src.pipeline.analyzer.runner import AnalyzeRunner
from src.pipeline.processor.runner import ProcessRunner
from src.storage.db import init_db
from src.storage.vector_db import QdrantStore

SBERT_MODEL_NAME = "keepitreal/vietnamese-sbert"
QDRANT_HOST = "qdrant"
QDRANT_PORT = 6333


def _setup_logging() -> None:
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    root = logging.getLogger()
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(fmt)
        root.addHandler(handler)
    root.setLevel(logging.INFO)
    for noisy in ("httpx", "httpcore", "urllib3", "multipart"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _setup_logging()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    init_db()

    sbert = SentenceTransformer(SBERT_MODEL_NAME)
    qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    qdrant_store = QdrantStore(qdrant_client)

    s = app.state
    s.ready = False
    s.sbert = sbert
    s.qdrant = qdrant_client
    s.qdrant_store = qdrant_store
    s.process_runner = ProcessRunner(sbert=sbert, qdrant_store=qdrant_store)
    s.analyze_runner = AnalyzeRunner(sbert=sbert, qdrant_store=qdrant_store)

    s.pipeline_lock = asyncio.Lock()
    s.pipeline_cancel = threading.Event()
    s.pipeline_running = False

    s.crawl_lock = asyncio.Lock()
    s.crawl_cancel = threading.Event()
    s.crawl_running = False

    s.preprocess_lock = asyncio.Lock()
    s.preprocess_cancel = threading.Event()
    s.preprocess_running = False

    s.analyze_lock = asyncio.Lock()
    s.analyze_cancel = threading.Event()
    s.analyze_running = False

    s.ready = True
    logging.getLogger(__name__).info("App ready: SBERT + Qdrant initialized")
    yield
    s.ready = False


def create_app() -> FastAPI:
    app = FastAPI(title="News Gathering Assistant", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()