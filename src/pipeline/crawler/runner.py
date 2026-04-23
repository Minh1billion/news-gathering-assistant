import logging
import random
import threading
import time
from dataclasses import dataclass

from src.pipeline.base import PipelineStep
from src.storage.db import save_articles
from .config import SOURCES
from .fetcher import fetch_article_detail
from .parsers import PARSERS

log = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    inserted: int
    skipped: int
    status: str
    sources: list[str]


def _interruptible_sleep(seconds: float, cancel_event: threading.Event | None) -> None:
    if cancel_event is None:
        time.sleep(seconds)
    else:
        cancel_event.wait(timeout=seconds)


class CrawlRunner(PipelineStep):
    def __init__(
        self,
        sources: dict | None = None,
        delay: tuple[float, float] = (1.0, 2.0),
    ) -> None:
        self.sources = sources or SOURCES
        self.delay = delay

    def _enrich(
        self,
        articles: list[dict],
        source_name: str,
        cancel_event: threading.Event | None,
    ) -> list[dict]:
        config = self.sources.get(source_name, {})
        content_selector = config.get("content_selector")
        date_selector = config.get("date_selector")
        source_type = config.get("type")

        for i, article in enumerate(articles):
            if cancel_event and cancel_event.is_set():
                log.info("[%s] Enrich cancelled at %d/%d", source_name, i, len(articles))
                break

            log.info("  [%d/%d] %s...", i + 1, len(articles), article["title"][:70])

            if content_selector and article.get("link"):
                detail = fetch_article_detail(
                    article["link"],
                    content_selector,
                    date_selector,
                    cancel_event=cancel_event,
                )
                article["content"] = detail["content"]
                if source_type == "html":
                    article["published_at"] = detail["published_at"]
                elif source_type == "rss" and not article.get("published_at"):
                    article["published_at"] = detail["published_at"]

        return articles

    def run(self, cancel_event: threading.Event | None = None) -> CrawlResult:
        total_inserted = 0
        total_skipped = 0

        for source_name, config in self.sources.items():
            if cancel_event and cancel_event.is_set():
                log.info("Crawler cancelled before source: %s", source_name)
                break

            mode = config["type"]
            display_url = config.get("rss_url") or config.get("url", "")
            log.info("[%s] %s: %s", mode.upper(), source_name, display_url)

            try:
                articles = PARSERS[mode](config, source_name, cancel_event=cancel_event)
                log.info("  -> %d articles found", len(articles))
            except Exception as e:
                log.error("  -> Crawl error [%s]: %s", source_name, e)
                _interruptible_sleep(random.uniform(*self.delay), cancel_event)
                continue

            enriched = self._enrich(articles, source_name, cancel_event)
            stats = save_articles(enriched)
            total_inserted += stats["inserted"]
            total_skipped += stats["skipped"]
            log.info(
                "  -> [%s] %d inserted / %d skipped",
                source_name, stats["inserted"], stats["skipped"],
            )

            if not (cancel_event and cancel_event.is_set()):
                _interruptible_sleep(random.uniform(*self.delay), cancel_event)

        status = "cancelled" if (cancel_event and cancel_event.is_set()) else "done"
        log.info("=== %s: %d inserted / %d skipped ===", status.capitalize(), total_inserted, total_skipped)

        return CrawlResult(
            inserted=total_inserted,
            skipped=total_skipped,
            status=status,
            sources=list(self.sources.keys()),
        )