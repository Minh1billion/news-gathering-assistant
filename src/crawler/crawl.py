import time
import random
from .config import SOURCES
from .fetcher import fetch_article_detail
from .parsers import PARSERS
from .exporter import save_json, save_html
from ..storage.db import init_db, save_articles


def crawl_all() -> list[dict]:
    all_results = []

    for source_name, config in SOURCES.items():
        mode = config["type"]
        display_url = config["rss_url"] if mode == "rss" else config["url"]
        print(f"\nFetching [{mode.upper()}]: {display_url}")
        try:
            parser_fn = PARSERS[mode]
            data = parser_fn(config, source_name)
            print(f" -> Found {len(data)} articles")
            all_results.extend(data)
        except Exception as e:
            print(f" -> Error: {e}")

        time.sleep(random.uniform(1, 2))

    return all_results


def enrich_with_content(articles: list[dict]) -> list[dict]:
    total = len(articles)

    for i, article in enumerate(articles):
        config = SOURCES.get(article["source"], {})
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

        time.sleep(random.uniform(0.5, 1.5))

    return articles


if __name__ == "__main__":
    init_db()

    print("=== Step 1: Crawl article list ===")
    articles = crawl_all()
    save_json(articles, "articles.json")
    print(f"\nSaved {len(articles)} articles to articles.json")

    print("\n=== Step 2: Enrich with content and date ===")
    enriched = enrich_with_content(articles)

    save_json(enriched, "article-content.json")
    save_html(enriched, "article-content.html")

    stats = save_articles(enriched)
    print(f"\n=== DB saved: {stats['inserted']} inserted / {stats['skipped']} skipped ===")

    success_content = sum(1 for a in enriched if a.get("content"))
    success_date = sum(1 for a in enriched if a.get("published_at"))
    no_date = [a for a in enriched if not a.get("published_at")]

    print(f"\nDone!")
    print(f" -> Content : {success_content}/{len(enriched)}")
    print(f" -> Date    : {success_date}/{len(enriched)}")

    if no_date:
        print(f"\nArticles with no date ({len(no_date)}):")
        for a in no_date[:5]:
            print(f"  [{a['source']}] {a['title'][:60]}")
        if len(no_date) > 5:
            print(f"  ... and {len(no_date) - 5} more")

    print("\nSaved to article-content.json, article-content.html, and PostgreSQL")