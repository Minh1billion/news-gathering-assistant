# News Gathering Assistant

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Docker](https://img.shields.io/badge/Docker-Container-2496ED?logo=docker&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-DB-4169E1?logo=postgresql&logoColor=white)
![Qdrant](https://img.shields.io/badge/Qdrant-VectorDB-FF4F8B)
![License](https://img.shields.io/badge/License-MIT-green)

An automated pipeline for collecting, processing, and analysing Vietnamese tech news. It combines a multi-source crawler, an NLP pipeline built on SBERT + TF-IDF, K-Means clustering, and a React dashboard.

---

## Architecture

```
src/
├── main.py                        # FastAPI app factory + lifespan
│
├── api/
│   ├── routes.py                  # All route handlers
│   ├── schemas.py                 # Pydantic request/response schemas
│   └── serializers.py             # Domain model → response schema converters
│
├── pipeline/
│   ├── base.py                    # Abstract PipelineStep
│   ├── crawler/
│   │   ├── config.py              # SOURCES, HEADERS
│   │   ├── fetcher.py             # fetch_html, fetch_article_detail
│   │   ├── parsers.py             # parse_html_source, parse_rss_source
│   │   └── runner.py              # CrawlRunner(PipelineStep)
│   ├── processor/
│   │   ├── config.py              # TECH_QUERIES, TOPIC_LABELS, STOPWORDS, thresholds
│   │   └── runner.py              # ProcessRunner(PipelineStep)
│   └── analyzer/
│       ├── config.py              # TF-IDF params, cluster params, REPORTS_DIR
│       ├── clustering.py          # pick_best_k, build_cluster_keywords, build_clusters
│       └── runner.py              # AnalyzeRunner(PipelineStep) + save/load report
│
├── storage/
│   ├── db.py                      # PostgreSQL: init_db, save_articles, get_connection
│   └── vector_db.py               # QdrantStore: ensure_collection, upsert, scroll_all
│
└── models/
    └── report.py                  # Domain models (Pydantic): AnalysisReport, ClusterReport, …
```

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) v24+ and [Docker Compose](https://docs.docker.com/compose/) v2.20+
- [Git](https://git-scm.com/)
- Python 3.11+ and pip *(only required for running the notebooks locally)*

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Minh1billion/news-gathering-assistant.git
cd news-gathering-assistant
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

The default values work out of the box with Docker Compose:

```dotenv
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=newsdb
POSTGRES_USER=admin
POSTGRES_PASSWORD=supersecretpassword123

QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

> Only change `POSTGRES_HOST` / `QDRANT_HOST` if you are running the databases outside of Docker.

### 3. Build and start the stack

```bash
docker compose up --build
```

| Service     | Description         | URL                        |
|-------------|---------------------|----------------------------|
| `app`       | FastAPI backend     | http://localhost:8000      |
| `dashboard` | React + Nginx       | http://localhost:3000      |
| `postgres`  | PostgreSQL 15       | localhost:5432             |
| `qdrant`    | Qdrant vector DB    | localhost:6333             |

> **First build:** downloads PyTorch (CPU) and `sentence-transformers`, which can take 5–15 minutes. Subsequent builds use the Docker layer cache and are much faster.

Run in the background:

```bash
docker compose up --build -d
```

Stop the stack:

```bash
docker compose down       # keep data volumes
docker compose down -v    # also delete PostgreSQL + Qdrant volumes
```

### 4. Verify the installation

```bash
curl http://localhost:8000/health
# → {"status":"ok","ready":true,...}
```

Open the dashboard: [http://localhost:3000](http://localhost:3000)

---

## API Reference

### Full pipeline

| Method | Endpoint                      | Description                                  |
|--------|-------------------------------|----------------------------------------------|
| POST   | `/pipeline`                   | Run everything: crawl → preprocess → analyze |
| POST   | `/pipeline?skip_crawl=true`   | Skip the crawl step                          |
| POST   | `/pipeline/cancel`            | Cancel the running pipeline                  |
| GET    | `/pipeline/status`            | Pipeline running state                       |

### Individual steps

| Method | Endpoint              | Description                                 |
|--------|-----------------------|---------------------------------------------|
| POST   | `/crawl`              | Fetch articles from all configured sources  |
| POST   | `/crawl/cancel`       | Cancel a running crawl                      |
| GET    | `/crawl/status`       | Crawl running state                         |
| POST   | `/preprocess`         | Tokenize, embed, filter tech articles       |
| POST   | `/preprocess/cancel`  | Cancel a running preprocess                 |
| GET    | `/preprocess/status`  | Preprocess running state                    |
| POST   | `/analyze`            | Cluster articles and generate a report      |
| POST   | `/analyze/cancel`     | Cancel a running analysis                   |
| GET    | `/analyze/status`     | Analyze running state                       |

### Reports

| Method | Endpoint              | Description                         |
|--------|-----------------------|-------------------------------------|
| GET    | `/report`             | Latest generated report             |
| GET    | `/reports`            | List all saved reports              |
| GET    | `/reports/{filename}` | Download a specific report file     |

---

## Configuration

All tunable parameters live in the `config.py` of each pipeline step — no magic numbers scattered through business logic.

| File                               | Key parameters                                                              |
|------------------------------------|-----------------------------------------------------------------------------|
| `pipeline/processor/config.py`     | `WINDOW_DAYS`, `MIN_CONTENT_LEN`, `SEMANTIC_THRESHOLD`, `SBERT_BATCH_SIZE` |
| `pipeline/analyzer/config.py`      | `N_CLUSTERS_DEFAULT`, `TOP_KEYWORDS`, `HIGHLIGHT_TOP_N`                     |
| `pipeline/crawler/config.py`       | `SOURCES` — add or remove news sources here                                 |

### Adding a new news source

Add an entry to `SOURCES` in `pipeline/crawler/config.py`:

```python
"source_name": {
    "type": "rss",                           # or "html"
    "rss_url": "https://example.com/rss",
    "content_selector": "div.article-body p",
    "date_selector": "meta[property='article:published_time']",
    "base_url": "https://example.com",
    "url": "https://example.com",
    "article_selector": "",
    "a_selector": "",
},
```

---

## Jupyter Notebooks

Located in `notebooks/`. The Docker stack (at minimum the `postgres` service) must be running before launching the notebooks.

### Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows

pip install jupyter notebook ipykernel numpy pandas matplotlib seaborn \
  scikit-learn sentence-transformers underthesea psycopg2-binary wordcloud python-dotenv
```

### Launch

```bash
export $(grep -v '^#' .env | xargs)   # load env vars
jupyter notebook notebooks/
```

| Notebook                  | Purpose                                                       |
|---------------------------|---------------------------------------------------------------|
| `explore.ipynb`           | Raw data inspection, mojibake detection, date quality checks  |
| `prototype_process.ipynb` | Cleaning pipeline, deduplication, content filtering          |
| `prototype_analyze.ipynb` | TF-IDF + SBERT analysis, topic clustering, keyword extraction |

---

## Troubleshooting

**`docker compose` not found** — Ensure you have Docker Compose v2. Run `docker compose version` to check. Older setups may have `docker-compose` (v1 with a hyphen).

**App health check keeps failing** — The first startup is slow due to model loading. Check logs with `docker compose logs app`. The app allows up to 12 retries (~120 seconds) before Docker marks it unhealthy.

**Notebooks cannot connect to PostgreSQL** — Verify the `postgres` container is running (`docker compose ps`) and that your environment variables are loaded. The notebooks connect to `localhost:5432`, which is forwarded by default in `docker-compose.yml`.

**`underthesea` is slow on first run** — Expected behaviour. The library downloads its Vietnamese model on first use and caches it for subsequent calls.

**Out of memory during SBERT encoding** — Reduce `SBERT_BATCH_SIZE` in `pipeline/processor/config.py` (default `64`). A value of `16` or `32` is safer on memory-constrained machines.