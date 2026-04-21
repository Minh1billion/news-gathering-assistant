import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer

from .cleaner import load_and_clean, tokenize_and_filter
from .scorer import load_sbert, embed_articles, score_tech_relevance
from .constants import SEMANTIC_THRESHOLD


def run_processor(
    df_raw: pd.DataFrame,
    threshold: float = SEMANTIC_THRESHOLD,
    sbert_model: SentenceTransformer = None,
) -> dict:
    print('=== PROCESSOR: clean & filter ===')
    df_clean = load_and_clean(df_raw)
    df_tokenized = tokenize_and_filter(df_clean)

    print('\n=== PROCESSOR: embed & score ===')
    model = sbert_model or load_sbert()
    article_embeddings = embed_articles(df_tokenized, model)
    df_tech, tech_embeddings, query_embeddings = score_tech_relevance(
        df_tokenized, article_embeddings, model, threshold=threshold
    )

    return {
        'df_raw': df_raw,
        'df_clean': df_tokenized,
        'df_tech': df_tech,
        'tech_embeddings': tech_embeddings,
        'article_embeddings': article_embeddings,
        'query_embeddings': query_embeddings,
        'model': model,
    }