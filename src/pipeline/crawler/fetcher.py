import logging
import threading

import requests
from bs4 import BeautifulSoup

from .config import HEADERS

log = logging.getLogger(__name__)


def fetch_html(url: str, timeout: int = 8) -> BeautifulSoup:
    res = requests.get(url, headers=HEADERS, timeout=timeout)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")


def fetch_article_detail(
    url: str,
    content_selector: str,
    date_selector: str | None,
    cancel_event: threading.Event | None = None,
) -> dict:
    if cancel_event and cancel_event.is_set():
        return {"content": None, "published_at": None}

    try:
        soup = fetch_html(url)

        paragraphs = soup.select(content_selector)
        content = (
            "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
            or None
        )

        published_at = None
        if date_selector:
            tag = soup.select_one(date_selector)
            if tag:
                published_at = tag.get("content") or tag.get_text(strip=True) or None

        return {"content": content, "published_at": published_at}

    except Exception as e:
        log.warning("Detail fetch error [%s]: %s", url, e)
        return {"content": None, "published_at": None}