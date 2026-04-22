import logging

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_similarity

from .models import ClusterArticle, ClusterQuality, ClusterReport

log = logging.getLogger(__name__)

TFIDF_MAX_FEATURES = 300
TFIDF_NGRAM = (1, 2)
TOP_CLUSTER_KEYWORDS = 10
TOP_NEWS_PER_CLUSTER = 2


def pick_best_k(embeddings: np.ndarray, chosen_k: int, radius: int) -> tuple[int, list[ClusterQuality]]:
    k_min = max(2, chosen_k - radius)
    k_max = chosen_k + radius
    quality_list: list[ClusterQuality] = []
    best_k, best_sil = chosen_k, -1.0

    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init="auto")
        labels = km.fit_predict(embeddings)
        sil = float(silhouette_score(
            embeddings, labels,
            sample_size=min(2000, len(embeddings)),
            random_state=42,
        ))
        quality_list.append(ClusterQuality(k=k, inertia=float(km.inertia_), silhouette=sil, chosen=False))
        if sil > best_sil:
            best_sil, best_k = sil, k

    for q in quality_list:
        if q.k == best_k:
            q.chosen = True

    log.info("Best K=%d (silhouette=%.4f)", best_k, best_sil)
    return best_k, quality_list


def build_cluster_keywords(df, cluster_labels: np.ndarray, n_clusters: int) -> dict[int, list[tuple[str, float]]]:
    result: dict[int, list[tuple[str, float]]] = {}
    for c in range(n_clusters):
        docs = df.loc[cluster_labels == c, "tokenized"].tolist()
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


def build_clusters(
    df,
    embeddings: np.ndarray,
    cluster_labels: np.ndarray,
    cluster_centers: np.ndarray,
    cluster_topic_name: list[str],
    cluster_keywords: dict[int, list[tuple[str, float]]],
    n_clusters: int,
) -> list[ClusterReport]:
    cluster_stats = []
    for c in range(n_clusters):
        mask = cluster_labels == c
        if not mask.any():
            continue
        avg_tech = float(df[mask]["tech_score"].mean())
        sims = cosine_similarity(embeddings[mask], cluster_centers[c].reshape(1, -1)).flatten()
        cluster_stats.append({
            "cluster_id": c,
            "avg_tech": avg_tech,
            "cohesion": float(sims.mean()),
            "mask": mask,
            "sims": sims,
        })

    avg_techs = np.array([s["avg_tech"] for s in cluster_stats])
    cohesions = np.array([s["cohesion"] for s in cluster_stats])

    def _norm(arr: np.ndarray) -> np.ndarray:
        rng = arr.max() - arr.min()
        return (arr - arr.min()) / rng if rng > 0 else np.zeros_like(arr)

    combined_scores = _norm(avg_techs) + _norm(cohesions)

    reports: list[ClusterReport] = []
    for idx, stat in enumerate(cluster_stats):
        c = stat["cluster_id"]
        mask = stat["mask"]
        cluster_df = df[mask].copy()
        cluster_df["dist_to_center"] = stat["sims"]
        top_articles = cluster_df.nlargest(TOP_NEWS_PER_CLUSTER, "dist_to_center")

        reports.append(ClusterReport(
            cluster_id=c,
            topic=cluster_topic_name[c],
            article_count=int(mask.sum()),
            avg_tech_score=round(stat["avg_tech"], 4),
            cohesion_score=round(stat["cohesion"], 4),
            combined_score=round(float(combined_scores[idx]), 4),
            top_keywords=cluster_keywords[c],
            top_articles=[
                ClusterArticle(
                    rank=i + 1,
                    title=row["title"],
                    source=row["source"],
                    url=row["url"],
                    published_at=str(row["published_at"]),
                    tech_score=round(float(row["tech_score"]), 4),
                    content_snippet=row.get("content_snippet", "")[:300].replace("\n", " "),
                )
                for i, (_, row) in enumerate(top_articles.iterrows())
            ],
        ))

    reports.sort(key=lambda r: r.combined_score, reverse=True)
    return reports