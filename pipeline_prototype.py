import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.getcwd())

from src.storage.db import get_connection, init_db, save_articles
from src.crawler.crawl import crawl_all, enrich_with_content
from src.processor.pipeline import run_processor
from src.analyzer.pipeline import run_analyzer

def run_crawl():
    init_db()
    articles = crawl_all()
    enriched = enrich_with_content(articles)
    stats = save_articles(enriched)
    print(f"Crawl done: {stats['inserted']} inserted / {stats['skipped']} skipped")
    return stats

def run_process():
    conn = get_connection()
    df_raw = pd.read_sql("SELECT * FROM articles", conn)
    conn.close()
    print(f"Loaded {len(df_raw):,} articles from DB")
    output = run_processor(df_raw)
    print(f"Processor done: {len(output['df_clean'])} clean, {len(output['df_tech'])} tech articles")
    return output

def run_analyze():
    output_dir = Path("./outputs")
    output_dir.mkdir(exist_ok=True)
    conn = get_connection()
    df_raw = pd.read_sql("SELECT * FROM articles", conn)
    conn.close()
    processor_output = run_processor(df_raw)
    analyzer_output = run_analyzer(processor_output, output_dir=output_dir)
    report = analyzer_output["report"]
    stats = report["stats"]
    print(f"Analyzer done: {stats['n_clusters']} clusters, coherence={stats['coherence']}, top keyword: {analyzer_output['top_keywords'][0]}")
    return analyzer_output

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", choices=["all", "crawl", "process", "analyze"], default="all")
    args = parser.parse_args()
    if args.step == "crawl":
        run_crawl()
    elif args.step == "process":
        run_process()
    elif args.step == "analyze":
        run_analyze()
    else:
        run_crawl()
        run_process()
        run_analyze()

if __name__ == "__main__":
    import pandas as pd
    main()