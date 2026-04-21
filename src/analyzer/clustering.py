import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

from .constants import N_CLUSTERS


class ClusteringEngine:
    @staticmethod
    def cluster_articles(
        df_tech: pd.DataFrame, tech_embeddings: np.ndarray
    ) -> tuple[pd.DataFrame, np.ndarray, KMeans]:
        kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init="auto")
        labels = kmeans.fit_predict(tech_embeddings)
        df_tech = df_tech.copy()
        df_tech["cluster"] = labels
        centers = kmeans.cluster_centers_
        return df_tech, centers, kmeans
