from pathlib import Path

TFIDF_MAX_FEATURES: int = 300
TFIDF_MIN_DF: int = 2
TFIDF_NGRAM: tuple[int, int] = (1, 2)

TOP_KEYWORDS: int = 30
TOP_NEWS_PER_CLUSTER: int = 2
TOP_NEWS_GLOBAL: int = 15
HIGHLIGHT_TOP_N: int = 10

N_CLUSTERS_DEFAULT: int = 6
CLUSTER_EXPLORE_RADIUS: int = 3
TOP_CLUSTER_KEYWORDS: int = 10

REPORTS_DIR: Path = Path("/reports")