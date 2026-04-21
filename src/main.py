import logging
from src.storage.db import init_db
from src.crawler.crawl import crawl_all, enrich_with_content
from src.storage.db import save_articles

log = logging.getLogger(__name__)


def main():
    log.info("Initializing database...")
    init_db()
    log.info("Database ready.")

    log.info("Starting crawl...")
    articles = crawl_all()

    log.info("Enriching content...")
    enriched = enrich_with_content(articles)

    stats = save_articles(enriched)
    log.info(f"Done: {stats['inserted']} inserted / {stats['skipped']} skipped")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    main()