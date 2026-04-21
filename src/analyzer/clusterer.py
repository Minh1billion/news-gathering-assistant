import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize
from sentence_transformers import SentenceTransformer

from src.processor.constants import STOPWORDS, K_MIN, K_MAX


def reduce_dimensions(tech_embeddings: np.ndarray) -> tuple[np.ndarray, PCA]:
    n_components = min(30, len(tech_embeddings) - 1)
    pca = PCA(n_components=n_components, random_state=42)
    emb_reduced = pca.fit_transform(tech_embeddings)
    print(f'Variance explained by {n_components} PCs: {pca.explained_variance_ratio_.sum():.1%}')
    return emb_reduced, pca


def topic_coherence(tokenized_series: pd.Series, labels: np.ndarray, top_n: int = 10) -> float:
    scores = []
    for c in sorted(set(labels)):
        mask = labels == c
        subset = tokenized_series[mask].reset_index(drop=True)
        if len(subset) < 2:
            scores.append(0.0)
            continue
        vec = TfidfVectorizer(
            max_features=top_n, stop_words=None,
            ngram_range=(1, 1), min_df=1,
            token_pattern=r'(?u)\b\w\w+\b'
        )
        vec.fit(subset)
        top_kws = set(vec.get_feature_names_out())
        hit = subset.apply(lambda t: len(top_kws & set(t.split())) >= max(1, top_n // 3))
        scores.append(hit.mean())
    return float(np.mean(scores))


def get_cluster_labels_dict(
    embeddings: np.ndarray,
    tokenized_series: pd.Series,
    labels: np.ndarray,
    model: SentenceTransformer,
    top_n: int = 5,
) -> dict:
    result = {}
    for c in sorted(set(labels)):
        mask = labels == c
        subset = tokenized_series[mask]
        c_embeds = embeddings[mask]
        if len(subset) == 0:
            result[c] = 'empty'
            continue
        vec = TfidfVectorizer(
            max_features=200, stop_words=list(STOPWORDS),
            ngram_range=(1, 2), min_df=1,
            token_pattern=r'(?u)\b\w\w+\b'
        )
        mat = vec.fit_transform(subset)
        kw_scores = dict(zip(vec.get_feature_names_out(), mat.mean(axis=0).A1))
        kw_list = list(kw_scores.keys())
        kw_embeds = model.encode(kw_list, normalize_embeddings=True, show_progress_bar=False)
        center = normalize(c_embeds.mean(axis=0, keepdims=True))
        sem = cosine_similarity(kw_embeds, center).flatten()
        combined = {kw: kw_scores[kw] * sem[i] for i, kw in enumerate(kw_list)}
        top = sorted(combined, key=combined.get, reverse=True)[:top_n]
        result[c] = ' | '.join(top)
    return result


def scan_k_range(
    emb_reduced: np.ndarray,
    tokenized_series: pd.Series,
    k_min: int = K_MIN,
    k_max: int = K_MAX,
) -> tuple[int, list[float]]:
    coherence_scores = []
    print(f'\nScanning K in [{k_min}, {k_max}] for interpretability:')
    print(f'  {"K":>3}  {"coherence":>10}  {"min_size":>9}')

    for k in range(k_min, k_max + 1):
        if len(tokenized_series) < k * 2:
            print(f'  {k:>3}  {"(skipped)":>20}')
            coherence_scores.append(0.0)
            continue
        km = KMeans(n_clusters=k, random_state=42, n_init=20)
        labels = km.fit_predict(emb_reduced)
        coh = topic_coherence(tokenized_series, labels)
        min_sz = pd.Series(labels).value_counts().min()
        coherence_scores.append(coh)
        print(f'  {k:>3}  {coh:>10.4f}  {min_sz:>9}')

    best_k = int(np.argmax(coherence_scores)) + k_min
    best_k = max(k_min, min(k_max, best_k))
    print(f'\nBest K by coherence: {best_k} (score={max(coherence_scores):.4f})')
    return best_k, coherence_scores


def explore_k_range(
    emb_reduced: np.ndarray,
    tech_embeddings: np.ndarray,
    tokenized_series: pd.Series,
    model: SentenceTransformer,
    best_k_ref: int,
    k_min: int = K_MIN,
    k_max: int = K_MAX,
) -> dict:
    explore_lo = max(k_min, best_k_ref - 2)
    explore_hi = min(k_max, best_k_ref + 2)
    explore_range = range(explore_lo, explore_hi + 1)

    print(f'\nExploring K in {list(explore_range)} (best_k_ref={best_k_ref})')
    print('=' * 80)

    results = {}
    for k in explore_range:
        if len(tokenized_series) < k * 2:
            print(f'\n--- K = {k}  (skipped) ---')
            continue
        km = KMeans(n_clusters=k, random_state=42, n_init=20)
        labels = km.fit_predict(emb_reduced)
        coh = topic_coherence(tokenized_series, labels)
        sizes = pd.Series(labels).value_counts().sort_index()
        lbl_dict = get_cluster_labels_dict(tech_embeddings, tokenized_series, labels, model)
        results[k] = {
            'labels': labels,
            'coherence': coh,
            'label_dict': lbl_dict,
            'sizes': sizes.to_dict(),
        }
        print(f'\n--- K = {k}  (coherence={coh:.4f}) ---')
        for c in sorted(lbl_dict):
            sz = sizes.get(c, 0)
            print(f'  Cluster {c:>2} ({sz:>3} articles): {lbl_dict[c]}')

    if not results:
        raise RuntimeError('No valid K found in explore range.')

    return results


def select_best_k(explore_results: dict, min_cluster_size: int = 3) -> int:
    valid = {
        k: v for k, v in explore_results.items()
        if min(v['sizes'].values()) >= min_cluster_size
    }
    if not valid:
        valid = explore_results
    best_k = max(valid, key=lambda k: valid[k]['coherence'])
    print(f'\nSelected K={best_k} (coherence={explore_results[best_k]["coherence"]:.4f})')
    return best_k


def run_clustering(
    df_tech: pd.DataFrame,
    tech_embeddings: np.ndarray,
    model: SentenceTransformer,
    n_clusters: int = None,
    min_cluster_size: int = 3,
) -> tuple[pd.DataFrame, int, dict]:
    emb_reduced, _ = reduce_dimensions(tech_embeddings)

    best_k_ref, _ = scan_k_range(emb_reduced, df_tech['tokenized'])
    explore_results = explore_k_range(
        emb_reduced, tech_embeddings, df_tech['tokenized'], model, best_k_ref
    )

    k = n_clusters if n_clusters else select_best_k(explore_results, min_cluster_size)

    df_out = df_tech.copy()
    df_out['cluster'] = explore_results[k]['labels']
    df_out['cluster_label'] = df_out['cluster'].map(explore_results[k]['label_dict'])

    return df_out, k, explore_results