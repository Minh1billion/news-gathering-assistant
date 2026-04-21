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

    def crawl_all(self) -> list[dict]:
        results = []
        for source_name, config in self.sources.items():
            mode = config["type"]
            display_url = config.get("rss_url") or config.get("url", "")
            print(f"\nFetching [{mode.upper()}]: {display_url}")
            try:
                parser_fn = PARSERS[mode]
                data = parser_fn(config, source_name)
                print(f" -> Found {len(data)} articles")
                results.extend(data)
            except Exception as e:
                print(f" -> Error: {e}")
            time.sleep(random.uniform(*self.delay))
        return results

    def enrich_with_content(self, articles: list[dict]) -> list[dict]:
        total = len(articles)
        for i, article in enumerate(articles):
            config = self.sources.get(article["source"], {})
            content_selector = config.get("content_selector")
            date_selector = config.get("date_selector")
            source_type = config.get("type")
            print(f"[{i+1}/{total}] {article['title'][:70]}...")
            if content_selector and article.get("link"):
                detail = fetch_article_detail(article["link"], content_selector, date_selector)
                article["content"] = detail["content"]
                if source_type == "html":
                    article["published_at"] = detail["published_at"]
                elif source_type == "rss" and not article.get("published_at"):
                    article["published_at"] = detail["published_at"]
        return articles

    def run(self) -> dict:
        print("=== Step 1: Crawl article list ===")
        articles = self.crawl_all()
        print(f"\nFound {len(articles)} articles")

        print("\n=== Step 2: Enrich with content and date ===")
        enriched = self.enrich_with_content(articles)

        stats = save_articles(enriched)
        print(f"\n=== DB saved: {stats['inserted']} inserted / {stats['skipped']} skipped ===")
        return stats