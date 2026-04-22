# News Gathering Assistant - Setup Guide

This guide walks you through getting the project running from scratch, whether you want to spin up the full Docker stack or explore the data using the Jupyter notebooks.

---

## Prerequisites

Make sure the following are installed on your machine before proceeding:

- [Docker](https://docs.docker.com/get-docker/) (v24+) and [Docker Compose](https://docs.docker.com/compose/) (v2.20+)
- [Git](https://git-scm.com/)
- Python 3.11+ and pip *(only required for running the notebooks locally)*

---

## 1. Clone the Repository

```bash
git clone https://github.com/Minh1billion/news-gathering-assistant.git
cd news-gathering-assistant
```

---

## 2. Configure Environment Variables

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and verify or update the following variables:

```dotenv
# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=newsdb
POSTGRES_USER=admin
POSTGRES_PASSWORD=supersecretpassword123

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

> **Note:** The default values work out of the box for the Docker Compose setup. Only change `POSTGRES_HOST` / `QDRANT_HOST` if you're running the databases outside of Docker.

---

## 3. Build and Start the Stack

```bash
docker compose up --build
```

This will spin up four services:

| Service | Description | Port |
|---|---|---|
| `app` | FastAPI backend | `http://localhost:8000` |
| `dashboard` | React/Nginx frontend | `http://localhost:3000` |
| `postgres` | PostgreSQL 15 database | `localhost:5432` |
| `qdrant` | Qdrant vector database | `localhost:6333` |

> **First build note:** The backend image downloads PyTorch (CPU build) and `sentence-transformers` during the build step, which can take **5–15 minutes** depending on your internet connection. Subsequent builds use the Docker layer cache and are much faster.

The app service will wait for PostgreSQL to be healthy before starting. Once all services are up, the `dashboard` will wait for the app's `/health` endpoint to return `ready: true` before it becomes available.

To run in the background:

```bash
docker compose up --build -d
```

To stop everything:

```bash
docker compose down
```

To stop and also delete all persisted data (PostgreSQL and Qdrant volumes):

```bash
docker compose down -v
```

---

## 4. Verify the Installation

Check that the API is running:

```bash
curl http://localhost:8000/health
```

You should see a JSON response with `"ready": true`.

Open the dashboard in your browser: [http://localhost:3000](http://localhost:3000)

---

## 5. Running the Jupyter Notebooks (Prototype)

The `notebooks/` directory contains three exploratory notebooks for data analysis and prototyping. These connect directly to the PostgreSQL database, so **the Docker stack must be running first** (at minimum the `postgres` service).

### 5.1 - Install Notebook Dependencies

The notebooks require additional packages beyond what the Docker app uses. It is strongly recommended to use a virtual environment:

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows

# Install notebook dependencies
pip install \
  jupyter \
  notebook \
  ipykernel \
  numpy \
  pandas \
  matplotlib \
  seaborn \
  scikit-learn \
  sentence-transformers \
  underthesea \
  psycopg2-binary \
  wordcloud \
  python-dotenv
```

> **sentence-transformers** will also install `torch` as a dependency. If you're on a CPU-only machine this is fine - the notebooks use the `keepitreal/vietnamese-sbert` model which runs on CPU.

> **underthesea** is a Vietnamese NLP library used for word tokenization. It may take a moment to download its language models on first use.

### 5.2 - Set Environment Variables for the Notebooks

The notebooks read database credentials from environment variables. The easiest way to load them is to source your `.env` file before starting Jupyter:

```bash
# macOS / Linux
export $(grep -v '^#' .env | xargs)

# Or use python-dotenv - it's already in the requirements and used in the notebooks
```

### 5.3 - Launch Jupyter

```bash
jupyter notebook notebooks/
```

Then open the notebooks in this order for a guided exploration:

| Notebook | Purpose |
|---|---|
| `explore.ipynb` | Raw data inspection, mojibake detection, date quality checks |
| `prototype_process.ipynb` | Data cleaning pipeline, deduplication, content filtering |
| `prototype_analyze.ipynb` | TF-IDF + SBERT semantic analysis, topic clustering, keyword extraction |

---

## Project Structure

```
news-gathering-assistant/
├── src/
│   ├── analyzer/       # Analysis logic
│   ├── crawler/        # News crawlers / RSS fetchers
│   ├── processor/      # Text processing pipeline
│   ├── storage/        # DB and vector store clients
│   └── main.py         # FastAPI app entrypoint
├── dashboard/          # React frontend (Vite + Nginx)
├── notebooks/          # Jupyter notebooks for prototyping
├── reports/            # Generated reports (mounted volume)
├── docker-compose.yml
├── Dockerfile          # Backend image
├── requirements.txt
└── .env.example
```

---

## Troubleshooting

**`docker compose` not found** - Make sure you have Docker Compose v2. Try `docker compose version`. On older setups you may have `docker-compose` (with a hyphen) from v1.

**App health check fails repeatedly** - The first startup can be slow due to model loading. Check the logs with `docker compose logs app`. The app is allowed up to 12 retries (≈120 seconds) before Docker marks it unhealthy.

**Notebooks can't connect to PostgreSQL** - Make sure the `postgres` container is running (`docker compose ps`) and that your environment variables are loaded. The notebooks connect to `localhost:5432`, so the port must be forwarded (it is by default in `docker-compose.yml`).

**`underthesea` tokenization is slow on first run** - This is expected. The library downloads its Vietnamese model on first use and caches it locally for subsequent calls.

**Out of memory during `sentence-transformers` encoding** - Reduce `SBERT_BATCH_SIZE` in the notebook config block (default is `64`). A value of `16` or `32` is safer on machines with limited RAM.
