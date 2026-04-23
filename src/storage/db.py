import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv(override=True)


def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", 5432),
        dbname=os.getenv("POSTGRES_DB", "newsdb"),
        user=os.getenv("POSTGRES_USER", "admin"),
        password=os.getenv("POSTGRES_PASSWORD", "supersecretpassword123"),
    )


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id           SERIAL PRIMARY KEY,
                    source       VARCHAR(50)  NOT NULL,
                    title        TEXT         NOT NULL,
                    url          TEXT         UNIQUE NOT NULL,
                    image        TEXT,
                    published_at TIMESTAMPTZ,
                    crawled_at   TIMESTAMPTZ  DEFAULT NOW(),
                    content      TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_articles_source    ON articles(source);
                CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at DESC);
                CREATE INDEX IF NOT EXISTS idx_articles_crawled   ON articles(crawled_at DESC);
            """)
        conn.commit()


def save_articles(articles: list[dict]) -> dict:
    if not articles:
        return {"inserted": 0, "skipped": 0}

    rows = [
        (a.get("source"), a.get("title"), a.get("link"), a.get("image"), a.get("published_at"), a.get("content"))
        for a in articles
        if a.get("title") and a.get("link")
    ]

    with get_connection() as conn:
        with conn.cursor() as cur:
            results = psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO articles (source, title, url, image, published_at, content)
                VALUES %s
                ON CONFLICT (url) DO NOTHING
                RETURNING id
                """,
                rows,
                fetch=True,
            )
            inserted = len(results)
            skipped = len(rows) - inserted
        conn.commit()

    return {"inserted": inserted, "skipped": skipped}


def fetch_articles_for_analysis(window_days: int = 7) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, source, title, url, image, published_at, content
                FROM articles
                WHERE published_at >= NOW() - INTERVAL '%s days'
                ORDER BY id
            """, (window_days,))
            return [dict(r) for r in cur.fetchall()]