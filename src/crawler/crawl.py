import logging
import random
import threading
from .sources import SOURCES
from .fetcher import fetch_article_detail
from .parsers import PARSERS
from ..storage.db import save_articles

log = logging.getLogger(__name__)


def _interruptible_sleep(seconds: float, cancel_event: threading.Event | None) -> None:
    if cancel_event is None:
        import time; time.sleep(seconds)
    else:
        cancel_event.wait(timeout=seconds)


class Crawler:
    def __init__(self, sources: dict = None, delay: tuple[float, float] = (1.0, 2.0),
                 cancel_event: threading.Event = None):
        self.sources = sources or SOURCES
        self.delay = delay
        self._cancel = cancel_event or threading.Event()

    def _is_cancelled(self) -> bool:
        return self._cancel.is_set()

    def _enrich(self, articles: list[dict], source_name: str) -> list[dict]:
        config = self.sources.get(source_name, {})
        content_selector = config.get("content_selector")
        date_selector = config.get("date_selector")
        source_type = config.get("type")
        total = len(articles)

        for i, article in enumerate(articles):
            if self._is_cancelled():
                log.info("  [%s] Enrich cancelled at %d/%d", source_name, i, total)
                break

            log.info("  [%d/%d] %s...", i + 1, total, article["title"][:70])

            if content_selector and article.get("link"):
                detail = fetch_article_detail(
                    article["link"], content_selector, date_selector,
                    cancel_event=self._cancel,
                )
                article["content"] = detail["content"]
                if source_type == "html":
                    article["published_at"] = detail["published_at"]
                elif source_type == "rss" and not article.get("published_at"):
                    article["published_at"] = detail["published_at"]

        return articles

    def run(self) -> dict:
        total_inserted = 0
        total_skipped = 0

        for source_name, config in self.sources.items():
            if self._is_cancelled():
                log.info("Crawler cancelled before source: %s", source_name)
                break

            mode = config["type"]
            display_url = config.get("rss_url") or config.get("url", "")
            log.info("\n[%s] %s: %s", mode.upper(), source_name, display_url)

            try:
                articles = PARSERS[mode](config, source_name, cancel_event=self._cancel)
                log.info("  -> %d articles found", len(articles))
            except Exception as e:
                log.error("  -> Crawl error: %s", e)
                _interruptible_sleep(random.uniform(*self.delay), self._cancel)
                continue

            enriched = self._enrich(articles, source_name)
            stats = save_articles(enriched)
            total_inserted += stats["inserted"]
            total_skipped += stats["skipped"]
            log.info(
                "  -> [%s] Saved: %d inserted / %d skipped",
                source_name, stats["inserted"], stats["skipped"],
            )

            if not self._is_cancelled():
                _interruptible_sleep(random.uniform(*self.delay), self._cancel)

        status = "cancelled" if self._is_cancelled() else "done"
        log.info("\n=== %s: %d inserted / %d skipped ===", status.capitalize(), total_inserted, total_skipped)
        return {"inserted": total_inserted, "skipped": total_skipped, "status": status}