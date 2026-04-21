import re
import pandas as pd
from underthesea import word_tokenize

from .constants import IMPORTANT_ENGLISH_KEYWORDS, STOPWORDS, MOJIBAKE_TERMS, MIN_TOKEN_LEN


def fix_mojibake(x):
    if not isinstance(x, str):
        return x
    try:
        return x.encode('latin1').decode('utf-8')
    except Exception:
        return x


def clean_text(text: str) -> str:
    text = re.sub(r'https?://\S+|www\.\S+', ' ', text)
    text = re.sub(r'\S+@\S+\.\S+', ' ', text)
    text = re.sub(r'[^\w\s]', ' ', text, flags=re.UNICODE)
    text = re.sub(r'\b\d+\b', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def remove_stopwords(tokenized_text: str) -> str:
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
    return ' '.join(filtered)


def load_and_clean(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()

    for col in ['title', 'content', 'url']:
        if col in df.columns:
            df[col] = df[col].apply(fix_mojibake)

    df['published_at'] = pd.to_datetime(df['published_at'], utc=True)
    cutoff = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=7)
    df = df[df['published_at'] >= cutoff].reset_index(drop=True)

    df['content'] = df['content'].fillna('')
    df['title'] = df['title'].fillna('')
    df['url'] = df['url'].fillna('') if 'url' in df.columns else ''

    df = df.drop_duplicates(subset=['url']).reset_index(drop=True)
    df = df.drop_duplicates(subset=['title']).reset_index(drop=True)

    print(f'Articles in past 7 days (after dedup): {len(df):,}')
    print(f'Date range: {df["published_at"].min().date()} -> {df["published_at"].max().date()}')
    return df


def tokenize_and_filter(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['text_raw'] = (df['title'] + ' ' + df['content']).str.lower()
    df['text_clean'] = df['text_raw'].apply(clean_text)
    df['mojibake_count'] = df['text_clean'].apply(
        lambda x: sum(x.count(t) for t in MOJIBAKE_TERMS)
    )
    df['tokenized'] = df['text_clean'].apply(lambda x: word_tokenize(x, format='text'))
    df['tokenized'] = df['tokenized'].apply(remove_stopwords)

    df = df[df['mojibake_count'] < 2].drop('mojibake_count', axis=1).reset_index(drop=True)
    df = df[df['tokenized'].str.split().str.len() >= MIN_TOKEN_LEN].reset_index(drop=True)

    print(f'Articles after mojibake + min-token filter: {len(df):,}')
    return df