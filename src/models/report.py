from pydantic import BaseModel


class KeywordEntry(BaseModel):
    rank: int
    keyword: str
    tfidf_score: float
    semantic_score: float
    combined_score: float


class ClusterArticle(BaseModel):
    rank: int
    title: str
    source: str
    url: str
    published_at: str
    tech_score: float
    content_snippet: str


class ClusterReport(BaseModel):
    cluster_id: int
    topic: str
    article_count: int
    avg_tech_score: float
    cohesion_score: float
    combined_score: float
    top_keywords: list[tuple[str, float]]
    top_articles: list[ClusterArticle]


class HighlightedArticle(BaseModel):
    rank: int
    title: str
    source: str
    url: str
    published_at: str
    topic: str
    tech_score: float
    content_snippet: str


class TopicDistribution(BaseModel):
    topic: str
    count: int
    percentage: float


class DailyCount(BaseModel):
    date: str
    count: int


class ClusterQuality(BaseModel):
    k: int
    inertia: float
    silhouette: float
    chosen: bool


class AnalysisReport(BaseModel):
    generated_at: str
    week_start: str
    week_end: str
    stats: dict
    executive_summary: dict
    trending_keywords: list[KeywordEntry]
    topic_distribution: list[TopicDistribution]
    daily_counts: list[DailyCount]
    clusters: list[ClusterReport]
    highlighted_articles: list[HighlightedArticle]