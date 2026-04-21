import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

import pandas as pd
from src.storage.db import get_connection, init_db, save_articles
from src.crawler.crawl import crawl_all, enrich_with_content
from src.processor.pipeline import run_processor
from src.analyzer.pipeline import run_analyzer

sys.path.insert(0, "/opt/airflow/project")

DEFAULT_ARGS = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


def task_crawl(**ctx):
    init_db()
    articles = crawl_all()
    enriched = enrich_with_content(articles)
    stats = save_articles(enriched)
    print(f"Crawl done: {stats['inserted']} inserted / {stats['skipped']} skipped")
    return stats


def task_process(**ctx):
    conn = get_connection()
    df_raw = pd.read_sql("SELECT * FROM articles", conn)
    conn.close()
    print(f"Loaded {len(df_raw):,} articles from DB")

    output = run_processor(df_raw)

    ti = ctx["ti"]
    ti.xcom_push(key="n_clean", value=len(output["df_clean"]))
    ti.xcom_push(key="n_tech", value=len(output["df_tech"]))
    print(f"Processor done: {len(output['df_tech'])} tech articles")


def task_analyze(**ctx):
    output_dir = Path("/opt/airflow/project/notebooks/outputs")

    conn = get_connection()
    df_raw = pd.read_sql("SELECT * FROM articles", conn)
    conn.close()

    processor_output = run_processor(df_raw)
    analyzer_output = run_analyzer(processor_output, output_dir=output_dir)

    report = analyzer_output["report"]
    stats = report["stats"]
    print(
        f"Analyzer done: {stats['n_clusters']} clusters, "
        f"coherence={stats['coherence']}, "
        f"top keyword: {analyzer_output['top_keywords'][0]}"
    )


with DAG(
    dag_id="news_pipeline_daily",
    default_args=DEFAULT_ARGS,
    description="Daily crawl → process → analyze Vietnamese tech news",
    schedule_interval="0 23 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["news", "nlp"],
) as dag:

    crawl = PythonOperator(
        task_id="crawl",
        python_callable=task_crawl,
    )

    process = PythonOperator(
        task_id="process",
        python_callable=task_process,
    )

    analyze = PythonOperator(
        task_id="analyze",
        python_callable=task_analyze,
    )

    crawl >> process >> analyze