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

                CREATE INDEX IF NOT EXISTS idx_articles_source
                    ON articles(source);
                CREATE INDEX IF NOT EXISTS idx_articles_published
                    ON articles(published_at DESC);
                CREATE INDEX IF NOT EXISTS idx_articles_crawled
                    ON articles(crawled_at DESC);
            """)
        conn.commit()
    print("DB initialized.")


def save_articles(articles: list[dict]) -> dict:
    inserted = 0
    skipped = 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            for art in articles:
                try:
                    cur.execute("""
                        INSERT INTO articles
                            (source, title, url, image, published_at, content)
                        VALUES
                            (%(source)s, %(title)s, %(link)s, %(image)s,
                             %(published_at)s, %(content)s)
                        ON CONFLICT (url) DO UPDATE SET
                            content      = EXCLUDED.content,
                            published_at = COALESCE(articles.published_at, EXCLUDED.published_at),
                            image        = COALESCE(articles.image, EXCLUDED.image)
                        RETURNING (xmax = 0) AS is_inserted
                    """, art)

                    row = cur.fetchone()
                    if row and row[0]:
                        inserted += 1
                    else:
                        skipped += 1

                except Exception as e:
                    print(f"   -> DB error [{art.get('source')}] {art.get('link')}: {e}")
                    conn.rollback()
                    continue

        conn.commit()

    return {"inserted": inserted, "skipped": skipped}


def query_weekly_report() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    source,
                    DATE(crawled_at AT TIME ZONE 'Asia/Ho_Chi_Minh') AS day,
                    COUNT(*) AS article_count
                FROM articles
                WHERE crawled_at >= NOW() - INTERVAL '7 days'
                GROUP BY source, day
                ORDER BY day DESC, source
            """)
            return cur.fetchall()