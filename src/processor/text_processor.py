import re
from underthesea import word_tokenize

from .constants import MOJIBAKE_PATTERNS, IMPORTANT_ENGLISH_KEYWORDS, STOPWORDS


def fix_text(x):
    if not isinstance(x, str):
        return x
    try:
        return x.encode("latin1").decode("utf-8")
    except Exception:
        return x


def has_mojibake(text: str) -> bool:
    for pattern in MOJIBAKE_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def clean_text(text: str) -> str:
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"\S+@\S+\.\S+", " ", text)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\b\d+\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize_and_filter(text: str) -> str:
    filtered = []
    tokenized = word_tokenize(text, format="text")
    
    for token in tokenized.split():
        is_english = token.isascii() and token.isalpha()
        if token.lower() in IMPORTANT_ENGLISH_KEYWORDS:
            filtered.append(token)
        elif not is_english and token not in STOPWORDS and len(token) > 2 and not token.isnumeric():
            filtered.append(token)
    
    return " ".join(filtered)
