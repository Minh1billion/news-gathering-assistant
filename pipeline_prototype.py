import pandas as pd
from pathlib import Path

from src.storage.db import get_connection
from src.processor.pipeline import run_processor
from src.analyzer.pipeline import run_analyzer
from src.processor.constants import SEMANTIC_THRESHOLD

OUTPUT_DIR = Path('notebooks/outputs')


def run_pipeline(
    threshold: float = SEMANTIC_THRESHOLD,
    n_clusters: int = None,
    min_cluster_size: int = 3,
    output_dir: Path = OUTPUT_DIR,
) -> dict:
    print('=== PIPELINE START ===\n')

    conn = get_connection()
    df_raw = pd.read_sql('SELECT * FROM articles', conn)
    conn.close()
    print(f'Total rows loaded: {len(df_raw):,}')

    processor_output = run_processor(df_raw, threshold=threshold)

    analyzer_output = run_analyzer(
        processor_output,
        output_dir=output_dir,
        n_clusters=n_clusters,
        min_cluster_size=min_cluster_size,
        threshold=threshold,
    )

    print('\n=== PIPELINE DONE ===')
    print(f"Clusters: {analyzer_output['n_clusters']}")
    print(f"Tech articles: {len(analyzer_output['df_clustered'])}")
    print(f"Top keywords: {analyzer_output['top_keywords'][:10]}")

    return {**processor_output, **analyzer_output}


if __name__ == '__main__':
    run_pipeline()