import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize
from sentence_transformers import SentenceTransformer

from src.processor.constants import STOPWORDS


def extract_trending_keywords(
    df_tech: pd.DataFrame,
    query_embeddings: np.ndarray,
    model: SentenceTransformer,
    top_n: int = 30,
    max_features: int = 300,
) -> pd.DataFrame:
    tfidf = TfidfVectorizer(
        max_features=max_features,
        ngram_range=(1, 2),
        stop_words=list(STOPWORDS),
        token_pattern=r'(?u)\b\w\w+\b',
        min_df=2,
    )
    tfidf_matrix = tfidf.fit_transform(df_tech['tokenized'])
    tfidf_scores = dict(zip(
        tfidf.get_feature_names_out(),
        tfidf_matrix.mean(axis=0).A1
    ))

    kw_list = list(tfidf_scores.keys())
    kw_embeds = model.encode(kw_list, normalize_embeddings=True, show_progress_bar=False)
    query_mean = normalize(query_embeddings.mean(axis=0, keepdims=True))
    kw_relevance = cosine_similarity(kw_embeds, query_mean).flatten()

    kw_df = pd.DataFrame({
        'keyword': kw_list,
        'tfidf': [tfidf_scores[k] for k in kw_list],
        'semantic': kw_relevance,
    })
    kw_df['combined'] = kw_df['tfidf'] * kw_df['semantic']
    kw_df = kw_df.sort_values('combined', ascending=False).reset_index(drop=True)

    print(f'Top 20 tech-relevant keywords (TF-IDF x semantic):')
    print(kw_df.head(20).to_string(index=False))

    return kw_df.head(top_n)