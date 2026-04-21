import re
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize
from underthesea import word_tokenize

MOJIBAKE_PATTERNS = [
    r"Ã©|Ã |Ã¢|Æ°|Ã´|Ã³|Ã¹|Ã",
    r"â€™|â€œ|â€|â€˜|â€¦",
]

IMPORTANT_ENGLISH_KEYWORDS = {
    "ai","ml","llm","gpt","openai","chatgpt","github","python","java",
    "javascript","typescript","sql","api","web","app","ios","android",
    "cloud","aws","azure","google","meta","nvidia","tesla","apple",
    "samsung","iphone","bitcoin","ethereum","blockchain","nft","metaverse",
    "vr","ar","iot","ota","crm","erp","saas","paas","iaas","edge",
    "quantum","chip","5g","6g","cpu","gpu","ram","ssd","usb",
    "wifi","bluetooth","hdmi","usb-c","oled","amoled",
    "battery","megapixel","fps","tps","latency","bandwidth",
    "vpn","proxy","firewall","encryption","hash","zero-day",
    "exploit","malware","ransomware","trojan","worm","bot","ddos",
    "deepseek","gemini","claude","copilot","sora","mistral","llama",
}

STOPWORDS = {
    "một_số","tuy_nhiên","đồng_thời","không_chỉ","thay_vì",
    "trong_khi","bên_cạnh","ngoài_ra","theo_đó","do_đó",
    "vì_vậy","mặc_dù","bởi_vì","chẳng_hạn","hay_là",
    "hơn","sao","tàu","kỳ","tận","ưu","tiên","nhân","ích",
    "gói","bộ","kho","nút","cúp","trẻ","già","gia","chủ",
    "thừa","khuyên","bắt","ép","mách","báo","kể","nói",
    "có_thể","sử_dụng","cho_phép","giúp_đỡ","thực_hiện",
    "xây_dựng","hoạt_động","tiếp_tục","bao_gồm","liên_quan",
    "tham_gia","chia_sẻ","thành_công","hiệu_quả","quan_trọng",
    "trong","của","với","tại","từ","theo","qua","bằng",
    "hay","còn","mà","nếu","khi","vì","để","là","và",
    "ra","vào","đến","lại","đã","sẽ","đang","được","bị",
    "một","những","nhiều","này","đây","các","cùng","đó",
    "như","sau","trên","cho","cần","có","không","làm",
    "người","phát_triển","khả_năng",
    "thông_tin","nội_dung","vấn_đề","trường_hợp","thời_gian",
    "việc","điều","cách","loại","số","mức","lần","công_nghệ",
    "năm","tháng","ngày","tuần","giờ",
    "http","https","www","com","vn","html","utm","org","net",
    "họ","ta","tôi","bạn","chúng","mình","anh","chị","tp","hcm",
    "được","đang","sẽ","đã","phải","cần",
    "dùng","làm","tạo","cho","giúp","trợ","thực","thấy",
    "hoặc","và","nhưng","nếu","vì","nên",
    "mới","cũ","lớn","nhỏ","tốt","xấu","nhanh",
    "dân_trí","vnexpress","thanh_niên","tuổi_trẻ","báo_chí",
    "trang_web","website","công_bố","thông_báo","tin_tức",
    "cũng","chưa","ông","vẫn","chỉ","trước","khác","thêm","đạt","đưa",
}

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

MIN_CONTENT_LEN = 200
MIN_TOKEN_LEN = 20
SEMANTIC_THRESHOLD = 0.25
SBERT_CONTENT_CHARS = 512


def _fix_text(x):
    if not isinstance(x, str):
        return x
    try:
        return x.encode("latin1").decode("utf-8")
    except Exception:
        return x


def _has_mojibake(text: str) -> bool:
    for pattern in MOJIBAKE_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def _clean_text(text: str) -> str:
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"\S+@\S+\.\S+", " ", text)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\b\d+\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _remove_stopwords(tokenized: str) -> str:
    filtered = []
    for t in tokenized.split():
        is_english = t.isascii() and t.isalpha()
        if t.lower() in IMPORTANT_ENGLISH_KEYWORDS:
            filtered.append(t)
        elif not is_english and t not in STOPWORDS and len(t) > 2 and not t.isnumeric():
            filtered.append(t)
    return " ".join(filtered)


def build_dataframe(raw_rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(raw_rows)
    for col in ["title", "content", "url"]:
        if col in df.columns:
            df[col] = df[col].apply(_fix_text)

    df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
    df["content"] = df["content"].fillna("")
    df["title"] = df["title"].fillna("")
    df["content_len"] = df["content"].str.len()

    df["has_mojibake"] = df["title"].apply(_has_mojibake) | df["content"].apply(_has_mojibake)
    return df


def filter_articles(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.drop_duplicates(subset=["url"])
        .drop_duplicates(subset=["title"])
        .pipe(lambda d: d[~d["has_mojibake"]])
        .pipe(lambda d: d[d["content_len"] >= MIN_CONTENT_LEN])
        .reset_index(drop=True)
    )


def tokenize_articles(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["text_clean"] = (df["title"] + " " + df["content"]).str.lower().apply(_clean_text)
    df["tokenized"] = df["text_clean"].apply(
        lambda x: _remove_stopwords(word_tokenize(x, format="text"))
    )
    df["token_count"] = df["tokenized"].str.split().str.len()
    return df[df["token_count"] >= MIN_TOKEN_LEN].reset_index(drop=True)


def score_articles(df: pd.DataFrame, sbert_model) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    texts = (df["title"] + ". " + df["content"].str[:SBERT_CONTENT_CHARS]).tolist()
    embeddings = sbert_model.encode(texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True)
    query_embeddings = sbert_model.encode(TECH_QUERIES, normalize_embeddings=True)

    sim_matrix = cosine_similarity(embeddings, query_embeddings)
    df = df.copy()
    df["tech_score"] = sim_matrix.max(axis=1)
    df["tech_topic_idx"] = sim_matrix.argmax(axis=1)
    df["tech_topic"] = [TOPIC_LABELS[i] for i in df["tech_topic_idx"]]

    mask = df["tech_score"] >= SEMANTIC_THRESHOLD
    df_tech = df[mask].reset_index(drop=True)
    tech_embeddings = embeddings[mask.values]
    return df_tech, tech_embeddings, query_embeddings


def compute_trending_keywords(df_tech: pd.DataFrame, sbert_model, query_embeddings: np.ndarray, top_n: int = 30) -> pd.DataFrame:
    tfidf = TfidfVectorizer(
        max_features=300,
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b\w\w+\b",
        min_df=2,
    )
    mat = tfidf.fit_transform(df_tech["tokenized"])
    tfidf_scores = dict(zip(tfidf.get_feature_names_out(), mat.mean(axis=0).A1))

    kw_keys = list(tfidf_scores.keys())
    kw_embeds = sbert_model.encode(kw_keys, normalize_embeddings=True, show_progress_bar=False)
    query_mean = normalize(query_embeddings.mean(axis=0, keepdims=True))
    kw_relevance = cosine_similarity(kw_embeds, query_mean).flatten()

    kw_df = pd.DataFrame({
        "keyword": kw_keys,
        "tfidf": list(tfidf_scores.values()),
        "semantic": kw_relevance,
    })
    kw_df["combined"] = kw_df["tfidf"] * kw_df["semantic"]
    return kw_df.sort_values("combined", ascending=False).reset_index(drop=True).head(top_n)