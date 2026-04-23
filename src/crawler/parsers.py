import logging
import time
import random
import threading
import feedparser
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .fetcher import fetch_html

log = logging.getLogger(__name__)


def _interruptible_sleep(seconds: float, cancel_event: threading.Event | None) -> bool:
    if cancel_event is None:
        time.sleep(seconds)
        return False
    return cancel_event.wait(timeout=seconds)


def parse_html_source(
    config: dict,
    source_name: str,
    cancel_event: threading.Event | None = None,
) -> list[dict]:
    urls = [config["url"]]

    pagination = config.get("pagination")
    if pagination:
        for page in range(pagination["start"], pagination["start"] + pagination["max_pages"]):
            urls.append(pagination["pattern"].format(page=page))

    results = []
    seen_links = set()

    for url in urls:
        if cancel_event and cancel_event.is_set():
            log.info("   [%s] HTML parse cancelled", source_name)
            break

        log.info("   Fetching page: %s", url)
        try:
            soup = fetch_html(url)
            articles = soup.select(config["article_selector"])

            for art in articles:
                a_tag = art.select_one(config["a_selector"])
                if not a_tag:
                    continue

                title = a_tag.get("title") or a_tag.get_text(strip=True)
                link = urljoin(config["base_url"], a_tag.get("href", ""))

                if not title or not link or link in seen_links:
                    continue

                seen_links.add(link)

                img = art.select_one("img")
                img_url = img.get("data-src") or img.get("src") if img else None

                results.append({
                    "title": title,
                    "link": link,
                    "image": img_url,
                    "published_at": None,
                    "content": None,
                    "source": source_name,
                })

            _interruptible_sleep(random.uniform(1, 2), cancel_event)

        except Exception as e:
            log.error("   -> Page error %s: %s", url, e)

    return results


def _extract_rss_description(entry: dict) -> str | None:
    raw = entry.get("summary") or entry.get("description")
    if not raw:
        return None
    text = BeautifulSoup(raw, "html.parser").get_text(strip=True)
    return text or None


def parse_rss_source(
    config: dict,
    source_name: str,
    cancel_event: threading.Event | None = None,
) -> list[dict]:
    feed = feedparser.parse(config["rss_url"])
    if feed.bozo:
        log.warning("   -> RSS feed may be malformed: %s", feed.bozo_exception)

    results = []
    use_description_as_content = not config.get("content_selector")

    for entry in feed.entries:
        results.append({
            "title": entry.get("title"),
            "link": entry.get("link"),
            "image": None,
            "published_at": entry.get("published"),
            "content": _extract_rss_description(entry) if use_description_as_content else None,
            "source": source_name,
        })

    return results


PARSERS = {
    "html": parse_html_source,
    "rss": parse_rss_source,
}