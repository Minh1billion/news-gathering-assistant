from src.storage.db import fetch_articles_for_analysis
from src.processor.preprocess import Preprocess
from .clustering import ClusteringEngine
from .reporting import ReportingEngine
from .constants import WINDOW_DAYS


class Analyzer:
    def __init__(self, sbert_model):
        self.preprocessor = Preprocess(sbert_model)

    def run(self, window_days: int = WINDOW_DAYS) -> dict:
        rows = fetch_articles_for_analysis(window_days)
        if not rows:
            raise ValueError("No articles found in the given window")

        df_tech, tech_embeddings, query_embeddings = self.preprocessor.run(rows)
        if df_tech.empty:
            raise ValueError("No tech articles passed the relevance threshold")

        kw_df = self.preprocessor.get_trending_keywords(df_tech, query_embeddings)
        df_tech, centers, _ = ClusteringEngine.cluster_articles(df_tech, tech_embeddings)
        df_highlights = ReportingEngine.select_highlights(df_tech, tech_embeddings, centers)
        return ReportingEngine.build_report(df_tech, kw_df, df_highlights)