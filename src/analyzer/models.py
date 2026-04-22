from dataclasses import dataclass


@dataclass
class KeywordEntry:
    rank: int
    keyword: str
    tfidf_score: float
    semantic_score: float
    combined_score: float


@dataclass
class ClusterArticle:
    rank: int
    title: str
    source: str
    url: str
    published_at: str
    tech_score: float
    content_snippet: str


@dataclass
class ClusterReport:
    cluster_id: int
    topic: str
    article_count: int
    avg_tech_score: float
    cohesion_score: float
    combined_score: float
    top_keywords: list[tuple[str, float]]
    top_articles: list[ClusterArticle]


@dataclass
class HighlightedArticle:
    rank: int
    title: str
    source: str
    url: str
    published_at: str
    topic: str
    tech_score: float
    content_snippet: str


@dataclass
class TopicDistribution:
    topic: str
    count: int
    percentage: float


@dataclass
class DailyCount:
    date: str
    count: int


@dataclass
class ClusterQuality:
    k: int
    inertia: float
    silhouette: float
    chosen: bool


@dataclass
class AnalysisReport:
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