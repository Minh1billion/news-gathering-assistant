import logging
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from underthesea import word_tokenize
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)

from src.storage.db import get_connection
from src.storage.qdrant_store import QdrantStore

log = logging.getLogger(__name__)

WINDOW_DAYS = 7
MIN_CONTENT_LEN = 200
MIN_TOKEN_LEN = 20
SBERT_CONTENT_CHARS = 512
SBERT_BATCH_SIZE = 64
SEMANTIC_THRESHOLD = 0.25
QDRANT_COLLECTION = "articles"

TECH_QUERIES = [
    "trí tuệ nhân tạo AI machine learning deep learning mô hình chatgpt openai gemini",
    "điện thoại smartphone iphone samsung chip vi xử lý màn hình camera",
    "phần mềm ứng dụng lập trình code backend frontend framework",
    "an ninh mạng bảo mật dữ liệu hacker tấn công mã hóa",
    "xe điện năng lượng pin sạc xe tự lái ô tô điện",
    "mạng xã hội facebook tiktok youtube instagram người dùng nội dung",
    "khởi nghiệp startup đầu tư gọi vốn định giá IPO",
    "máy tính laptop desktop server chip CPU GPU",
    "blockchain bitcoin ethereum tiền mã hóa crypto",
]

TOPIC_LABELS = [
    "AI / ML",
    "Thiết bị di động",
    "Phần mềm / Dev",
    "An ninh mạng",
    "Xe điện / Năng lượng",
    "Mạng xã hội",
    "Startup / Đầu tư",
    "Phần cứng / Server",
    "Crypto / Blockchain",
]

IMPORTANT_ENGLISH_KEYWORDS = {
    "ai", "ml", "llm", "gpt", "openai", "chatgpt", "github", "python", "java",
    "javascript", "typescript", "sql", "api", "web", "app", "ios", "android",
    "cloud", "aws", "azure", "google", "meta", "nvidia", "tesla", "apple",
    "samsung", "iphone", "bitcoin", "ethereum", "blockchain", "nft", "metaverse",
    "vr", "ar", "iot", "ota", "crm", "erp", "saas", "paas", "iaas", "edge",
    "quantum", "chip", "5g", "6g", "cpu", "gpu", "ram", "ssd", "usb",
    "wifi", "bluetooth", "hdmi", "usb-c", "oled", "amoled",
    "battery", "megapixel", "fps", "tps", "latency", "bandwidth",
    "vpn", "proxy", "firewall", "encryption", "hash", "zero-day",
    "exploit", "malware", "ransomware", "trojan", "worm", "bot", "ddos",
    "deepseek", "gemini", "claude", "copilot", "sora", "mistral", "llama",
}

STOPWORDS = {
    "một_số", "tuy_nhiên", "đồng_thời", "không_chỉ", "thay_vì",
    "trong_khi", "bên_cạnh", "ngoài_ra", "theo_đó", "do_đó",
    "vì_vậy", "mặc_dù", "bởi_vì", "chẳng_hạn", "hay_là",
    "hơn", "sao", "tàu", "kỳ", "tận", "ưu", "tiên", "nhân", "ích",
    "gói", "bộ", "kho", "nút", "cúp", "trẻ", "già", "gia", "chủ",
    "thừa", "khuyên", "bắt", "ép", "mách", "báo", "kể", "nói",
    "có_thể", "sử_dụng", "cho_phép", "giúp_đỡ", "thực_hiện",
    "xây_dựng", "hoạt_động", "tiếp_tục", "bao_gồm", "liên_quan",
    "tham_gia", "chia_sẻ", "thành_công", "hiệu_quả", "quan_trọng",
    "trong", "của", "với", "tại", "từ", "theo", "qua", "bằng",
    "hay", "còn", "mà", "nếu", "khi", "vì", "để", "là", "và",
    "ra", "vào", "đến", "lại", "đã", "sẽ", "đang", "được", "bị",
    "một", "những", "nhiều", "này", "đây", "các", "cùng", "đó",
    "như", "sau", "trên", "cho", "cần", "có", "không", "làm",
    "người",
    "phát_triển", "khả_năng",
    "thông_tin", "nội_dung", "vấn_đề", "trường_hợp", "thời_gian",
    "việc", "điều", "cách", "loại", "số", "mức", "lần", "công_nghệ",
    "năm", "tháng", "ngày", "tuần", "giờ",
    "http", "https", "www", "com", "vn", "html", "utm", "org", "net",
    "họ", "ta", "tôi", "bạn", "chúng", "mình", "anh", "chị",
    "tp", "hcm",
    "được", "đang", "sẽ", "đã", "phải", "cần",
    "dùng", "làm", "tạo", "cho", "giúp", "trợ", "thực", "thấy",
    "hoặc", "và", "nhưng", "nếu", "vì", "nên",
    "mới", "cũ", "lớn", "nhỏ", "tốt", "xấu", "nhanh",
    "dân_trí", "vnexpress", "thanh_niên", "tuổi_trẻ", "báo_chí",
    "trang_web", "website", "công_bố", "thông_báo", "tin_tức",
    "cũng", "chưa", "ông", "vẫn", "chỉ", "trước", "khác", "thêm",
    "đạt", "đưa",
}

MOJIBAKE_PATTERNS = [
    ("latin1_as_utf8", r"Ã©|Ã |Ã¢|Æ°|Ã´|Ã³|Ã¹|Ã"),
    ("broken_sequences", r"â€™|â€œ|â€|â€˜|â€¦"),
]


@dataclass
class PreprocessStats:
    raw_total: int
    past_window: int
    after_filter: int
    after_token_filter: int
    tech_articles: int
    upserted_qdrant: int


def _fix_text(x: str) -> str:
    if not isinstance(x, str):
        return x
    try:
        return x.encode("latin1").decode("utf-8")
    except Exception:
        return x


def _detect_mojibake(df: pd.DataFrame) -> pd.DataFrame:
    df["has_mojibake"] = False
    for col in ["title", "content"]:
        for name, pattern in MOJIBAKE_PATTERNS:
            flag_col = f"{col}_{name}"
            df[flag_col] = df[col].fillna("").str.contains(pattern, regex=True)
            df["has_mojibake"] |= df[flag_col]
    return df


def _clean_text(text: str) -> str:
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"\S+@\S+\.\S+", " ", text)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\b\d+\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _remove_stopwords(tokenized_text: str) -> str:
    tokens = tokenized_text.split()
    filtered = []
    for t in tokens:
        is_english = t.isascii() and t.isalpha()
        is_important_english = t.lower() in IMPORTANT_ENGLISH_KEYWORDS
        if is_important_english:
            filtered.append(t)
        elif (
            t not in STOPWORDS
            and len(t) > 2
            and not t.isnumeric()
            and not is_english
        ):
            filtered.append(t)
    return " ".join(filtered)


def _save_processed_postgres(df: pd.DataFrame) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS processed_articles (
                article_id    INTEGER PRIMARY KEY REFERENCES articles(id),
                tokenized     TEXT    NOT NULL,
                tech_score    FLOAT   NOT NULL,
                tech_topic    TEXT    NOT NULL,
                processed_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO processed_articles
                    (article_id, tokenized, tech_score, tech_topic)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (article_id) DO UPDATE SET
                    tokenized    = EXCLUDED.tokenized,
                    tech_score   = EXCLUDED.tech_score,
                    tech_topic   = EXCLUDED.tech_topic,
                    processed_at = NOW()
            """, (
                int(row["id"]),
                row["tokenized"],
                float(row["tech_score"]),
                row["tech_topic"],
            ))
        conn.commit()
    finally:
        conn.close()


class Preprocessor:
    def __init__(self, sbert: SentenceTransformer, qdrant_store: QdrantStore) -> None:
        self.sbert = sbert
        self.qdrant_store = qdrant_store

    def run(self) -> PreprocessStats:
        log.info("Preprocessor: loading articles from Postgres")
        conn = get_connection()
        df_raw = pd.read_sql("SELECT * FROM articles ORDER BY id", conn)
        conn.close()

        for col in ["title", "content", "url"]:
            if col in df_raw.columns:
                df_raw[col] = df_raw[col].apply(_fix_text)

        df_raw = _detect_mojibake(df_raw)
        df_raw["published_at"] = pd.to_datetime(df_raw["published_at"], utc=True, errors="coerce")
        df_raw["content_len"] = df_raw["content"].fillna("").str.len()
        df_raw["content"] = df_raw["content"].fillna("")
        df_raw["title"] = df_raw["title"].fillna("")
        df_raw["url"] = df_raw["url"].fillna("")

        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=WINDOW_DAYS)
        df_week = df_raw[df_raw["published_at"] >= cutoff].copy()

        df_clean = (
            df_week
            .drop_duplicates(subset=["url"])
            .drop_duplicates(subset=["title"])
            .pipe(lambda d: d[~d["has_mojibake"]])
            .pipe(lambda d: d[d["content_len"] >= MIN_CONTENT_LEN])
            .reset_index(drop=True)
        )

        log.info("Raw: %d | Past %d days: %d | After filter: %d",
                 len(df_raw), WINDOW_DAYS, len(df_week), len(df_clean))

        df_clean["text_raw"] = (df_clean["title"] + " " + df_clean["content"]).str.lower()
        df_clean["text_clean"] = df_clean["text_raw"].apply(_clean_text)
        df_clean["tokenized_raw"] = df_clean["text_clean"].apply(
            lambda x: word_tokenize(x, format="text")
        )
        df_clean["tokenized"] = df_clean["tokenized_raw"].apply(_remove_stopwords)
        df_clean["token_count_after"] = df_clean["tokenized"].str.split().str.len()

        df_filtered = df_clean[df_clean["token_count_after"] >= MIN_TOKEN_LEN].reset_index(drop=True)
        log.info("After token filter: %d articles", len(df_filtered))

        texts_for_embed = (
            df_filtered["title"] + ". " + df_filtered["content"].str[:SBERT_CONTENT_CHARS]
        ).tolist()

        log.info("Encoding %d articles with SBERT", len(df_filtered))
        article_embeddings = self.sbert.encode(
            texts_for_embed,
            batch_size=SBERT_BATCH_SIZE,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        query_embeddings = self.sbert.encode(TECH_QUERIES, normalize_embeddings=True)

        sim_matrix = cosine_similarity(article_embeddings, query_embeddings)
        df_filtered = df_filtered.copy()
        df_filtered["tech_score"] = sim_matrix.max(axis=1)
        df_filtered["tech_topic_idx"] = sim_matrix.argmax(axis=1)
        df_filtered["tech_topic"] = [TOPIC_LABELS[i] for i in df_filtered["tech_topic_idx"]]

        tech_mask = df_filtered["tech_score"] >= SEMANTIC_THRESHOLD
        df_tech = df_filtered[tech_mask].reset_index(drop=True)
        tech_embeddings = article_embeddings[tech_mask.values]

        log.info("Tech articles (threshold=%.2f): %d / %d",
                 SEMANTIC_THRESHOLD, len(df_tech), len(df_filtered))

        log.info("Saving processed articles to Postgres")
        _save_processed_postgres(df_tech)

        vector_size = tech_embeddings.shape[1]

        self.qdrant_store.ensure_collection(vector_size)

        log.info("Upserting %d vectors to Qdrant", len(df_tech))
        upserted = self.qdrant_store.upsert_articles(df_tech, tech_embeddings)

        return PreprocessStats(
            raw_total=len(df_raw),
            past_window=len(df_week),
            after_filter=len(df_clean),
            after_token_filter=len(df_filtered),
            tech_articles=len(df_tech),
            upserted_qdrant=upserted,
        )