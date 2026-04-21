import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from .constants import N_CLUSTERS, TOP_NEWS_PER_CLUSTER, TOP_NEWS_GLOBAL, HIGHLIGHT_TOP_N, WINDOW_DAYS


class ReportingEngine:
    @staticmethod
    def select_highlights(
        df_tech: pd.DataFrame, tech_embeddings: np.ndarray, cluster_centers: np.ndarray
    ) -> pd.DataFrame:
        highlight_rows = []
        for c in range(N_CLUSTERS):
            mask = df_tech["cluster"].values == c
            if not mask.any():
                continue
            cluster_df = df_tech[mask].copy()
            cluster_emb = tech_embeddings[mask]
            center = cluster_centers[c]
            cluster_df["dist_to_center"] = cosine_similarity(
                cluster_emb, center.reshape(1, -1)
            ).flatten()
            highlight_rows.append(
                cluster_df.nlargest(TOP_NEWS_PER_CLUSTER, "dist_to_center")
            )

        df_cluster_picks = pd.concat(highlight_rows).drop_duplicates(subset=["url"])
        df_global = df_tech.nlargest(TOP_NEWS_GLOBAL, "tech_score")

        return (
            pd.concat([df_cluster_picks, df_global])
            .drop_duplicates(subset=["url"])
            .nlargest(HIGHLIGHT_TOP_N, "tech_score")
            .reset_index(drop=True)
        )

    @staticmethod
    def build_report(
        df_tech: pd.DataFrame, kw_df: pd.DataFrame, df_highlights: pd.DataFrame
    ) -> dict:
        now = datetime.now(timezone.utc)
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=WINDOW_DAYS)
        week_str = f"{cutoff.strftime('%d/%m/%Y')} - {now.strftime('%d/%m/%Y')}"

        topic_dist = df_tech["tech_topic"].value_counts()
        dominant_topic = topic_dist.index[0]
        dominant_pct = round(float(topic_dist.iloc[0] / len(df_tech) * 100), 1)
        top3_kw = kw_df["keyword"].tolist()[:3]

        return {
            "week": week_str,
            "generated_at": now.isoformat(),
            "stats": {
                "total_tech_articles": int(len(df_tech)),
                "sources": int(df_tech["source"].nunique()),
                "dominant_topic": dominant_topic,
                "dominant_topic_pct": dominant_pct,
            },
            "executive_summary": {
                "landscape": f"{len(df_tech):,} bài viết công nghệ từ {df_tech['source'].nunique()} nguồn trong tuần {week_str}.",
                "dominant_topic": dominant_topic,
                "top_keywords": top3_kw,
            },
            "trending_keywords": [
                {
                    "rank": i + 1,
                    "keyword": row["keyword"],
                    "score": round(float(row["combined"]), 5),
                }
                for i, row in kw_df.iterrows()
            ],
            "highlighted_news": [
                {
                    "rank": i + 1,
                    "title": row["title"],
                    "source": row["source"],
                    "url": row["url"],
                    "published_at": str(row["published_at"]),
                    "topic": row["tech_topic"],
                    "tech_score": round(float(row["tech_score"]), 4),
                    "summary": row["content"][:300].replace("\n", " "),
                }
                for i, (_, row) in enumerate(df_highlights.iterrows())
            ],
        }
