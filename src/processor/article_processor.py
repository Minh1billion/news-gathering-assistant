import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

from .constants import (
    MIN_CONTENT_LEN,
    MIN_TOKEN_LEN,
    SEMANTIC_THRESHOLD,
    SBERT_CONTENT_CHARS,
    TECH_QUERIES,
    TOPIC_LABELS,
)
from .text_processor import fix_text, has_mojibake, clean_text, tokenize_and_filter


class ArticleProcessor:
    @staticmethod
    def build_dataframe(raw_rows: list[dict]) -> pd.DataFrame:
        df = pd.DataFrame(raw_rows)
        for col in ["title", "content", "url"]:
            if col in df.columns:
                df[col] = df[col].apply(fix_text)
        df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
        df["content"] = df["content"].fillna("")
        df["title"] = df["title"].fillna("")
        df["content_len"] = df["content"].str.len()
        df["has_mojibake"] = df["title"].apply(has_mojibake) | df["content"].apply(has_mojibake)
        return df

    @staticmethod
    def filter_articles(df: pd.DataFrame) -> pd.DataFrame:
        return (
            df.drop_duplicates(subset=["url"])
            .drop_duplicates(subset=["title"])
            .pipe(lambda d: d[~d["has_mojibake"]])
            .pipe(lambda d: d[d["content_len"] >= MIN_CONTENT_LEN])
            .reset_index(drop=True)
        )

    @staticmethod
    def tokenize_articles(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["text_clean"] = (df["title"] + " " + df["content"]).str.lower().apply(clean_text)
        df["tokenized"] = df["text_clean"].apply(tokenize_and_filter)
        df["token_count"] = df["tokenized"].str.split().str.len()
        return df[df["token_count"] >= MIN_TOKEN_LEN].reset_index(drop=True)

    @staticmethod
    def score_articles(
        df: pd.DataFrame, sbert_model
    ) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
        texts = (df["title"] + ". " + df["content"].str[:SBERT_CONTENT_CHARS]).tolist()
        embeddings = sbert_model.encode(
            texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True
        )
        query_embeddings = sbert_model.encode(TECH_QUERIES, normalize_embeddings=True)
        sim_matrix = cosine_similarity(embeddings, query_embeddings)
        df = df.copy()
        df["tech_score"] = sim_matrix.max(axis=1)
        df["tech_topic_idx"] = sim_matrix.argmax(axis=1)
        df["tech_topic"] = [TOPIC_LABELS[i] for i in df["tech_topic_idx"]]
        mask = df["tech_score"] >= SEMANTIC_THRESHOLD
        return df[mask].reset_index(drop=True), embeddings[mask.values], query_embeddings

    @staticmethod
    def compute_trending_keywords(
        df_tech: pd.DataFrame, sbert_model, query_embeddings: np.ndarray, top_n: int = 30
    ) -> pd.DataFrame:
        tfidf = TfidfVectorizer(
            max_features=300,
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w\w+\b",
            min_df=2,
        )
        mat = tfidf.fit_transform(df_tech["tokenized"])
        tfidf_scores = dict(zip(tfidf.get_feature_names_out(), mat.mean(axis=0).A1))
        kw_keys = list(tfidf_scores.keys())
        kw_embeds = sbert_model.encode(kw_keys, normalize_embeddings=True, show_progress_bar=False)
        query_mean = normalize(query_embeddings.mean(axis=0, keepdims=True))
        kw_relevance = cosine_similarity(kw_embeds, query_mean).flatten()
        kw_df = pd.DataFrame({
            "keyword": kw_keys,
            "tfidf": list(tfidf_scores.values()),
            "semantic": kw_relevance,
        })
        kw_df["combined"] = kw_df["tfidf"] * kw_df["semantic"]
        return kw_df.sort_values("combined", ascending=False).head(top_n).reset_index(drop=True)