# News Gathering Assistant

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Docker](https://img.shields.io/badge/Docker-Container-2496ED?logo=docker&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-DB-4169E1?logo=postgresql&logoColor=white)
![Qdrant](https://img.shields.io/badge/Qdrant-VectorDB-FF4F8B)
![License](https://img.shields.io/badge/License-MIT-green)

A comprehensive news aggregation and analysis platform that automatically crawls Vietnamese tech news from multiple sources, processes articles with NLP, clusters them by topic, and generates interactive weekly intelligence reports.

## Overview

The News Gathering Assistant automates the entire pipeline from news gathering to intelligent analysis:

1. **Crawling**: Fetches articles from multiple Vietnamese news sources (RSS feeds and HTML scraping)
2. **Preprocessing**: Filters articles, generates semantic embeddings, and computes tech relevance scores
3. **Analysis**: Clusters articles by topic, extracts trending keywords, and generates weekly reports
4. **Visualization**: Interactive React-based dashboard displaying insights with charts and tables

### Key Features

- **Multi-source crawling**: Aggregates news from VNExpress, ThanhNien, TuoiTre, and ZingNews
- **Semantic analysis**: Uses Vietnamese SBERT embeddings for content understanding
- **Automatic clustering**: Groups articles into coherent topics using K-means
- **Keyword extraction**: TF-IDF + semantic scoring for trending keyword identification
- **Tech relevance scoring**: Filters articles based on relevance to technology topics
- **Weekly reports**: Generates comprehensive intelligence reports with executive summaries
- **Interactive dashboard**: React-based UI with charts, tables, and export functionality
- **REST API**: Full API for programmatic access to crawling, preprocessing, and analysis
- **Containerized deployment**: Docker Compose setup for easy deployment

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    News Gathering Assistant                │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────┐      ┌───────────────┐                   │
│  │   Crawler    │      │  Preprocessor │                   │
│  │  (HTML/RSS)  │──>   │   (Embeddings │                   │
│  └──────────────┘      │   + Filtering)│                   │
│         │              └───────────────┘                   │
│         │                     │                            │
│         └─────> ┌─────────────┴──────────┐                 │
│                 │                        │                 │
│          ┌──────▼───────┐         ┌──────▼──────┐          │
│          │  PostgreSQL  │         │   Qdrant    │          │
│          │   (Articles) │         │ (Embeddings)│          │
│          └──────────────┘         └─────────────┘          │
│                 │                        │                 │
│                 └──────────┬─────────────┘                 │
│                            │                               │
│                     ┌──────▼────────┐                      │
│                     │   Analyzer    │                      │
│                     │  (Clustering/ │                      │
│                     │   Keywords)   │                      │
│                     └──────┬────────┘                      │
│                            │                               │
│                     ┌──────▼────────┐                      │
│                     │  Weekly Report│                      │
│                     │     + API     │                      │
│                     └──────┬────────┘                      │
│                            │                               │
│                     ┌──────▼────────┐                      │
│                     │  React UI /   │                      │
│                     │  Dashboard    │                      │
│                     └───────────────┘                      │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Tech Stack

**Backend**
- **FastAPI**: Modern async Python web framework
- **Sentence-Transformers**: Vietnamese SBERT embeddings (`keepitreal/vietnamese-sbert`)
- **Qdrant**: Vector database for embeddings
- **PostgreSQL**: Relational database for article storage
- **scikit-learn**: ML for TF-IDF and clustering
- **BeautifulSoup4 + Feedparser**: Web scraping and RSS parsing
- **Groq API**: For advanced NLP analysis

**Frontend**
- **React 18**: UI framework
- **Vite**: Build tool and dev server
- **Recharts**: Chart visualization
- **React-to-Print**: PDF export functionality

**Infrastructure**
- **Docker & Docker Compose**: Containerized deployment
- **Nginx**: Reverse proxy for frontend
- **Python 3.11**: Runtime

## Project Structure

```
news-gathering-assistant/
├── src/
│   ├── main.py                 # FastAPI application entry point
│   ├── crawler/
│   │   ├── crawl.py           # Web crawler class
│   │   ├── config.py          # Source configurations
│   │   ├── fetcher.py         # Article detail fetching
│   │   ├── parsers.py         # HTML/RSS parsers
│   │   └── exporter.py        # Report export utilities
│   ├── processor/
│   │   ├── preprocess.py      # Article preprocessing pipeline
│   │   └── constants.py       # Tech queries and topic labels
│   ├── analyzer/
│   │   ├── analyze.py         # Core analysis logic
│   │   ├── clustering.py      # K-means clustering
│   │   └── models.py          # Data models
│   └── storage/
│       ├── db.py              # PostgreSQL operations
│       └── qdrant_store.py    # Qdrant vector store
├── dashboard/
│   ├── src/
│   │   ├── App.jsx            # Main React component
│   │   ├── components/        # UI components
│   │   ├── hooks/             # React hooks (useReport, useHealth)
│   │   ├── lib/               # Utilities and API client
│   │   └── index.css          # Global styles
│   ├── Dockerfile             # Frontend container
│   ├── nginx.conf             # Nginx config
│   └── package.json           # Node dependencies
├── notebooks/
│   ├── explore.ipynb          # Data exploration
│   ├── prototype_analyze.ipynb # Analysis prototyping
│   ├── prototype_process.ipynb # Processing prototyping
│   └── weekly_report.json     # Sample report
├── docker-compose.yml         # Service orchestration
├── Dockerfile                 # Backend container
├── requirements.txt           # Python dependencies
├── SETUP.md                   # Detailed setup guide
└── README.md                  # This file
```

## Getting Started

### Prerequisites

- Docker 24+ and Docker Compose 2.20+
- Git
- Python 3.11+ (for running notebooks locally, optional)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/Minh1billion/news-gathering-assistant.git
   cd news-gathering-assistant
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your settings if needed
   ```

3. **Build and start the stack**
   ```bash
   docker compose up --build
   ```

4. **Access the services**
   - Frontend: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

> **Note**: The first build downloads PyTorch and sentence-transformers (~5-15 minutes). Subsequent builds are much faster due to Docker layer caching.

### Stopping the Stack

```bash
# Stop all services
docker compose down

# Stop and remove all volumes (including database data)
docker compose down -v
```

## Usage

### API Endpoints

#### Health Check
```bash
curl http://localhost:8000/health
```

#### Crawl News
```bash
POST /crawl
```
Crawls articles from all configured sources and saves them to PostgreSQL.

**Response:**
```json
{
  "crawled": 42,
  "saved": 38,
  "sources": ["vnexpress", "thanhnien"]
}
```

#### Preprocess Articles
```bash
POST /preprocess
```
Filters articles, generates embeddings, and stores them in Qdrant.

**Response:**
```json
{
  "raw_total": 1250,
  "past_window": 850,
  "after_filter": 720,
  "after_token_filter": 650,
  "tech_articles": 580,
  "upserted_qdrant": 580
}
```

#### Analyze Articles
```bash
POST /analyze
```
Clusters articles, extracts keywords, and generates a comprehensive report.

**Response:**
```json
{
  "generated_at": "2026-04-22T06:00:00Z",
  "week_start": "2026-04-14",
  "week_end": "2026-04-21",
  "stats": {...},
  "executive_summary": {...},
  "trending_keywords": [...],
  "topic_distribution": [...],
  "clusters": [...],
  "highlighted_articles": [...]
}
```

#### Get Latest Report
```bash
GET /report
```
Returns the most recently generated analysis report.

#### Export Report
```bash
GET /export/pdf
```
Exports the latest report as a PDF file.

### Interactive Dashboard

The React dashboard displays:

- **Report Overview**: Key metrics (total articles, sources, clusters)
- **Executive Summary**: Landscape analysis and top keywords
- **Trending Keywords**: TF-IDF and semantic scores with charts
- **Topic Distribution**: Pie chart showing topic breakdown
- **Daily Article Counts**: Line chart of article volume over time
- **Topic Clusters**: Detailed view of each cluster with:
  - Cluster topic and article count
  - Top keywords
  - Top articles with content snippets
- **Highlighted Articles**: Important articles from across clusters
- **Export**: Print or download reports as PDF

## News Sources

The crawler automatically aggregates articles from four major Vietnamese tech news sources:

| Source | Type | URL |
|--------|------|-----|
| VNExpress | HTML + RSS | https://vnexpress.net/khoa-hoc-cong-nghe |
| ThanhNien | HTML + RSS | https://thanhnien.vn/cong-nghe.htm |
| TuoiTre | RSS | https://tuoitre.vn/cong-nghe.htm |
| ZingNews | RSS | https://znews.vn/cong-nghe.html |

Each source is configured with:
- Article selectors for HTML parsing
- Pagination patterns
- Content and date extraction selectors
- RSS feed URLs for RSS sources

## Analysis Pipeline

### 1. Crawling (`/crawl`)
- Fetches articles from configured sources
- Supports both HTML scraping and RSS feed parsing
- Enriches articles with full content and publication date
- Stores articles in PostgreSQL

### 2. Preprocessing (`/preprocess`)
- Filters articles from the past 7 days
- Removes duplicates and short articles
- Computes tech relevance score (semantic similarity to tech queries)
- Generates Vietnamese SBERT embeddings
- Stores vectors in Qdrant
- Stores metadata in PostgreSQL

### 3. Analysis (`/analyze`)
- Loads all processed articles from Qdrant
- Computes TF-IDF vectors
- Extracts top keywords (combined TF-IDF + semantic scores)
- Determines optimal number of clusters using silhouette score
- Clusters articles using K-means
- Assigns topic labels to clusters
- Generates executive summary
- Identifies highlighted articles
- Computes daily article counts
- Saves comprehensive report as JSON

### 4. Reporting & Visualization
- Displays interactive dashboard with charts and tables
- Allows filtering and exploring clusters
- Provides export functionality
- Generates printable reports

## Configuration

### Environment Variables

Edit `.env` to customize:

```dotenv
# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=newsdb
POSTGRES_USER=admin
POSTGRES_PASSWORD=supersecretpassword123

# Qdrant Vector Database
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

### News Sources

Edit `src/crawler/config.py` to add, remove, or modify news sources:

```python
SOURCES = {
    "your-source": {
        "type": "html",  # or "rss"
        "url": "https://example.com/tech",
        "base_url": "https://example.com",
        "article_selector": "div.article",
        "a_selector": "a.article-link",
        "date_selector": "span.date",
        "content_selector": "div.content p",
        "pagination": {
            "pattern": "https://example.com/tech?page={page}",
            "start": 2,
            "max_pages": 5,
        },
    }
}
```

## Development

### Running Tests

```bash
# Unit tests
python -m pytest tests/

# With coverage
python -m pytest --cov=src tests/
```

### Running Locally (without Docker)

1. **Set up Python environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Start PostgreSQL and Qdrant** (manually or via Docker)
   ```bash
   docker run -d -p 5432:5432 --name postgres -e POSTGRES_PASSWORD=mysecret postgres:15
   docker run -d -p 6333:6333 --name qdrant qdrant/qdrant:latest
   ```

3. **Start the backend**
   ```bash
   uvicorn src.main:app --reload
   ```

4. **Start the dashboard** (in another terminal)
   ```bash
   cd dashboard
   npm install
   npm run dev
   ```

### Jupyter Notebooks

Explore the data and prototype analysis steps:

```bash
# Install Jupyter
pip install jupyter

# Start Jupyter
jupyter notebook

# Open notebooks/explore.ipynb or prototype_*.ipynb
```

## Troubleshooting

### Backend takes long to start
- First build downloads PyTorch and sentence-transformers (~5-15 minutes)
- Subsequent builds use Docker cache and are much faster
- Check logs: `docker compose logs app`

### Dashboard won't connect to API
- Ensure the backend is healthy: `curl http://localhost:8000/health`
- Check CORS settings in `src/main.py`
- Verify firewall allows port 8000

### No articles found in reports
- Run `/crawl` endpoint first to fetch articles
- Run `/preprocess` to process articles
- Check PostgreSQL: `docker compose exec postgres psql -U admin -d newsdb`

### Memory issues
- Reduce `TFIDF_MAX_FEATURES` in `src/analyzer/analyze.py`
- Limit article window in `src/processor/preprocess.py`
- Reduce `N_CLUSTERS_DEFAULT` if clustering is slow

## Performance Notes

- **Crawling**: ~30-60 seconds for 100+ articles from multiple sources
- **Preprocessing**: ~5-10 minutes for 1000+ articles (depends on embedding model)
- **Analysis**: ~2-3 minutes for 500+ articles with clustering
- **Total pipeline**: ~10-15 minutes for a complete weekly report

## Data Storage

- **PostgreSQL**: Article content, metadata, and preprocessed data (~50MB per 10k articles)
- **Qdrant**: Vector embeddings (~30MB per 10k articles)
- **Reports**: JSON files in `/reports` directory (~1-2MB per report)

## API Documentation

Full interactive API documentation is available at: **http://localhost:8000/docs**

Uses Swagger UI for testing endpoints directly from the browser.

## Contributing

To extend this project:

1. Add new news sources in `src/crawler/config.py`
2. Create custom parsers in `src/crawler/parsers.py` for special cases
3. Modify analysis parameters in `src/analyzer/analyze.py`
4. Add new dashboard components in `dashboard/src/components/`
5. Extend API endpoints in `src/main.py`

## License

[Specify your license here]

## Support

For issues, questions, or suggestions, please [add your contact information or support channel].

---

**Last Updated**: April 2026
