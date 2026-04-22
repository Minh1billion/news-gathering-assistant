import json
from .sources import SOURCES


def save_json(data: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_html(data: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("<!DOCTYPE html>\n<html><head><meta charset='utf-8'>")
        f.write("""<style>
            body { font-family: sans-serif; max-width: 900px; margin: auto; padding: 20px; }
            h3 { margin-bottom: 4px; }
            h3 a { color: #1a1a1a; text-decoration: none; }
            h3 a:hover { text-decoration: underline; }
            small { color: #888; }
            .content p { color: #444; line-height: 1.6; margin: 6px 0; }
            .no-content { color: #bbb; font-style: italic; }
            .no-date { color: #f0a500; font-style: italic; }
            .article { margin-bottom: 32px; }
            .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-left: 6px; }
            .badge-html { background: #e3f0ff; color: #1a6ebd; }
            .badge-rss { background: #e8f5e9; color: #2e7d32; }
        </style>""")
        f.write("</head><body>\n")
        f.write(f"<h1>Articles ({len(data)})</h1>\n")

        for art in data:
            source_type = SOURCES.get(art["source"], {}).get("type", "")
            badge = f"<span class='badge badge-{source_type}'>{source_type.upper()}</span>"
            date_str = art.get("published_at") or "<span class='no-date'>No date</span>"

            f.write("<div class='article'>\n")
            f.write(f"<h3><a href='{art['link']}'>{art['title']}</a>{badge}</h3>\n")
            f.write(f"<small>{date_str} - {art['source']}</small><br>\n")

            if art.get("image"):
                f.write(f"<img src='{art['image']}' width='200' style='margin-top:8px'><br>\n")

            if art.get("content"):
                f.write("<div class='content'>\n")
                for para in art["content"].split("\n"):
                    if para.strip():
                        f.write(f"<p>{para.strip()}</p>\n")
                f.write("</div>\n")
            else:
                f.write("<p class='no-content'>No content</p>\n")

            f.write("</div><hr>\n")

        f.write("</body></html>")