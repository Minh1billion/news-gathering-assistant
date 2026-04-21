import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from .constants import SBERT_MODEL_NAME, TECH_QUERIES, SEMANTIC_THRESHOLD


def load_sbert() -> SentenceTransformer:
    model = SentenceTransformer(SBERT_MODEL_NAME)
    print(f'Model loaded: {SBERT_MODEL_NAME}')
    return model


def embed_articles(df: pd.DataFrame, model: SentenceTransformer) -> np.ndarray:
    texts = (df['title'] + '. ' + df['content'].str[:512]).tolist()
    embeddings = model.encode(
        texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True
    )
    return embeddings


def score_tech_relevance(
    df: pd.DataFrame,
    article_embeddings: np.ndarray,
    model: SentenceTransformer,
    threshold: float = SEMANTIC_THRESHOLD,
) -> tuple[pd.DataFrame, np.ndarray]:
    query_embeddings = model.encode(TECH_QUERIES, normalize_embeddings=True)
    sim_matrix = cosine_similarity(article_embeddings, query_embeddings)

    df = df.copy()
    df['tech_score'] = sim_matrix.max(axis=1)
    df['tech_topic_idx'] = sim_matrix.argmax(axis=1)
    df['tech_topic'] = [TECH_QUERIES[i] for i in df['tech_topic_idx']]

    print(f'Score range: {df["tech_score"].min():.3f} - {df["tech_score"].max():.3f}')
    print('Score percentiles:')
    print(df['tech_score'].quantile([.25, .5, .75, .9, .95]).to_string())

    df_tech = df[df['tech_score'] >= threshold].reset_index(drop=True)
    tech_idx = df[df['tech_score'] >= threshold].index.tolist()
    tech_embeddings = article_embeddings[tech_idx]

    print(f'\nSelected threshold: {threshold}  ->  {len(df_tech):,} / {len(df):,} articles')
    return df_tech, tech_embeddings, query_embeddings