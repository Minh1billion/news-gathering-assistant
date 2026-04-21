import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

from src.processor.preprocess import (
    QDRANT_COLLECTION,
    TECH_QUERIES,
    TOPIC_LABELS,
    SBERT_CONTENT_CHARS,
    SBERT_BATCH_SIZE,
)

log = logging.getLogger(__name__)

TFIDF_MAX_FEATURES = 300
TFIDF_MIN_DF = 2
TFIDF_NGRAM = (1, 2)
TOP_KEYWORDS = 30
TOP_CLUSTER_KEYWORDS = 10
TOP_NEWS_PER_CLUSTER = 2
TOP_NEWS_GLOBAL = 15
HIGHLIGHT_TOP_N = 10
N_CLUSTERS_DEFAULT = 6
CLUSTER_EXPLORE_RADIUS = 3


@dataclass
class KeywordEntry:
    rank: int
    keyword: str
    tfidf_score: float
    semantic_score: float
    combined_score: float


@dataclass
class ClusterInfo:
    cluster_id: int
    topic: str
    article_count: int
    top_keywords: list[tuple[str, float]]


@dataclass
class HighlightedArticle:
    rank: int
    title: str
    source: str
    url: str
    published_at: str
    topic: str
    tech_score: float
    content_snippet: str


@dataclass
class TopicDistribution:
    topic: str
    count: int
    percentage: float


@dataclass
class DailyCount:
    date: str
    count: int


@dataclass
class ClusterQuality:
    k: int
    inertia: float
    silhouette: float
    chosen: bool


@dataclass
class AnalysisReport:
    generated_at: str
    week_start: str
    week_end: str

    stats: dict

    executive_summary: dict

    trending_keywords: list[KeywordEntry]

    topic_distribution: list[TopicDistribution]
    daily_counts: list[DailyCount]

    clusters: list[ClusterInfo]
    cluster_quality: list[ClusterQuality]

    highlighted_articles: list[HighlightedArticle]


def _scroll_all_qdrant(client: QdrantClient) -> tuple[list[dict], list[list[float]]]:
    records, payloads, vectors = [], [], []
    offset = None
    while True:
        result, next_offset = client.scroll(
            collection_name=QDRANT_COLLECTION,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )
        if not result:
            break
        for point in result:
            payloads.append(point.payload)
            vectors.append(point.vector)
        offset = next_offset
        if offset is None:
            break
    return payloads, vectors


def _pick_best_k(
    embeddings: np.ndarray,
    chosen_k: int,
    radius: int,
) -> tuple[int, list[ClusterQuality]]:
    k_min = max(2, chosen_k - radius)
    k_max = chosen_k + radius
    quality_list = []

    best_k = chosen_k
    best_sil = -1.0

    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init="auto")
        labels = km.fit_predict(embeddings)
        inertia = float(km.inertia_)
        sil = float(silhouette_score(
            embeddings,
            labels,
            sample_size=min(2000, len(embeddings)),
            random_state=42,
        ))
        quality_list.append(ClusterQuality(k=k, inertia=inertia, silhouette=sil, chosen=False))
        if sil > best_sil:
            best_sil = sil
            best_k = k

    for q in quality_list:
        if q.k == best_k:
            q.chosen = True

    log.info("Best K=%d (silhouette=%.4f)", best_k, best_sil)
    return best_k, quality_list


def _cluster_keywords(
    df: pd.DataFrame,
    cluster_labels: np.ndarray,
    n_clusters: int,
) -> dict[int, list[tuple[str, float]]]:
    result = {}
    for c in range(n_clusters):
        mask = cluster_labels == c
        docs = df.loc[mask, "tokenized"].tolist()
        if not docs:
            result[c] = []
            continue
        tfidf_c = TfidfVectorizer(
            max_features=TFIDF_MAX_FEATURES,
            ngram_range=TFIDF_NGRAM,
            token_pattern=r"(?u)\b\w\w+\b",
            min_df=1,
        )
        mat = tfidf_c.fit_transform(docs)
        mean_scores = mat.mean(axis=0).A1
        top_idx = mean_scores.argsort()[::-1][:TOP_CLUSTER_KEYWORDS]
        feat = tfidf_c.get_feature_names_out()
        result[c] = [(feat[i], round(float(mean_scores[i]), 5)) for i in top_idx]
    return result


class Analyzer:
    def __init__(self, sbert: SentenceTransformer, qdrant: QdrantClient) -> None:
        self.sbert = sbert
        self.qdrant = qdrant

    def run(self) -> AnalysisReport:
        log.info("Analyzer: loading processed articles from Qdrant")
        payloads, vectors = _scroll_all_qdrant(self.qdrant)

        if not payloads:
            raise RuntimeError("No processed articles found in Qdrant. Run /preprocess first.")

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
        tfidf_scores = dict(zip(
            tfidf.get_feature_names_out(),
            tfidf_matrix.mean(axis=0).A1,
        ))

        query_embeddings = self.sbert.encode(TECH_QUERIES, normalize_embeddings=True)
        keyword_embeds = self.sbert.encode(
            list(tfidf_scores.keys()),
            normalize_embeddings=True,
            show_progress_bar=False,
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

        log.info("Picking best K for clustering")
        best_k, quality_list = _pick_best_k(embeddings, N_CLUSTERS_DEFAULT, CLUSTER_EXPLORE_RADIUS)

        kmeans = KMeans(n_clusters=best_k, random_state=42, n_init="auto")
        cluster_labels = kmeans.fit_predict(embeddings)
        df = df.copy()
        df["cluster"] = cluster_labels

        cluster_centers = kmeans.cluster_centers_
        cluster_sim = cosine_similarity(cluster_centers, query_embeddings)
        cluster_topic_idx = cluster_sim.argmax(axis=1)
        cluster_topic_name = [TOPIC_LABELS[i] for i in cluster_topic_idx]
        cluster_topic_map = {i: cluster_topic_name[i] for i in range(best_k)}
        df["cluster_topic"] = df["cluster"].map(cluster_topic_map)

        ckw = _cluster_keywords(df, cluster_labels, best_k)

        clusters_info = []
        for c in range(best_k):
            clusters_info.append(ClusterInfo(
                cluster_id=c,
                topic=cluster_topic_name[c],
                article_count=int((df["cluster"] == c).sum()),
                top_keywords=ckw[c],
            ))

        highlight_rows = []
        for c in range(best_k):
            mask_c = df["cluster"].values == c
            cluster_df = df[mask_c].copy()
            cluster_emb = embeddings[mask_c]
            center = cluster_centers[c]
            cluster_df["dist_to_center"] = cosine_similarity(
                cluster_emb, center.reshape(1, -1)
            ).flatten()
            top = cluster_df.nlargest(TOP_NEWS_PER_CLUSTER, "dist_to_center")
            highlight_rows.append(top)

        df_highlights_cluster = pd.concat(highlight_rows).drop_duplicates(subset=["url"])
        df_highlights_global = df.nlargest(TOP_NEWS_GLOBAL, "tech_score")
        df_highlights = (
            pd.concat([df_highlights_cluster, df_highlights_global])
            .drop_duplicates(subset=["url"])
            .nlargest(HIGHLIGHT_TOP_N, "tech_score")
            .reset_index(drop=True)
        )

        topic_counts = df["tech_topic"].value_counts()
        topic_dist = [
            TopicDistribution(
                topic=topic,
                count=int(count),
                percentage=round(float(count / len(df) * 100), 1),
            )
            for topic, count in topic_counts.items()
        ]

        daily = df.groupby(df["published_at"].dt.date).size()
        daily_counts = [
            DailyCount(date=str(date), count=int(cnt))
            for date, cnt in daily.items()
        ]

        now = pd.Timestamp.now(tz="UTC")
        week_start = (now - pd.Timedelta(days=7)).strftime("%d/%m/%Y")
        week_end = now.strftime("%d/%m/%Y")

        dominant_topic = topic_counts.index[0]
        dominant_pct = float(topic_counts.iloc[0] / len(df) * 100)
        top3_kw = top_kw["keyword"].tolist()[:3]

        trending_keywords = [
            KeywordEntry(
                rank=i + 1,
                keyword=row["keyword"],
                tfidf_score=round(float(row["tfidf"]), 5),
                semantic_score=round(float(row["semantic"]), 5),
                combined_score=round(float(row["combined"]), 5),
            )
            for i, row in top_kw.iterrows()
        ]

        highlighted_articles = [
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
        ]

        report = AnalysisReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            week_start=week_start,
            week_end=week_end,
            stats={
                "total_tech_articles": int(len(df)),
                "sources": int(df["source"].nunique()),
                "dominant_topic": dominant_topic,
                "dominant_topic_pct": round(dominant_pct, 1),
                "n_clusters": best_k,
                "date_range": f"{week_start} - {week_end}",
            },
            executive_summary={
                "landscape": (
                    f"{len(df):,} bài viết công nghệ từ {df['source'].nunique()} nguồn "
                    f"trong tuần {week_start} - {week_end}."
                ),
                "dominant_topic": dominant_topic,
                "dominant_topic_pct": round(dominant_pct, 1),
                "top_keywords": top3_kw,
                "highlight_count": len(df_highlights),
            },
            trending_keywords=trending_keywords,
            topic_distribution=topic_dist,
            daily_counts=daily_counts,
            clusters=clusters_info,
            cluster_quality=quality_list,
            highlighted_articles=highlighted_articles,
        )

        log.info(
            "Analysis complete: %d articles, %d clusters, %d highlighted",
            len(df), best_k, len(highlighted_articles),
        )
        return report