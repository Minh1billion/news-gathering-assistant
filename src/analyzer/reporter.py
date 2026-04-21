import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def build_cluster_summary(df_tech: pd.DataFrame, cluster_labels: dict) -> list[dict]:
    summary = []
    for c in sorted(cluster_labels):
        subset = df_tech[df_tech['cluster'] == c]
        summary.append({
            'cluster_id': int(c),
            'label': cluster_labels[c],
            'n_articles': len(subset),
            'top_sources': {
                str(k): int(v)
                for k, v in subset['source'].value_counts().head(3).items()
            },
            'avg_tech_score': round(float(subset['tech_score'].mean()), 4),
        })
    return summary


def build_highlighted_news(df_tech: pd.DataFrame, top_per_cluster: int = 3) -> list[dict]:
    highlighted = (
        df_tech
        .sort_values('tech_score', ascending=False)
        .groupby('cluster')
        .head(top_per_cluster)
        .sort_values(['cluster', 'tech_score'], ascending=[True, False])
        .reset_index(drop=True)
    )
    rows = []
    for _, row in highlighted.iterrows():
        rows.append({
            'cluster': int(row['cluster']),
            'cluster_label': row['cluster_label'],
            'title': row['title'],
            'source': row['source'],
            'published_at': row['published_at'].isoformat(),
            'tech_score': round(float(row['tech_score']), 4),
            'url': row.get('url', ''),
        })
    return rows


def build_report(
    df_raw: pd.DataFrame,
    df_clean: pd.DataFrame,
    df_tech: pd.DataFrame,
    cluster_labels: dict,
    explore_results: dict,
    n_clusters: int,
    threshold: float,
    top_keywords: list[str],
) -> dict:
    return {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'week_range': {
            'start': df_tech['published_at'].min().date().isoformat(),
            'end': df_tech['published_at'].max().date().isoformat(),
        },
        'stats': {
            'total_articles_crawled': len(df_raw),
            'articles_past_7_days': len(df_clean),
            'articles_tech_filtered': len(df_tech),
            'threshold_used': threshold,
            'n_clusters': int(n_clusters),
            'coherence': round(float(explore_results[n_clusters]['coherence']), 4),
        },
        'trending_keywords': top_keywords,
        'cluster_summary': build_cluster_summary(df_tech, cluster_labels),
        'highlighted_news': build_highlighted_news(df_tech),
    }


def build_markdown(report: dict) -> str:
    lines = []
    lines.append('# Weekly Tech News Report')
    lines.append(f"**Period:** {report['week_range']['start']} → {report['week_range']['end']}")
    lines.append(f"**Generated:** {report['generated_at']}")
    lines.append('')
    lines.append('## Executive Summary')
    s = report['stats']
    lines.append(
        f"Trong tuần từ **{report['week_range']['start']}** đến **{report['week_range']['end']}**, "
        f"hệ thống thu thập được **{s['total_articles_crawled']:,}** bài báo, "
        f"trong đó **{s['articles_past_7_days']:,}** bài thuộc 7 ngày gần nhất. "
        f"Sau lọc semantic (threshold={s['threshold_used']}), còn lại **{s['articles_tech_filtered']:,}** bài công nghệ "
        f"được phân thành **{s['n_clusters']}** nhóm chủ đề (coherence={s['coherence']})."
    )
    lines.append('')
    lines.append('Các nhóm chủ đề nổi bật trong tuần:')
    for cs in report['cluster_summary']:
        lines.append(f"- **Cluster {cs['cluster_id']}** – {cs['label']}: {cs['n_articles']} bài")
    lines.append('')
    lines.append('## Trending Keywords')
    lines.append(' · '.join(f'`{k}`' for k in report['trending_keywords'][:20]))
    lines.append('')
    lines.append('## Highlighted News')
    current_cluster = None
    for item in report['highlighted_news']:
        if item['cluster'] != current_cluster:
            current_cluster = item['cluster']
            lines.append(f"### Cluster {item['cluster']}: {item['cluster_label']}")
        date_str = item['published_at'][:10]
        url = item['url']
        title = item['title']
        source = item['source']
        score = item['tech_score']
        if url:
            lines.append(f'- [{title}]({url}) — *{source}* ({date_str}) | score: {score}')
        else:
            lines.append(f'- **{title}** — *{source}* ({date_str}) | score: {score}')
    return '\n'.join(lines)


def save_report(report: dict, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / 'weekly_report.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f'Saved: {json_path}')

    md_path = output_dir / 'weekly_report.md'
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(build_markdown(report))
    print(f'Saved: {md_path}')

    return json_path, md_path