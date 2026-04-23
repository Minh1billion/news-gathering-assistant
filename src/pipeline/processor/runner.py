import logging
import re
import threading
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from underthesea import word_tokenize

from src.pipeline.base import PipelineStep
from src.storage.db import get_connection
from src.storage.vector_db import QdrantStore
from .config import (
    IMPORTANT_ENGLISH_KEYWORDS,
    MIN_CONTENT_LEN,
    MIN_TOKEN_LEN,
    MOJIBAKE_PATTERNS,
    SBERT_BATCH_SIZE,
    SBERT_CONTENT_CHARS,
    SEMANTIC_THRESHOLD,
    STOPWORDS,
    TECH_QUERIES,
    TOPIC_LABELS,
    WINDOW_DAYS,
)

log = logging.getLogger(__name__)


@dataclass
class ProcessResult:
    raw_total: int
    past_window: int
    after_filter: int
    after_token_filter: int
    tech_articles: int
    upserted_qdrant: int


def _fix_text(x: str) -> str:
    if not isinstance(x, str):
        return x
    try:
        return x.encode("latin1").decode("utf-8")
    except Exception:
        return x


def _detect_mojibake(df: pd.DataFrame) -> pd.DataFrame:
    df["has_mojibake"] = False
    for col in ["title", "content"]:
        for name, pattern in MOJIBAKE_PATTERNS:
            flag_col = f"{col}_{name}"
            df[flag_col] = df[col].fillna("").str.contains(pattern, regex=True)
            df["has_mojibake"] |= df[flag_col]
    return df


def _clean_text(text: str) -> str:
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"\S+@\S+\.\S+", " ", text)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\b\d+\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _remove_stopwords(tokenized_text: str) -> str:
    filtered = []
    for token in tokenized_text.split():
        is_english = token.isascii() and token.isalpha()
        is_important = token.lower() in IMPORTANT_ENGLISH_KEYWORDS
        if is_important:
            filtered.append(token)
        elif token not in STOPWORDS and len(token) > 2 and not token.isnumeric() and not is_english:
            filtered.append(token)
    return " ".join(filtered)


def _save_processed_postgres(df: pd.DataFrame) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS processed_articles (
                article_id    INTEGER PRIMARY KEY REFERENCES articles(id),
                tokenized     TEXT    NOT NULL,
                tech_score    FLOAT   NOT NULL,
                tech_topic    TEXT    NOT NULL,
                processed_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO processed_articles (article_id, tokenized, tech_score, tech_topic)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (article_id) DO UPDATE SET
                    tokenized    = EXCLUDED.tokenized,
                    tech_score   = EXCLUDED.tech_score,
                    tech_topic   = EXCLUDED.tech_topic,
                    processed_at = NOW()
            """, (int(row["id"]), row["tokenized"], float(row["tech_score"]), row["tech_topic"]))
        conn.commit()
    finally:
        conn.close()


class ProcessRunner(PipelineStep):
    def __init__(self, sbert: SentenceTransformer, qdrant_store: QdrantStore) -> None:
        self.sbert = sbert
        self.qdrant_store = qdrant_store

    def run(self, cancel_event: threading.Event | None = None) -> ProcessResult:
        def cancelled() -> bool:
            return cancel_event is not None and cancel_event.is_set()

        log.info("ProcessRunner: loading articles from Postgres")
        conn = get_connection()
        df_raw = pd.read_sql("SELECT * FROM articles ORDER BY id", conn)
        conn.close()

        if cancelled():
            raise InterruptedError("Cancelled after load")

        for col in ["title", "content", "url"]:
            if col in df_raw.columns:
                df_raw[col] = df_raw[col].apply(_fix_text)

        df_raw = _detect_mojibake(df_raw)
        df_raw["published_at"] = pd.to_datetime(df_raw["published_at"], utc=True, errors="coerce")
        df_raw["content_len"] = df_raw["content"].fillna("").str.len()
        df_raw["content"] = df_raw["content"].fillna("")
        df_raw["title"] = df_raw["title"].fillna("")
        df_raw["url"] = df_raw["url"].fillna("")

        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=WINDOW_DAYS)
        df_week = df_raw[df_raw["published_at"] >= cutoff].copy()

        df_clean = (
            df_week
            .drop_duplicates(subset=["url"])
            .drop_duplicates(subset=["title"])
            .pipe(lambda d: d[~d["has_mojibake"]])
            .pipe(lambda d: d[d["content_len"] >= MIN_CONTENT_LEN])
            .reset_index(drop=True)
        )
        log.info(
            "Raw: %d | Past %d days: %d | After filter: %d",
            len(df_raw), WINDOW_DAYS, len(df_week), len(df_clean),
        )

        if cancelled():
            raise InterruptedError("Cancelled after filter")

        df_clean["text_raw"] = (df_clean["title"] + " " + df_clean["content"]).str.lower()
        df_clean["text_clean"] = df_clean["text_raw"].apply(_clean_text)
        df_clean["tokenized_raw"] = df_clean["text_clean"].apply(
            lambda x: word_tokenize(x, format="text")
        )
        df_clean["tokenized"] = df_clean["tokenized_raw"].apply(_remove_stopwords)
        df_clean["token_count_after"] = df_clean["tokenized"].str.split().str.len()

        df_filtered = df_clean[df_clean["token_count_after"] >= MIN_TOKEN_LEN].reset_index(drop=True)
        log.info("After token filter: %d articles", len(df_filtered))

        if cancelled():
            raise InterruptedError("Cancelled after tokenize")

        texts_for_embed = (
            df_filtered["title"] + ". " + df_filtered["content"].str[:SBERT_CONTENT_CHARS]
        ).tolist()

        log.info("Encoding %d articles with SBERT", len(df_filtered))
        article_embeddings = self.sbert.encode(
            texts_for_embed,
            batch_size=SBERT_BATCH_SIZE,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

        if cancelled():
            raise InterruptedError("Cancelled after encode")

        query_embeddings = self.sbert.encode(TECH_QUERIES, normalize_embeddings=True)
        sim_matrix = cosine_similarity(article_embeddings, query_embeddings)
        df_filtered = df_filtered.copy()
        df_filtered["tech_score"] = sim_matrix.max(axis=1)
        df_filtered["tech_topic_idx"] = sim_matrix.argmax(axis=1)
        df_filtered["tech_topic"] = [TOPIC_LABELS[i] for i in df_filtered["tech_topic_idx"]]

        tech_mask = df_filtered["tech_score"] >= SEMANTIC_THRESHOLD
        df_tech = df_filtered[tech_mask].reset_index(drop=True)
        tech_embeddings = article_embeddings[tech_mask.values]
        log.info(
            "Tech articles (threshold=%.2f): %d / %d",
            SEMANTIC_THRESHOLD, len(df_tech), len(df_filtered),
        )

        if cancelled():
            raise InterruptedError("Cancelled after scoring")

        _save_processed_postgres(df_tech)
        self.qdrant_store.ensure_collection(tech_embeddings.shape[1])
        upserted = self.qdrant_store.upsert_articles(df_tech, tech_embeddings)
        log.info("Upserted %d vectors to Qdrant", upserted)

        return ProcessResult(
            raw_total=len(df_raw),
            past_window=len(df_week),
            after_filter=len(df_clean),
            after_token_filter=len(df_filtered),
            tech_articles=len(df_tech),
            upserted_qdrant=upserted,
        )