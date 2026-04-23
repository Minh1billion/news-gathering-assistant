import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from src.models.report import AnalysisReport
from src.pipeline.crawler.runner import CrawlRunner
from src.pipeline.analyzer.runner import load_latest_report
from src.pipeline.analyzer.config import REPORTS_DIR
from .schemas import (
    CrawlResult,
    ProcessResult,
    ReportMeta,
    ReportResponse,
    StepStatus,
)
from .serializers import dict_to_response, report_to_response

log = logging.getLogger(__name__)
router = APIRouter()


def _get_state(request: Request) -> dict:
    return request.app.state.pipeline


@router.get("/health")
def health(request: Request):
    s = request.app.state
    return {
        "status": "ok" if s.ready else "starting",
        "ready": s.ready,
        "sbert_loaded": hasattr(s, "sbert"),
        "qdrant_connected": hasattr(s, "qdrant"),
    }


@router.get("/pipeline/status", response_model=StepStatus)
def pipeline_status(request: Request):
    s = request.app.state
    return StepStatus(running=s.pipeline_running, cancelled=s.pipeline_cancel.is_set())


@router.post("/pipeline/cancel", response_model=StepStatus)
def pipeline_cancel(request: Request):
    s = request.app.state
    if not s.pipeline_running:
        raise HTTPException(status_code=400, detail="No pipeline is running")
    s.pipeline_cancel.set()
    return StepStatus(running=s.pipeline_running, cancelled=True)


@router.get("/crawl/status", response_model=StepStatus)
def crawl_status(request: Request):
    s = request.app.state
    return StepStatus(running=s.crawl_running, cancelled=s.crawl_cancel.is_set())


@router.post("/crawl/cancel", response_model=StepStatus)
def crawl_cancel(request: Request):
    s = request.app.state
    if not s.crawl_running:
        raise HTTPException(status_code=400, detail="No crawl is running")
    s.crawl_cancel.set()
    return StepStatus(running=s.crawl_running, cancelled=True)


@router.get("/preprocess/status", response_model=StepStatus)
def preprocess_status(request: Request):
    s = request.app.state
    return StepStatus(running=s.preprocess_running, cancelled=s.preprocess_cancel.is_set())


@router.post("/preprocess/cancel", response_model=StepStatus)
def preprocess_cancel(request: Request):
    s = request.app.state
    if not s.preprocess_running:
        raise HTTPException(status_code=400, detail="No preprocess is running")
    s.preprocess_cancel.set()
    return StepStatus(running=s.preprocess_running, cancelled=True)


@router.get("/analyze/status", response_model=StepStatus)
def analyze_status(request: Request):
    s = request.app.state
    return StepStatus(running=s.analyze_running, cancelled=s.analyze_cancel.is_set())


@router.post("/analyze/cancel", response_model=StepStatus)
def analyze_cancel(request: Request):
    s = request.app.state
    if not s.analyze_running:
        raise HTTPException(status_code=400, detail="No analyze is running")
    s.analyze_cancel.set()
    return StepStatus(running=s.analyze_running, cancelled=True)


@router.get("/reports", response_model=list[ReportMeta])
def list_reports():
    files = sorted(REPORTS_DIR.glob("report_*.json"), reverse=True)
    result = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            result.append(ReportMeta(
                filename=f.name,
                generated_at=data.get("generated_at", ""),
                week_start=data.get("week_start", ""),
                week_end=data.get("week_end", ""),
                total_articles=data.get("stats", {}).get("total_tech_articles", 0),
            ))
        except Exception:
            continue
    return result


@router.get("/reports/{filename}")
def get_report_file(filename: str):
    path = REPORTS_DIR / filename
    if not path.exists() or not path.name.startswith("report_"):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(path, media_type="application/json")


@router.get("/report", response_model=ReportResponse)
async def get_latest_report():
    cached = await asyncio.to_thread(load_latest_report)
    if cached:
        return dict_to_response(cached)
    raise HTTPException(status_code=404, detail="no_report")


@router.post("/crawl", response_model=CrawlResult)
async def crawl(request: Request):
    s = request.app.state
    if s.crawl_lock.locked():
        raise HTTPException(status_code=409, detail="Crawl is already running")
    async with s.crawl_lock:
        s.crawl_running = True
        s.crawl_cancel.clear()
        try:
            runner = CrawlRunner()
            result = await asyncio.to_thread(runner.run, s.crawl_cancel)
            return CrawlResult(
                inserted=result.inserted,
                skipped=result.skipped,
                status=result.status,
                sources=result.sources,
            )
        except InterruptedError:
            raise HTTPException(status_code=499, detail="Crawl cancelled")
        except Exception as e:
            log.exception("Crawl failed")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            s.crawl_running = False


@router.post("/preprocess", response_model=ProcessResult)
async def preprocess(request: Request):
    s = request.app.state
    if s.preprocess_lock.locked():
        raise HTTPException(status_code=409, detail="Preprocess is already running")
    async with s.preprocess_lock:
        s.preprocess_running = True
        s.preprocess_cancel.clear()
        try:
            result = await asyncio.to_thread(s.process_runner.run, s.preprocess_cancel)
            return ProcessResult(
                raw_total=result.raw_total,
                past_window=result.past_window,
                after_filter=result.after_filter,
                after_token_filter=result.after_token_filter,
                tech_articles=result.tech_articles,
                upserted_qdrant=result.upserted_qdrant,
            )
        except InterruptedError:
            raise HTTPException(status_code=499, detail="Preprocess cancelled")
        except Exception as e:
            log.exception("Preprocess failed")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            s.preprocess_running = False


@router.post("/analyze", response_model=ReportResponse)
async def analyze(request: Request):
    s = request.app.state
    if s.analyze_lock.locked():
        raise HTTPException(status_code=409, detail="Analyze is already running")
    async with s.analyze_lock:
        s.analyze_running = True
        s.analyze_cancel.clear()
        try:
            result: AnalysisReport = await asyncio.to_thread(s.analyze_runner.run, s.analyze_cancel)
            return report_to_response(result)
        except InterruptedError:
            raise HTTPException(status_code=499, detail="Analyze cancelled")
        except RuntimeError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            log.exception("Analyze failed")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            s.analyze_running = False


@router.post("/pipeline", response_model=ReportResponse)
async def pipeline(request: Request, skip_crawl: bool = False):
    s = request.app.state
    if s.pipeline_lock.locked():
        raise HTTPException(status_code=409, detail="Pipeline is already running")
    async with s.pipeline_lock:
        s.pipeline_running = True
        s.pipeline_cancel.clear()
        try:
            if not skip_crawl:
                runner = CrawlRunner()
                await asyncio.to_thread(runner.run, s.pipeline_cancel)
                if s.pipeline_cancel.is_set():
                    raise HTTPException(status_code=499, detail="Pipeline cancelled during crawl")
                log.info("Pipeline: crawl done")

            await asyncio.to_thread(s.process_runner.run, s.pipeline_cancel)
            if s.pipeline_cancel.is_set():
                raise HTTPException(status_code=499, detail="Pipeline cancelled during preprocess")
            log.info("Pipeline: preprocess done")

            result: AnalysisReport = await asyncio.to_thread(s.analyze_runner.run, s.pipeline_cancel)
            if s.pipeline_cancel.is_set():
                raise HTTPException(status_code=499, detail="Pipeline cancelled during analyze")
            log.info("Pipeline: analyze done")
            return report_to_response(result)

        except HTTPException:
            raise
        except InterruptedError:
            raise HTTPException(status_code=499, detail="Pipeline cancelled")
        except RuntimeError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            log.exception("Pipeline failed")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            s.pipeline_running = False