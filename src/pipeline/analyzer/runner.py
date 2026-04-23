import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

from src.models.report import (
    AnalysisReport,
    DailyCount,
    HighlightedArticle,
    KeywordEntry,
    TopicDistribution,
)
from src.pipeline.base import PipelineStep
from src.pipeline.processor.config import TECH_QUERIES, TOPIC_LABELS
from src.storage.vector_db import QdrantStore
from .clustering import build_cluster_keywords, build_clusters, pick_best_k
from .config import (
    CLUSTER_EXPLORE_RADIUS,
    HIGHLIGHT_TOP_N,
    N_CLUSTERS_DEFAULT,
    REPORTS_DIR,
    TFIDF_MAX_FEATURES,
    TFIDF_MIN_DF,
    TFIDF_NGRAM,
    TOP_KEYWORDS,
    TOP_NEWS_GLOBAL,
    TOP_NEWS_PER_CLUSTER,
)

log = logging.getLogger(__name__)


def save_report(report: AnalysisReport) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = REPORTS_DIR / f"report_{ts}.json"
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    log.info("Report saved to %s", path)
    return path


def load_latest_report() -> dict | None:
    if not REPORTS_DIR.exists():
        return None
    for f in sorted(REPORTS_DIR.glob("report_*.json"), reverse=True):
        try:
            content = f.read_text(encoding="utf-8")
            if not content.strip():
                log.warning("Skipping empty report file: %s", f)
                continue
            return json.loads(content)
        except json.JSONDecodeError as e:
            log.warning("Skipping corrupt report file %s: %s", f, e)
    return None


class AnalyzeRunner(PipelineStep):
    def __init__(self, sbert: SentenceTransformer, qdrant_store: QdrantStore) -> None:
        self.sbert = sbert
        self.qdrant_store = qdrant_store

    def run(self, cancel_event: threading.Event | None = None) -> AnalysisReport:
        def cancelled() -> bool:
            return cancel_event is not None and cancel_event.is_set()

        log.info("AnalyzeRunner: loading articles from Qdrant")
        payloads, vectors = self.qdrant_store.scroll_all()
        if not payloads:
            raise RuntimeError("No processed articles found in Qdrant. Run /preprocess first.")

        if cancelled():
            raise InterruptedError("Cancelled after load")

        df = pd.DataFrame(payloads)
        embeddings = np.array(vectors, dtype=np.float32)
        df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
        df["tech_score"] = df["tech_score"].astype(float)
        log.info("Loaded %d articles from Qdrant", len(df))

        tfidf = TfidfVectorizer(
            max_features=TFIDF_MAX_FEATURES,
            ngram_range=TFIDF_NGRAM,
            token_pattern=r"(?u)\b\w\w+\b",
            min_df=TFIDF_MIN_DF,
        )
        tfidf_matrix = tfidf.fit_transform(df["tokenized"])
        tfidf_scores = dict(zip(tfidf.get_feature_names_out(), tfidf_matrix.mean(axis=0).A1))

        if cancelled():
            raise InterruptedError("Cancelled after TF-IDF")

        query_embeddings = self.sbert.encode(TECH_QUERIES, normalize_embeddings=True)
        keyword_embeds = self.sbert.encode(
            list(tfidf_scores.keys()), normalize_embeddings=True, show_progress_bar=False
        )
        query_embed_mean = normalize(query_embeddings.mean(axis=0, keepdims=True))
        kw_relevance = cosine_similarity(keyword_embeds, query_embed_mean).flatten()

        kw_df = pd.DataFrame({
            "keyword": list(tfidf_scores.keys()),
            "tfidf": list(tfidf_scores.values()),
            "semantic": kw_relevance,
        })
        kw_df["combined"] = kw_df["tfidf"] * kw_df["semantic"]
        kw_df = kw_df.sort_values("combined", ascending=False).reset_index(drop=True)
        top_kw = kw_df.head(TOP_KEYWORDS)

        if cancelled():
            raise InterruptedError("Cancelled after keyword scoring")

        best_k, _ = pick_best_k(embeddings, N_CLUSTERS_DEFAULT, CLUSTER_EXPLORE_RADIUS)
        kmeans = KMeans(n_clusters=best_k, random_state=42, n_init="auto")
        cluster_labels = kmeans.fit_predict(embeddings)
        df = df.copy()
        df["cluster"] = cluster_labels

        if cancelled():
            raise InterruptedError("Cancelled after clustering")

        cluster_centers = kmeans.cluster_centers_
        cluster_topic_idx = cosine_similarity(cluster_centers, query_embeddings).argmax(axis=1)
        cluster_topic_name = [TOPIC_LABELS[i] for i in cluster_topic_idx]
        df["cluster_topic"] = df["cluster"].map(dict(enumerate(cluster_topic_name)))

        ckw = build_cluster_keywords(df, cluster_labels, best_k)
        all_clusters = build_clusters(
            df, embeddings, cluster_labels, cluster_centers, cluster_topic_name, ckw, best_k
        )

        if cancelled():
            raise InterruptedError("Cancelled after building clusters")

        df_highlights = (
            pd.concat([
                pd.concat([
                    df[cluster_labels == c].assign(
                        dist_to_center=cosine_similarity(
                            embeddings[cluster_labels == c],
                            cluster_centers[c].reshape(1, -1),
                        ).flatten()
                    ).nlargest(TOP_NEWS_PER_CLUSTER, "dist_to_center")
                    for c in range(best_k)
                ]).drop_duplicates(subset=["url"]),
                df.nlargest(TOP_NEWS_GLOBAL, "tech_score"),
            ])
            .drop_duplicates(subset=["url"])
            .nlargest(HIGHLIGHT_TOP_N, "tech_score")
            .reset_index(drop=True)
        )

        topic_counts = df["tech_topic"].value_counts()
        now = pd.Timestamp.now(tz="UTC")
        week_start = (now - pd.Timedelta(days=7)).strftime("%d/%m/%Y")
        week_end = now.strftime("%d/%m/%Y")

        report = AnalysisReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            week_start=week_start,
            week_end=week_end,
            stats={
                "total_tech_articles": int(len(df)),
                "sources": int(df["source"].nunique()),
                "dominant_topic": topic_counts.index[0],
                "dominant_topic_pct": round(float(topic_counts.iloc[0] / len(df) * 100), 1),
                "n_clusters": best_k,
                "date_range": f"{week_start} - {week_end}",
            },
            executive_summary={
                "landscape": (
                    f"{len(df):,} bài viết công nghệ từ {df['source'].nunique()} nguồn"
                    f" trong tuần {week_start} - {week_end}."
                ),
                "dominant_topic": topic_counts.index[0],
                "dominant_topic_pct": round(float(topic_counts.iloc[0] / len(df) * 100), 1),
                "top_keywords": top_kw["keyword"].tolist()[:3],
                "highlight_count": len(df_highlights),
            },
            trending_keywords=[
                KeywordEntry(
                    rank=i + 1,
                    keyword=row["keyword"],
                    tfidf_score=round(float(row["tfidf"]), 5),
                    semantic_score=round(float(row["semantic"]), 5),
                    combined_score=round(float(row["combined"]), 5),
                )
                for i, row in top_kw.iterrows()
            ],
            topic_distribution=[
                TopicDistribution(topic=t, count=int(c), percentage=round(float(c / len(df) * 100), 1))
                for t, c in topic_counts.items()
            ],
            daily_counts=[
                DailyCount(date=str(d), count=int(c))
                for d, c in df.groupby(df["published_at"].dt.date).size().items()
            ],
            clusters=all_clusters,
            highlighted_articles=[
                HighlightedArticle(
                    rank=i + 1,
                    title=row["title"],
                    source=row["source"],
                    url=row["url"],
                    published_at=str(row["published_at"]),
                    topic=row["tech_topic"],
                    tech_score=round(float(row["tech_score"]), 4),
                    content_snippet=row.get("content_snippet", "")[:300].replace("\n", " "),
                )
                for i, (_, row) in enumerate(df_highlights.iterrows())
            ],
        )

        save_report(report)
        return report