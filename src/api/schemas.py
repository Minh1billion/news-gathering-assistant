from pydantic import BaseModel


class StepStatus(BaseModel):
    running: bool
    cancelled: bool


class CrawlResult(BaseModel):
    inserted: int
    skipped: int
    status: str
    sources: list[str]


class ProcessResult(BaseModel):
    raw_total: int
    past_window: int
    after_filter: int
    after_token_filter: int
    tech_articles: int
    upserted_qdrant: int


class ReportMeta(BaseModel):
    filename: str
    generated_at: str
    week_start: str
    week_end: str
    total_articles: int


class KeywordResponse(BaseModel):
    rank: int
    keyword: str
    tfidf_score: float
    semantic_score: float
    combined_score: float


class ClusterKeyword(BaseModel):
    keyword: str
    score: float


class ClusterArticleResponse(BaseModel):
    rank: int
    title: str
    source: str
    url: str
    published_at: str
    tech_score: float
    content_snippet: str


class ClusterResponse(BaseModel):
    cluster_id: int
    topic: str
    article_count: int
    avg_tech_score: float
    cohesion_score: float
    combined_score: float
    top_keywords: list[ClusterKeyword]
    top_articles: list[ClusterArticleResponse]


class HighlightResponse(BaseModel):
    rank: int
    title: str
    source: str
    url: str
    published_at: str
    topic: str
    tech_score: float
    content_snippet: str


class TopicDistributionResponse(BaseModel):
    topic: str
    count: int
    percentage: float


class DailyCountResponse(BaseModel):
    date: str
    count: int


class ReportResponse(BaseModel):
    generated_at: str
    week_start: str
    week_end: str
    stats: dict
    executive_summary: dict
    trending_keywords: list[KeywordResponse]
    topic_distribution: list[TopicDistributionResponse]
    daily_counts: list[DailyCountResponse]
    clusters: list[ClusterResponse]
    highlighted_articles: list[HighlightResponse]