import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize
from sentence_transformers import SentenceTransformer

from src.processor.preprocess import TECH_QUERIES, TOPIC_LABELS
from src.storage.qdrant_store import QdrantStore

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
REPORTS_DIR = Path("/reports")


@dataclass
class KeywordEntry:
    rank: int
    keyword: str
    tfidf_score: float
    semantic_score: float
    combined_score: float


@dataclass
class ClusterArticle:
    rank: int
    title: str
    source: str
    url: str
    published_at: str
    tech_score: float
    content_snippet: str


@dataclass
class ClusterReport:
    cluster_id: int
    topic: str
    article_count: int
    avg_tech_score: float
    cohesion_score: float
    combined_score: float
    top_keywords: list[tuple[str, float]]
    top_articles: list[ClusterArticle]


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
    clusters: list[ClusterReport]
    highlighted_articles: list[HighlightedArticle]


def _pick_best_k(embeddings, chosen_k, radius):
    k_min = max(2, chosen_k - radius)
    k_max = chosen_k + radius
    quality_list = []
    best_k, best_sil = chosen_k, -1.0
    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init="auto")
        labels = km.fit_predict(embeddings)
        sil = float(silhouette_score(embeddings, labels, sample_size=min(2000, len(embeddings)), random_state=42))
        quality_list.append(ClusterQuality(k=k, inertia=float(km.inertia_), silhouette=sil, chosen=False))
        if sil > best_sil:
            best_sil, best_k = sil, k
    for q in quality_list:
        if q.k == best_k:
            q.chosen = True
    log.info("Best K=%d (silhouette=%.4f)", best_k, best_sil)
    return best_k, quality_list


def _cluster_keywords(df, cluster_labels, n_clusters):
    result = {}
    for c in range(n_clusters):
        docs = df.loc[cluster_labels == c, "tokenized"].tolist()
        if not docs:
            result[c] = []
            continue
        tfidf_c = TfidfVectorizer(max_features=TFIDF_MAX_FEATURES, ngram_range=TFIDF_NGRAM,
                                   token_pattern=r"(?u)\b\w\w+\b", min_df=1)
        mat = tfidf_c.fit_transform(docs)
        mean_scores = mat.mean(axis=0).A1
        top_idx = mean_scores.argsort()[::-1][:TOP_CLUSTER_KEYWORDS]
        feat = tfidf_c.get_feature_names_out()
        result[c] = [(feat[i], round(float(mean_scores[i]), 5)) for i in top_idx]
    return result


def _build_all_clusters(df, embeddings, cluster_labels, cluster_centers, cluster_topic_name, ckw, n_clusters):
    cluster_stats = []
    for c in range(n_clusters):
        mask = cluster_labels == c
        if not mask.any():
            continue
        avg_tech = float(df[mask]["tech_score"].mean())
        sims = cosine_similarity(embeddings[mask], cluster_centers[c].reshape(1, -1)).flatten()
        cluster_stats.append({"cluster_id": c, "avg_tech": avg_tech, "cohesion": float(sims.mean()), "mask": mask, "sims": sims})

    avg_techs = np.array([s["avg_tech"] for s in cluster_stats])
    cohesions = np.array([s["cohesion"] for s in cluster_stats])

    def _norm(arr):
        rng = arr.max() - arr.min()
        return (arr - arr.min()) / rng if rng > 0 else np.zeros_like(arr)

    combined_scores = _norm(avg_techs) + _norm(cohesions)
    reports = []
    for idx, stat in enumerate(cluster_stats):
        c = stat["cluster_id"]
        mask = stat["mask"]
        cluster_df = df[mask].copy()
        cluster_df["dist_to_center"] = stat["sims"]
        top_articles = cluster_df.nlargest(TOP_NEWS_PER_CLUSTER, "dist_to_center")
        reports.append(ClusterReport(
            cluster_id=c, topic=cluster_topic_name[c], article_count=int(mask.sum()),
            avg_tech_score=round(stat["avg_tech"], 4), cohesion_score=round(stat["cohesion"], 4),
            combined_score=round(float(combined_scores[idx]), 4), top_keywords=ckw[c],
            top_articles=[
                ClusterArticle(rank=i+1, title=row["title"], source=row["source"], url=row["url"],
                               published_at=str(row["published_at"]),
                               tech_score=round(float(row["tech_score"]), 4),
                               content_snippet=row.get("content_snippet", "")[:300].replace("\n", " "))
                for i, (_, row) in enumerate(top_articles.iterrows())
            ],
        ))
    reports.sort(key=lambda r: r.combined_score, reverse=True)
    return reports


def _report_to_dict(report: AnalysisReport) -> dict:
    return {
        "generated_at": report.generated_at,
        "week_start": report.week_start,
        "week_end": report.week_end,
        "stats": report.stats,
        "executive_summary": report.executive_summary,
        "trending_keywords": [vars(k) for k in report.trending_keywords],
        "topic_distribution": [vars(t) for t in report.topic_distribution],
        "daily_counts": [vars(d) for d in report.daily_counts],
        "clusters": [
            {
                **{k: v for k, v in vars(c).items() if k not in ("top_keywords", "top_articles")},
                "top_keywords": c.top_keywords,
                "top_articles": [vars(a) for a in c.top_articles],
            }
            for c in report.clusters
        ],
        "highlighted_articles": [vars(a) for a in report.highlighted_articles],
    }


def _save_report(report: AnalysisReport) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = REPORTS_DIR / f"report_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(_report_to_dict(report), ensure_ascii=False, indent=2))
    log.info("Report saved to %s", path)
    return path


def load_latest_report() -> dict | None:
    if not REPORTS_DIR.exists():
        return None
    files = sorted(REPORTS_DIR.glob("report_*.json"), reverse=True)
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                content = fh.read()
            if not content.strip():
                log.warning("Skipping empty report file: %s", f)
                continue
            return json.loads(content)
        except json.JSONDecodeError as e:
            log.warning("Skipping corrupt report file %s: %s", f, e)
            continue
    return None


class Analyzer:
    def __init__(self, sbert: SentenceTransformer, qdrant_store: QdrantStore) -> None:
        self.sbert = sbert
        self.qdrant_store = qdrant_store

    def run(self) -> AnalysisReport:
        log.info("Analyzer: loading processed articles from Qdrant")
        payloads, vectors = self.qdrant_store.scroll_all()
        if not payloads:
            raise RuntimeError("No processed articles found in Qdrant. Run /preprocess first.")

        df = pd.DataFrame(payloads)
        embeddings = np.array(vectors, dtype=np.float32)
        df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
        df["tech_score"] = df["tech_score"].astype(float)
        log.info("Loaded %d articles from Qdrant", len(df))

        tfidf = TfidfVectorizer(max_features=TFIDF_MAX_FEATURES, ngram_range=TFIDF_NGRAM,
                                 token_pattern=r"(?u)\b\w\w+\b", min_df=TFIDF_MIN_DF)
        tfidf_matrix = tfidf.fit_transform(df["tokenized"])
        tfidf_scores = dict(zip(tfidf.get_feature_names_out(), tfidf_matrix.mean(axis=0).A1))

        query_embeddings = self.sbert.encode(TECH_QUERIES, normalize_embeddings=True)
        keyword_embeds = self.sbert.encode(list(tfidf_scores.keys()), normalize_embeddings=True, show_progress_bar=False)
        query_embed_mean = normalize(query_embeddings.mean(axis=0, keepdims=True))
        kw_relevance = cosine_similarity(keyword_embeds, query_embed_mean).flatten()

        kw_df = pd.DataFrame({"keyword": list(tfidf_scores.keys()), "tfidf": list(tfidf_scores.values()), "semantic": kw_relevance})
        kw_df["combined"] = kw_df["tfidf"] * kw_df["semantic"]
        kw_df = kw_df.sort_values("combined", ascending=False).reset_index(drop=True)
        top_kw = kw_df.head(TOP_KEYWORDS)

        best_k, _ = _pick_best_k(embeddings, N_CLUSTERS_DEFAULT, CLUSTER_EXPLORE_RADIUS)
        kmeans = KMeans(n_clusters=best_k, random_state=42, n_init="auto")
        cluster_labels = kmeans.fit_predict(embeddings)
        df = df.copy()
        df["cluster"] = cluster_labels

        cluster_centers = kmeans.cluster_centers_
        cluster_topic_idx = cosine_similarity(cluster_centers, query_embeddings).argmax(axis=1)
        cluster_topic_name = [TOPIC_LABELS[i] for i in cluster_topic_idx]
        df["cluster_topic"] = df["cluster"].map({i: cluster_topic_name[i] for i in range(best_k)})

        ckw = _cluster_keywords(df, cluster_labels, best_k)
        all_clusters = _build_all_clusters(df, embeddings, cluster_labels, cluster_centers, cluster_topic_name, ckw, best_k)

        df_highlights = (
            pd.concat([
                pd.concat([
                    df[cluster_labels == c].assign(
                        dist_to_center=cosine_similarity(embeddings[cluster_labels == c], cluster_centers[c].reshape(1, -1)).flatten()
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
                "landscape": f"{len(df):,} bài viết công nghệ từ {df['source'].nunique()} nguồn trong tuần {week_start} - {week_end}.",
                "dominant_topic": topic_counts.index[0],
                "dominant_topic_pct": round(float(topic_counts.iloc[0] / len(df) * 100), 1),
                "top_keywords": top_kw["keyword"].tolist()[:3],
                "highlight_count": len(df_highlights),
            },
            trending_keywords=[
                KeywordEntry(rank=i+1, keyword=row["keyword"],
                             tfidf_score=round(float(row["tfidf"]), 5),
                             semantic_score=round(float(row["semantic"]), 5),
                             combined_score=round(float(row["combined"]), 5))
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
                HighlightedArticle(rank=i+1, title=row["title"], source=row["source"], url=row["url"],
                                   published_at=str(row["published_at"]), topic=row["tech_topic"],
                                   tech_score=round(float(row["tech_score"]), 4),
                                   content_snippet=row.get("content_snippet", "")[:300].replace("\n", " "))
                for i, (_, row) in enumerate(df_highlights.iterrows())
            ],
        )

        _save_report(report)
        return report