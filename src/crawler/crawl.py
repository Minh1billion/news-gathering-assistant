import time
import random
from .config import SOURCES
from .fetcher import fetch_article_detail
from .parsers import PARSERS
from ..storage.db import save_articles


class Crawler:
    def __init__(self, sources: dict = None, delay: tuple[float, float] = (1.0, 2.0)):
        self.sources = sources or SOURCES
        self.delay = delay

    def _enrich(self, articles: list[dict], source_name: str) -> list[dict]:
        config = self.sources.get(source_name, {})
        content_selector = config.get("content_selector")
        date_selector = config.get("date_selector")
        source_type = config.get("type")
        total = len(articles)

        for i, article in enumerate(articles):
            print(f"  [{i+1}/{total}] {article['title'][:70]}...")
            if content_selector and article.get("link"):
                detail = fetch_article_detail(article["link"], content_selector, date_selector)
                article["content"] = detail["content"]
                if source_type == "html":
                    article["published_at"] = detail["published_at"]
                elif source_type == "rss" and not article.get("published_at"):
                    article["published_at"] = detail["published_at"]

        return articles

    async def run(self) -> dict:
        total_inserted = 0
        total_skipped = 0

        for source_name, config in self.sources.items():
            mode = config["type"]
            display_url = config.get("rss_url") or config.get("url", "")
            print(f"\n[{mode.upper()}] {source_name}: {display_url}")

            try:
                articles = PARSERS[mode](config, source_name)
                print(f"  -> {len(articles)} articles found")
            except Exception as e:
                print(f"  -> Crawl error: {e}")
                time.sleep(random.uniform(*self.delay))
                continue

            enriched = self._enrich(articles, source_name)
            stats = save_articles(enriched)
            total_inserted += stats["inserted"]
            total_skipped += stats["skipped"]
            print(f"  -> Saved: {stats['inserted']} inserted / {stats['skipped']} skipped")

            time.sleep(random.uniform(*self.delay))

        stats = {"inserted": total_inserted, "skipped": total_skipped}
        print(f"\n=== Done: {total_inserted} inserted / {total_skipped} skipped ===")
        return stats