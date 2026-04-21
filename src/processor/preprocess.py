import numpy as np
import pandas as pd

from .article_processor import ArticleProcessor


class Preprocess:
    def __init__(self, sbert_model):
        self.sbert = sbert_model

    def run(self, raw_rows: list[dict]) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
        df = ArticleProcessor.build_dataframe(raw_rows)
        df = ArticleProcessor.filter_articles(df)
        df = ArticleProcessor.tokenize_articles(df)
        return ArticleProcessor.score_articles(df, self.sbert)

    def get_trending_keywords(
        self, df_tech: pd.DataFrame, query_embeddings: np.ndarray, top_n: int = 30
    ) -> pd.DataFrame:
        return ArticleProcessor.compute_trending_keywords(df_tech, self.sbert, query_embeddings, top_n)