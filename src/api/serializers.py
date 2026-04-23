from src.models.report import AnalysisReport
from .schemas import (
    ClusterArticleResponse,
    ClusterKeyword,
    ClusterResponse,
    DailyCountResponse,
    HighlightResponse,
    KeywordResponse,
    ReportResponse,
    TopicDistributionResponse,
)


def _cluster_response(c) -> ClusterResponse:
    return ClusterResponse(
        cluster_id=c.cluster_id,
        topic=c.topic,
        article_count=c.article_count,
        avg_tech_score=c.avg_tech_score,
        cohesion_score=c.cohesion_score,
        combined_score=c.combined_score,
        top_keywords=[ClusterKeyword(keyword=kw, score=sc) for kw, sc in c.top_keywords],
        top_articles=[
            ClusterArticleResponse(
                rank=a.rank,
                title=a.title,
                source=a.source,
                url=a.url,
                published_at=a.published_at,
                tech_score=a.tech_score,
                content_snippet=a.content_snippet,
            )
            for a in c.top_articles
        ],
    )


def report_to_response(report: AnalysisReport) -> ReportResponse:
    return ReportResponse(
        generated_at=report.generated_at,
        week_start=report.week_start,
        week_end=report.week_end,
        stats=report.stats,
        executive_summary=report.executive_summary,
        trending_keywords=[
            KeywordResponse(
                rank=k.rank,
                keyword=k.keyword,
                tfidf_score=k.tfidf_score,
                semantic_score=k.semantic_score,
                combined_score=k.combined_score,
            )
            for k in report.trending_keywords
        ],
        topic_distribution=[
            TopicDistributionResponse(topic=t.topic, count=t.count, percentage=t.percentage)
            for t in report.topic_distribution
        ],
        daily_counts=[DailyCountResponse(date=d.date, count=d.count) for d in report.daily_counts],
        clusters=[_cluster_response(c) for c in report.clusters],
        highlighted_articles=[
            HighlightResponse(
                rank=a.rank,
                title=a.title,
                source=a.source,
                url=a.url,
                published_at=a.published_at,
                topic=a.topic,
                tech_score=a.tech_score,
                content_snippet=a.content_snippet,
            )
            for a in report.highlighted_articles
        ],
    )


def dict_to_response(data: dict) -> ReportResponse:
    return ReportResponse(
        generated_at=data["generated_at"],
        week_start=data["week_start"],
        week_end=data["week_end"],
        stats=data["stats"],
        executive_summary=data["executive_summary"],
        trending_keywords=[KeywordResponse(**k) for k in data["trending_keywords"]],
        topic_distribution=[TopicDistributionResponse(**t) for t in data["topic_distribution"]],
        daily_counts=[DailyCountResponse(**d) for d in data["daily_counts"]],
        clusters=[
            ClusterResponse(
                cluster_id=c["cluster_id"],
                topic=c["topic"],
                article_count=c["article_count"],
                avg_tech_score=c["avg_tech_score"],
                cohesion_score=c["cohesion_score"],
                combined_score=c["combined_score"],
                top_keywords=[ClusterKeyword(keyword=kw, score=sc) for kw, sc in c["top_keywords"]],
                top_articles=[ClusterArticleResponse(**a) for a in c["top_articles"]],
            )
            for c in data["clusters"]
        ],
        highlighted_articles=[HighlightResponse(**a) for a in data["highlighted_articles"]],
    )