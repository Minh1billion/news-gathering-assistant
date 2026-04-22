import json
import os
import time
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="News Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
[data-testid="stAppViewContainer"] { background: #f5f4f0; }
[data-testid="stSidebar"] { background: #1a1a1a; border-right: none; }
[data-testid="stSidebar"] * { color: #d4d0c8 !important; }
[data-testid="stSidebarContent"] { padding: 2rem 1.5rem; }
[data-testid="stHeader"] { background: transparent; }

[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e0ddd6;
    border-top: 3px solid #1a1a1a;
    border-radius: 0;
    padding: 18px 20px;
}
[data-testid="stMetricLabel"] {
    color: #3a3a3a !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.68rem !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
[data-testid="stMetricValue"] {
    color: #1a1a1a !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 1.6rem !important;
    font-weight: 600 !important;
}
[data-testid="stMetricDelta"] {
    color: #2a7a3a !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.75rem !important;
}

.section-rule { display: flex; align-items: center; gap: 12px; margin: 32px 0 16px 0; }
.section-rule-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.14em;
    color: #3a3835; white-space: nowrap;
}
.section-rule-line { flex: 1; height: 1px; background: #c8c5be; }

.article-row {
    background: #ffffff;
    border: 1px solid #e0ddd6;
    border-left: 3px solid #1a1a1a;
    padding: 14px 18px; margin-bottom: 8px;
    transition: border-left-color 0.15s;
}
.article-row:hover { border-left-color: #c0392b; }
.article-row-title { font-size: 0.9rem; font-weight: 500; color: #1a1a1a; margin-bottom: 5px; line-height: 1.4; }
.article-row-meta {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem; color: #5a5855;
    margin-bottom: 6px; display: flex; gap: 16px;
    flex-wrap: wrap; align-items: center;
}
.article-snippet { font-size: 0.8rem; color: #3a3835; line-height: 1.55; }
.score-track { height: 2px; background: #e0ddd6; margin-top: 8px; }
.score-fill { height: 2px; background: #1a1a1a; }

.topic-tag {
    display: inline-block;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.62rem; font-weight: 600;
    letter-spacing: 0.06em; text-transform: uppercase;
    padding: 2px 7px; border: 1px solid currentColor; border-radius: 2px;
}

.cluster-block { background: #ffffff; border: 1px solid #e0ddd6; padding: 18px; height: 100%; }
.cluster-id { font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; color: #5a5855; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 4px; }
.cluster-topic { font-size: 0.95rem; font-weight: 600; color: #1a1a1a; margin-bottom: 10px; }
.cluster-stats { font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; color: #5a5855; display: flex; gap: 14px; margin-bottom: 12px; }
.kw-tag {
    display: inline-block;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.62rem; background: #f5f4f0;
    border: 1px solid #d0cdc6; color: #3a3835;
    padding: 2px 7px; margin: 2px 2px 2px 0; border-radius: 2px;
}

.summary-block {
    background: #1a1a1a; color: #d4d0c8;
    padding: 20px 24px; margin-bottom: 8px;
    line-height: 1.75; font-size: 0.88rem;
}
.summary-block b { color: #f0ede8; }

.report-header { border-bottom: 2px solid #1a1a1a; padding-bottom: 16px; margin-bottom: 24px; }
.report-title { font-family: 'IBM Plex Mono', monospace; font-size: 1.4rem; font-weight: 600; color: #1a1a1a; letter-spacing: -0.02em; }
.report-subtitle { font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: #5a5855; margin-top: 4px; }

.sidebar-nav-label {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.62rem !important;
    text-transform: uppercase; letter-spacing: 0.12em;
    color: #9b9890 !important; margin: 20px 0 8px 0;
}

.empty-state { background: #ffffff; border: 1px dashed #c8c5be; padding: 48px 32px; text-align: center; margin: 16px 0; }
.empty-state-title { font-family: 'IBM Plex Mono', monospace; font-size: 1rem; font-weight: 600; color: #1a1a1a; margin-bottom: 8px; }
.empty-state-body { font-size: 0.85rem; color: #5a5855; line-height: 1.6; }

.skeleton { background: #e8e6e1; border-radius: 2px; animation: pulse 1.5s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

a { color: #1a1a1a !important; text-decoration: underline !important; text-underline-offset: 2px; }
a:hover { color: #c0392b !important; }
#MainMenu, footer { visibility: hidden; }

/* ── Sidebar buttons ── */
.stButton > button {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.72rem !important; font-weight: 600 !important;
    text-transform: uppercase !important; letter-spacing: 0.08em !important;
    border-radius: 0 !important;
    border: 1px solid #d4d0c8 !important;
    background: transparent !important; color: #d4d0c8 !important;
    padding: 6px 14px !important; transition: all 0.15s !important;
}
.stButton > button:hover { background: #d4d0c8 !important; color: #1a1a1a !important; }
[data-testid="stSidebar"] .stButton > button { border-color: #d4d0c8 !important; color: #d4d0c8 !important; }
.stButton > button[data-testid="baseButton-primary"] {
    background: #f0ede8 !important; color: #1a1a1a !important; border-color: #f0ede8 !important;
}
.stButton > button[data-testid="baseButton-primary"]:hover {
    background: #ffffff !important; color: #1a1a1a !important; border-color: #ffffff !important;
}

/* ── Download buttons — match main-area export style ── */
[data-testid="stDownloadButton"] > button {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.72rem !important; font-weight: 600 !important;
    text-transform: uppercase !important; letter-spacing: 0.08em !important;
    border-radius: 0 !important;
    width: 100% !important;
    background: #1a1a1a !important;
    color: #f0ede8 !important;
    border: 1px solid #1a1a1a !important;
    padding: 8px 14px !important;
    transition: all 0.15s !important;
}
[data-testid="stDownloadButton"] > button:hover {
    background: #333333 !important;
    color: #ffffff !important;
    border-color: #333333 !important;
}

/* ── Form labels ── */
[data-testid="stMultiSelect"] label, [data-testid="stSlider"] label {
    color: #1a1a1a !important; font-size: 0.8rem !important; font-weight: 500 !important;
}
[data-testid="stSlider"] [data-testid="stMarkdownContainer"] p { color: #1a1a1a !important; }

/* ── Export row alignment ── */
.export-row-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.62rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.12em;
    color: #5a5855; margin-bottom: 6px;
}

/* ================================================================
   PRINT / PDF STYLES
   ================================================================ */
@media print {
    /* Hide all Streamlit chrome */
    [data-testid="stSidebar"],
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    header[data-testid="stHeader"],
    .stApp > header,
    footer,
    #MainMenu,
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    iframe,
    /* Hide the entire export bar section */
    .print-hide { display: none !important; }

    /* Reset page chrome */
    @page { margin: 16mm 14mm; size: A4 portrait; }
    html, body { background: #ffffff !important; }
    .stApp, [data-testid="stAppViewContainer"],
    [data-testid="block-container"],
    .main, .main > div { background: #ffffff !important; padding: 0 !important; margin: 0 !important; }

    /* Keep content colours */
    .report-header, .section-rule, .summary-block,
    .cluster-block, .article-row { break-inside: avoid; page-break-inside: avoid; }

    /* Plotly charts */
    .stPlotlyChart { break-inside: avoid; page-break-inside: avoid; }

    /* Ensure text prints dark */
    * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Constants ────────────────────────────────────────────────────────────────
API_BASE = os.environ.get("API_BASE_URL", "http://app:8000")
PLOT_BASE = dict(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#ffffff",
    font=dict(family="IBM Plex Mono, monospace", color="#3a3835", size=11),
    margin=dict(l=10, r=10, t=28, b=10),
)
TOPIC_COLORS = {
    "AI / ML": "#3498db",
    "Phan mem / Dev": "#5dade2",
    "Thiet bi di dong": "#e67e22",
    "An ninh mang": "#e74c3c",
    "Phan cung / Server": "#2ecc71",
    "Startup / Dau tu": "#9b59b6",
    "Crypto / Blockchain": "#f1c40f",
    "Xe dien / Nang luong": "#1abc9c",
    # Original Vietnamese keys still supported
    "Phan m\u1ec1m / Dev": "#5dade2",
    "Thi\u1ebft b\u1ecb di \u0111\u1ed9ng": "#e67e22",
    "An ninh m\u1ea1ng": "#e74c3c",
    "Ph\u1ea7n c\u1ee9ng / Server": "#2ecc71",
    "Startup / \u0110\u1ea7u t\u01b0": "#9b59b6",
    "Xe \u0111i\u1ec7n / N\u0103ng l\u01b0\u1ee3ng": "#1abc9c",
}


def topic_color(t):
    return TOPIC_COLORS.get(t, "#7f8c8d")


def fmt_date(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%d %b %Y  %H:%M")
    except Exception:
        return iso


def section(label):
    st.markdown(
        f'<div class="section-rule">'
        f'<span class="section-rule-label">{label}</span>'
        f'<span class="section-rule-line"></span>'
        f"</div>",
        unsafe_allow_html=True,
    )


# ── Data fetching ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_report() -> dict | None:
    try:
        resp = requests.get(f"{API_BASE}/report", timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


@st.cache_data(ttl=60)
def fetch_reports_list() -> list:
    try:
        resp = requests.get(f"{API_BASE}/reports", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return []


def api_action(endpoint, method="POST", params=None):
    fn = requests.post if method == "POST" else requests.get
    resp = fn(f"{API_BASE}/{endpoint}", params=params, timeout=300)
    resp.raise_for_status()
    return resp.json()


def wait_for_api(max_wait=120):
    bar = st.progress(0, text="Waiting for API to become ready...")
    for i in range(max_wait):
        try:
            if requests.get(f"{API_BASE}/health", timeout=3).json().get("ready"):
                bar.empty()
                return True
        except Exception:
            pass
        bar.progress((i + 1) / max_wait, text=f"Waiting for API... ({i + 1}s)")
        time.sleep(1)
    bar.empty()
    return False


# ── Charts ────────────────────────────────────────────────────────────────────
def chart_keywords(keywords):
    df = pd.DataFrame(keywords).head(15).sort_values("combined_score")
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["tfidf_score"], y=df["keyword"], orientation="h",
            name="TF-IDF", marker_color="#2c3e50", opacity=0.9,
        )
    )
    fig.add_trace(
        go.Bar(
            x=df["semantic_score"] * 0.1, y=df["keyword"], orientation="h",
            name="Semantic x0.1", marker_color="#95a5a6", opacity=0.7,
        )
    )
    fig.update_layout(
        **PLOT_BASE, barmode="overlay", height=400,
        legend=dict(orientation="h", y=1.1, x=0, font=dict(size=10)),
        xaxis=dict(showgrid=True, gridcolor="#e0ddd6", title="Score", zeroline=False),
        yaxis=dict(showgrid=False, tickfont=dict(size=10)),
    )
    return fig


def chart_topic_bar(topic_dist):
    df = pd.DataFrame(topic_dist).sort_values("count")
    fig = go.Figure(
        go.Bar(
            x=df["count"], y=df["topic"], orientation="h",
            marker_color=[topic_color(t) for t in df["topic"]],
            text=df["percentage"].apply(lambda p: f"{p}%"),
            textposition="outside",
            textfont=dict(family="IBM Plex Mono, monospace", size=10, color="#1a1a1a"),
            hovertemplate="<b>%{y}</b><br>%{x} articles<extra></extra>",
        )
    )
    fig.update_layout(
        **PLOT_BASE, height=300,
        xaxis=dict(showgrid=True, gridcolor="#e0ddd6", zeroline=False),
        yaxis=dict(showgrid=False, tickfont=dict(size=10)),
    )
    return fig


def chart_daily(daily):
    df = pd.DataFrame(daily)
    df["date"] = pd.to_datetime(df["date"])
    fig = go.Figure(
        go.Scatter(
            x=df["date"], y=df["count"], mode="lines+markers",
            line=dict(color="#2c3e50", width=1.5),
            marker=dict(size=5, color="#2c3e50"),
            fill="tozeroy", fillcolor="rgba(44,62,80,0.05)",
            hovertemplate="%{x|%d %b}<br><b>%{y} articles</b><extra></extra>",
        )
    )
    fig.update_layout(
        **PLOT_BASE, height=180,
        xaxis=dict(showgrid=False, tickformat="%d %b", tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor="#e0ddd6", zeroline=False),
    )
    return fig


def chart_cluster_scatter(clusters):
    fig = go.Figure()
    for c in clusters:
        color = topic_color(c["topic"])
        fig.add_trace(
            go.Scatter(
                x=[c["cohesion_score"]], y=[c["avg_tech_score"]],
                mode="markers+text",
                marker=dict(
                    size=c["article_count"] ** 0.6 * 4,
                    color=color, opacity=0.85,
                    line=dict(color="#ffffff", width=1.5),
                ),
                text=[f"C{c['cluster_id']}"],
                textposition="middle center",
                textfont=dict(size=9, color="#ffffff"),
                name=c["topic"],
                hovertemplate=(
                    f"<b>C{c['cluster_id']} - {c['topic']}</b><br>"
                    f"Cohesion: {c['cohesion_score']:.3f}<br>"
                    f"Tech score: {c['avg_tech_score']:.3f}<br>"
                    f"Articles: {c['article_count']}<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        **PLOT_BASE, height=300, showlegend=False,
        xaxis=dict(title="Cohesion", showgrid=True, gridcolor="#e0ddd6", zeroline=False),
        yaxis=dict(title="Avg Tech Score", showgrid=True, gridcolor="#e0ddd6", zeroline=False),
    )
    return fig


# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar(report):
    with st.sidebar:
        st.markdown(
            '<p style="font-family:IBM Plex Mono,monospace;font-size:0.95rem;'
            'font-weight:600;color:#f0ede8;letter-spacing:-0.01em;margin-bottom:2px;">'
            "◈ NEWS INTELLIGENCE</p>"
            '<p style="font-family:IBM Plex Mono,monospace;font-size:0.62rem;'
            'color:#9b9890;text-transform:uppercase;letter-spacing:0.12em;">'
            "Operations Dashboard</p>",
            unsafe_allow_html=True,
        )
        st.divider()
        st.markdown('<p class="sidebar-nav-label">Pipeline Control</p>', unsafe_allow_html=True)

        if st.button("Run Full Pipeline", width="stretch", type="primary"):
            with st.spinner("Running pipeline..."):
                try:
                    api_action("pipeline")
                    st.cache_data.clear()
                    st.success("Pipeline complete.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Crawl", width="stretch"):
                with st.spinner("Crawling..."):
                    try:
                        r = api_action("crawl")
                        st.success(f"{r.get('crawled', '?')} articles")
                    except Exception as e:
                        st.error(str(e))
        with c2:
            if st.button("Preprocess", width="stretch"):
                with st.spinner("Processing..."):
                    try:
                        r = api_action("preprocess")
                        st.success(f"Tech: {r.get('tech_articles', '?')}")
                    except Exception as e:
                        st.error(str(e))

        c3, c4 = st.columns(2)
        with c3:
            if st.button("Analyze", width="stretch"):
                with st.spinner("Analyzing..."):
                    try:
                        api_action("analyze")
                        st.cache_data.clear()
                        st.success("Done.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        with c4:
            if st.button("Refresh", width="stretch"):
                st.cache_data.clear()
                st.rerun()

        st.divider()
        if report:
            st.markdown('<p class="sidebar-nav-label">Report Period</p>', unsafe_allow_html=True)
            st.markdown(
                f'<p style="font-family:IBM Plex Mono,monospace;font-size:0.75rem;color:#d4d0c8;">'
                f'{report["week_start"]} — {report["week_end"]}</p>'
                f'<p style="font-family:IBM Plex Mono,monospace;font-size:0.62rem;color:#9b9890;">'
                f'Generated {fmt_date(report["generated_at"])}</p>',
                unsafe_allow_html=True,
            )
            st.divider()
            st.markdown('<p class="sidebar-nav-label">Topic Breakdown</p>', unsafe_allow_html=True)
            for td in report["topic_distribution"]:
                color = topic_color(td["topic"])
                pct = td["percentage"]
                st.markdown(
                    f'<div style="margin-bottom:8px;">'
                    f'<div style="display:flex;justify-content:space-between;'
                    f'font-family:IBM Plex Mono,monospace;font-size:0.68rem;margin-bottom:3px;">'
                    f'<span style="color:{color};">{td["topic"]}</span>'
                    f'<span style="color:#9b9890;">{td["count"]}</span></div>'
                    f'<div style="height:2px;background:#2a2a2a;">'
                    f'<div style="height:2px;background:{color};width:{pct}%;"></div>'
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
            st.divider()

        st.markdown('<p class="sidebar-nav-label">Saved Reports</p>', unsafe_allow_html=True)
        reports_list = fetch_reports_list()
        if reports_list:
            for r in reports_list[:5]:
                st.markdown(
                    f'<p style="font-family:IBM Plex Mono,monospace;font-size:0.62rem;'
                    f'color:#9b9890;margin-bottom:4px;">'
                    f'↳ {r["week_start"]}–{r["week_end"]} '
                    f'<span style="color:#6b6860;">({r["total_articles"]} art.)</span></p>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<p style="font-family:IBM Plex Mono,monospace;font-size:0.62rem;'
                'color:#6b6860;">No saved reports yet</p>',
                unsafe_allow_html=True,
            )


# ── Empty state ───────────────────────────────────────────────────────────────
def render_empty_state():
    st.markdown(
        '<div class="report-header">'
        '<div class="report-title">Weekly Tech Intelligence Report</div>'
        '<div class="report-subtitle">No report available</div>'
        "</div>",
        unsafe_allow_html=True,
    )
    for col, label in zip(
        st.columns(5),
        ["Total Articles", "Sources", "Clusters", "Dominant Topic", "Highlighted"],
    ):
        col.markdown(
            f'<div style="background:#ffffff;border:1px solid #e0ddd6;'
            f'border-top:3px solid #e0ddd6;padding:18px 20px;">'
            f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;'
            f'color:#c8c5be;text-transform:uppercase;letter-spacing:0.1em;">{label}</div>'
            f'<div class="skeleton" style="height:32px;width:60%;margin-top:8px;"></div>'
            f"</div>",
            unsafe_allow_html=True,
        )
    section("Status")
    st.markdown(
        '<div class="empty-state">'
        '<div class="empty-state-title">◈ No report data found</div>'
        '<div class="empty-state-body">'
        "Run the pipeline to crawl articles, preprocess them, and generate the first report.<br>"
        "Use <b>Run Full Pipeline</b> in the sidebar, or run each step individually."
        "</div></div>",
        unsafe_allow_html=True,
    )
    col_a, col_b, _ = st.columns([1, 1, 4])
    with col_a:
        if st.button("Run Full Pipeline", type="primary", width="stretch"):
            with st.spinner("Running pipeline..."):
                try:
                    api_action("pipeline")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
    with col_b:
        if st.button("Check Again", width="stretch"):
            st.cache_data.clear()
            st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────
def render_header(report):
    s = report["stats"]
    st.markdown(
        f'<div class="report-header">'
        f'<div class="report-title">Weekly Tech Intelligence Report</div>'
        f'<div class="report-subtitle">'
        f'Period: {report["week_start"]} — {report["week_end"]}'
        f' &nbsp;·&nbsp; Generated: {fmt_date(report["generated_at"])}'
        f"</div></div>",
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Articles", f"{s['total_tech_articles']:,}")
    c2.metric("Sources", s["sources"])
    c3.metric("Clusters", s["n_clusters"])
    c4.metric("Dominant Topic", s["dominant_topic"], f"{s['dominant_topic_pct']}%")
    c5.metric("Highlighted", report["executive_summary"]["highlight_count"])


# ── Export bar ────────────────────────────────────────────────────────────────
def render_export_bar(report):
    """
    Three equal-width export actions: JSON download, CSV download, Print-to-PDF.

    The Print button uses st.components.v1.html so that window.parent.print()
    is called on the TOP-LEVEL page — not the sandboxed iframe that
    st.markdown HTML runs inside.
    """
    section("Export")

    col1, col2, col3, _pad = st.columns([1, 1, 1, 3])

    # ── JSON ──────────────────────────────────────────────────────────────────
    with col1:
        st.markdown('<p class="export-row-label">Report JSON</p>', unsafe_allow_html=True)
        st.download_button(
            label="Download JSON",
            data=json.dumps(report, ensure_ascii=False, indent=2),
            file_name=(
                f"report_{report['week_start'].replace('/', '-')}"
                f"_{report['week_end'].replace('/', '-')}.json"
            ),
            mime="application/json",
            use_container_width=True,
            key="json_export",
        )

    # ── CSV ───────────────────────────────────────────────────────────────────
    with col2:
        st.markdown('<p class="export-row-label">Highlights CSV</p>', unsafe_allow_html=True)
        df_csv = pd.DataFrame(
            [
                {
                    "rank": a["rank"],
                    "title": a["title"],
                    "source": a["source"],
                    "url": a["url"],
                    "published_at": a["published_at"],
                    "topic": a["topic"],
                    "tech_score": a["tech_score"],
                }
                for a in report["highlighted_articles"]
            ]
        )
        st.download_button(
            label="Download CSV",
            data=df_csv.to_csv(index=False),
            file_name="highlights.csv",
            mime="text/csv",
            use_container_width=True,
            key="csv_export",
        )

    # ── Print / PDF ───────────────────────────────────────────────────────────
    # IMPORTANT: window.print() inside st.markdown iframes only prints that
    # iframe. We must use st.components.v1.html which also runs in an iframe,
    # but we call window.parent.print() to target the Streamlit host page.
    with col3:
        st.markdown('<p class="export-row-label">Print / PDF</p>', unsafe_allow_html=True)
        components.html(
            """
            <style>
              * { margin: 0; padding: 0; box-sizing: border-box; }
              button {
                width: 100%;
                background: #1a1a1a;
                color: #f0ede8;
                border: none;
                padding: 8px 14px;
                font-family: 'IBM Plex Mono', monospace;
                font-size: 0.72rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                cursor: pointer;
                transition: background 0.15s;
              }
              button:hover { background: #333333; }
            </style>
            <button onclick="window.parent.print()">Print / Save PDF</button>
            """,
            height=40,
        )


# ── Summary ───────────────────────────────────────────────────────────────────
def render_summary(es):
    section("Executive Summary")
    kws = "  ·  ".join(f"<b>{k}</b>" for k in es["top_keywords"])
    st.markdown(
        f'<div class="summary-block">'
        f"<b>Overview</b><br>{es['landscape']}<br><br>"
        f"<b>Dominant Topic</b> &nbsp; {es['dominant_topic']} ({es['dominant_topic_pct']}%)<br><br>"
        f"<b>Top Keywords</b> &nbsp; {kws}"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── Keywords + Topics ────────────────────────────────────────────────────────
def render_keywords_topics(report):
    section("Trending Keywords & Topic Distribution")
    col_kw, col_bar = st.columns([3, 2], gap="large")
    with col_kw:
        st.markdown(
            '<p style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;'
            'color:#5a5855;text-transform:uppercase;letter-spacing:0.1em;">'
            "Top 15 — TF-IDF / Semantic</p>",
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            chart_keywords(report["trending_keywords"]),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with col_bar:
        st.markdown(
            '<p style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;'
            'color:#5a5855;text-transform:uppercase;letter-spacing:0.1em;">'
            "Articles per topic</p>",
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            chart_topic_bar(report["topic_distribution"]),
            use_container_width=True,
            config={"displayModeBar": False},
        )


# ── Timeline ──────────────────────────────────────────────────────────────────
def render_timeline(daily):
    section("Daily Volume")
    st.plotly_chart(
        chart_daily(daily),
        use_container_width=True,
        config={"displayModeBar": False},
    )


# ── Clusters ──────────────────────────────────────────────────────────────────
def render_clusters(clusters):
    section("Cluster Analysis")
    col_scatter, col_table = st.columns([2, 3], gap="large")
    with col_scatter:
        st.markdown(
            '<p style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;'
            'color:#5a5855;text-transform:uppercase;letter-spacing:0.1em;">'
            "Cohesion vs Tech Score (size = article count)</p>",
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            chart_cluster_scatter(clusters),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with col_table:
        st.markdown(
            '<p style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;'
            'color:#5a5855;text-transform:uppercase;letter-spacing:0.1em;">'
            "Cluster summary table</p>",
            unsafe_allow_html=True,
        )
        rows = [
            {
                "ID": f"C{c['cluster_id']}",
                "Topic": c["topic"],
                "Articles": c["article_count"],
                "Tech": round(c["avg_tech_score"], 3),
                "Cohesion": round(c["cohesion_score"], 3),
                "Score": round(c["combined_score"], 3),
                "Keywords": ", ".join(k["keyword"] for k in c["top_keywords"][:5]),
            }
            for c in clusters
        ]
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
            height=280,
            column_config={
                "ID": st.column_config.TextColumn(width="small"),
                "Topic": st.column_config.TextColumn(width="medium"),
                "Articles": st.column_config.NumberColumn(width="small"),
                "Tech": st.column_config.NumberColumn(width="small", format="%.3f"),
                "Cohesion": st.column_config.NumberColumn(width="small", format="%.3f"),
                "Score": st.column_config.NumberColumn(width="small", format="%.3f"),
                "Keywords": st.column_config.TextColumn(width="large"),
            },
        )

    st.markdown(
        '<p style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;'
        'color:#5a5855;text-transform:uppercase;letter-spacing:0.1em;margin-top:24px;">'
        "Top 3 clusters — representative articles</p>",
        unsafe_allow_html=True,
    )
    cols = st.columns(3, gap="medium")
    for i, c in enumerate(clusters[:3]):
        color = topic_color(c["topic"])
        kw_html = "".join(
            f'<span class="kw-tag">{k["keyword"]}</span>' for k in c["top_keywords"][:6]
        )
        articles_html = "".join(
            f'<div style="margin-top:10px;padding-top:10px;border-top:1px solid #e0ddd6;">'
            f'<a href="{a["url"]}" target="_blank" '
            f'style="font-size:0.8rem;font-weight:500;color:#1a1a1a !important;">'
            f'{a["title"]}</a>'
            f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.62rem;'
            f'color:#5a5855;margin-top:3px;">'
            f'{a["source"]}  ·  score {a["tech_score"]:.3f}</div></div>'
            for a in c["top_articles"]
        )
        with cols[i]:
            st.markdown(
                f'<div class="cluster-block">'
                f'<div class="cluster-id">Cluster {c["cluster_id"]}</div>'
                f'<div class="cluster-topic" style="color:{color};">{c["topic"]}</div>'
                f'<div class="cluster-stats">'
                f'<span>{c["article_count"]} art.</span>'
                f'<span>coh {c["cohesion_score"]:.3f}</span>'
                f'<span>combined {c["combined_score"]:.3f}</span>'
                f"</div>{kw_html}{articles_html}</div>",
                unsafe_allow_html=True,
            )


# ── Highlights ────────────────────────────────────────────────────────────────
def render_highlights(articles):
    section("Highlighted Articles")
    col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
    all_topics = sorted({a["topic"] for a in articles})
    all_sources = sorted({a["source"] for a in articles})
    with col_f1:
        sel_topic = st.multiselect("Filter by topic", all_topics, placeholder="All topics")
    with col_f2:
        sel_source = st.multiselect("Filter by source", all_sources, placeholder="All sources")
    with col_f3:
        min_score = st.slider("Min tech score", 0.0, 1.0, 0.0, 0.05)

    filtered = [
        a for a in articles
        if (not sel_topic or a["topic"] in sel_topic)
        and (not sel_source or a["source"] in sel_source)
        and a["tech_score"] >= min_score
    ]
    st.markdown(
        f'<p style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;'
        f'color:#5a5855;margin-bottom:14px;">'
        f"Showing {len(filtered)} of {len(articles)} articles</p>",
        unsafe_allow_html=True,
    )
    for a in filtered:
        color = topic_color(a["topic"])
        pct = min(100, int(a["tech_score"] * 100))
        st.markdown(
            f'<div class="article-row">'
            f'<div class="article-row-title">'
            f'<span style="font-family:IBM Plex Mono,monospace;font-size:0.68rem;'
            f'color:#5a5855;margin-right:10px;">#{a["rank"]:02d}</span>'
            f'<a href="{a["url"]}" target="_blank">{a["title"]}</a>'
            f"</div>"
            f'<div class="article-row-meta">'
            f'<span class="topic-tag" style="color:{color};border-color:{color};">'
            f'{a["topic"]}</span>'
            f'<span>{a["source"]}</span>'
            f'<span>{fmt_date(a["published_at"])}</span>'
            f'<span style="margin-left:auto;font-weight:600;color:#1a1a1a;">'
            f'{a["tech_score"]:.4f}</span>'
            f"</div>"
            f'<div class="article-snippet">{a["content_snippet"]}</div>'
            f'<div class="score-track">'
            f'<div class="score-fill" style="width:{pct}%;"></div>'
            f"</div></div>",
            unsafe_allow_html=True,
        )


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    try:
        health = requests.get(f"{API_BASE}/health", timeout=3).json()
        if not health.get("ready"):
            st.info("API is starting up. Please wait...")
            if not wait_for_api():
                st.error("API did not become ready in time. Please refresh.")
                st.stop()
            st.rerun()
    except requests.exceptions.ConnectionError:
        st.error(f"Cannot connect to API at `{API_BASE}`")
        if st.button("Retry"):
            st.rerun()
        st.stop()

    report = fetch_report()
    render_sidebar(report)

    if report is None:
        render_empty_state()
        return

    render_header(report)
    render_export_bar(report)
    st.divider()
    render_summary(report["executive_summary"])
    st.divider()
    render_keywords_topics(report)
    st.divider()
    render_timeline(report["daily_counts"])
    st.divider()
    render_clusters(report["clusters"])
    st.divider()
    render_highlights(report["highlighted_articles"])


main()