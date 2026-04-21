from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from .clusterer import run_clustering
from .keywords import extract_trending_keywords
from .reporter import build_report, save_report
from src.processor.constants import SEMANTIC_THRESHOLD

OUTPUT_DIR = Path('notebooks/outputs')


def run_analyzer(
    processor_output: dict,
    output_dir: Path = OUTPUT_DIR,
    n_clusters: int = None,
    min_cluster_size: int = 3,
    threshold: float = SEMANTIC_THRESHOLD,
) -> dict:
    df_raw: pd.DataFrame = processor_output['df_raw']
    df_clean: pd.DataFrame = processor_output['df_clean']
    df_tech: pd.DataFrame = processor_output['df_tech']
    tech_embeddings: np.ndarray = processor_output['tech_embeddings']
    query_embeddings: np.ndarray = processor_output['query_embeddings']
    model: SentenceTransformer = processor_output['model']

    print('=== ANALYZER: clustering ===')
    df_clustered, k, explore_results = run_clustering(
        df_tech, tech_embeddings, model,
        n_clusters=n_clusters,
        min_cluster_size=min_cluster_size,
    )
    cluster_labels = explore_results[k]['label_dict']

    print('\n=== ANALYZER: keyword extraction ===')
    top_kw_df = extract_trending_keywords(df_clustered, query_embeddings, model)
    top_keywords = top_kw_df['keyword'].tolist()

    print('\n=== ANALYZER: report generation ===')
    report = build_report(
        df_raw=df_raw,
        df_clean=df_clean,
        df_tech=df_clustered,
        cluster_labels=cluster_labels,
        explore_results=explore_results,
        n_clusters=k,
        threshold=threshold,
        top_keywords=top_keywords,
    )
    save_report(report, output_dir)

    return {
        'df_clustered': df_clustered,
        'cluster_labels': cluster_labels,
        'explore_results': explore_results,
        'n_clusters': k,
        'top_keywords': top_keywords,
        'report': report,
    }