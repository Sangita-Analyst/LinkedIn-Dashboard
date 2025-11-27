import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO
from datetime import datetime
import textwrap

st.set_page_config(layout="wide", page_title="LinkedIn Merits Dashboard", page_icon="🔎")

# ---------- Helper functions ----------
@st.cache_data
def read_file(uploaded_file):
    if uploaded_file is None:
        return pd.DataFrame()

    filename = uploaded_file.name.lower()
    try:
        if filename.endswith('.csv'):
            return pd.read_csv(uploaded_file)
        elif filename.endswith('.xls') or filename.endswith('.xlsx'):
            return pd.read_excel(uploaded_file)
        elif filename.endswith('.json'):
            return pd.read_json(uploaded_file)
        else:
            try:
                uploaded_file.seek(0)
                return pd.read_csv(uploaded_file)
            except:
                uploaded_file.seek(0)
                return pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Could not read file: {e}")
        return pd.DataFrame()


def fuzzy_col(df, candidates):
    cols = [c.lower() for c in df.columns]
    for cand in candidates:
        for i, col in enumerate(cols):
            if cand.lower() in col:
                return df.columns[i]
    return None


def detect_date_col(df):
    for col in df.columns:
        if np.issubdtype(df[col].dtype, np.datetime64):
            return col
    for name in ['date', 'posted_at', 'created_at', 'timestamp']:
        if name in [c.lower() for c in df.columns]:
            return df.columns[[c.lower() for c in df.columns].index(name)]
    for col in df.columns:
        try:
            pd.to_datetime(df[col])
            return col
        except:
            continue
    return None


def calculate_metrics(df):
    df = df.copy()

    impressions_col = fuzzy_col(df, ['impression', 'impressions', 'views'])
    likes_col = fuzzy_col(df, ['like', 'likes', 'reactions'])
    comments_col = fuzzy_col(df, ['comment', 'comments'])
    shares_col = fuzzy_col(df, ['share', 'shares'])
    clicks_col = fuzzy_col(df, ['click', 'clicks'])
    followers_col = fuzzy_col(df, ['follower', 'followers'])
    connections_col = fuzzy_col(df, ['connection', 'connections'])
    profile_views_col = fuzzy_col(df, ['profile_view', 'profile views'])
    search_appear_col = fuzzy_col(df, ['search_appear', 'search appearances'])
    video_views_col = fuzzy_col(df, ['video_view', 'video views'])
    video_complete_col = fuzzy_col(df, ['video_complete', 'video completed'])
    form_sub_col = fuzzy_col(df, ['form', 'form_submission', 'lead'])

    numeric_cols = [impressions_col, likes_col, comments_col, shares_col, clicks_col,
                    video_views_col, video_complete_col, form_sub_col]
    for c in numeric_cols:
        if c and c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    total_impressions = int(df[impressions_col].sum()) if impressions_col else 0
    total_likes = int(df[likes_col].sum()) if likes_col else 0
    total_comments = int(df[comments_col].sum()) if comments_col else 0
    total_shares = int(df[shares_col].sum()) if shares_col else 0
    total_clicks = int(df[clicks_col].sum()) if clicks_col else 0
    total_video_views = int(df[video_views_col].sum()) if video_views_col else 0
    total_video_completions = int(df[video_complete_col].sum()) if video_complete_col else 0
    total_forms = int(df[form_sub_col].sum()) if form_sub_col else 0

    total_engagements = total_likes + total_comments + total_shares + total_clicks

    engagement_rate = (total_engagements / total_impressions * 100) if total_impressions else 0
    ctr = (total_clicks / total_impressions * 100) if total_impressions else 0
    avg_likes = total_likes / len(df) if likes_col and len(df) else 0
    avg_comments = total_comments / len(df) if comments_col and len(df) else 0
    vid_rate = (total_video_completions / total_video_views * 100) if total_video_views else 0

    metrics = {
        'total_impressions': total_impressions,
        'total_engagements': total_engagements,
        'total_clicks': total_clicks,
        'total_forms': total_forms,
        'engagement_rate_pct': round(engagement_rate, 2),
        'ctr_pct': round(ctr, 2),
        'avg_likes': round(avg_likes, 2),
        'avg_comments': round(avg_comments, 2),
        'video_completion_rate_pct': round(vid_rate, 2),
        'detected': {
            'impressions': impressions_col,
            'likes': likes_col,
            'comments': comments_col,
            'shares': shares_col,
            'clicks': clicks_col,
            'form': form_sub_col,
            'video_views': video_views_col,
            'video_completions': video_complete_col
        }
    }

    return metrics, df


# ---------- App Layout ----------
st.sidebar.title("Upload File")
uploaded_file = st.sidebar.file_uploader("Upload Excel/CSV/JSON", type=["csv", "xls", "xlsx", "json"])

if uploaded_file is None:
    st.title("LinkedIn Dashboard App")
    st.write("Upload a file from the left sidebar to start.")
    st.stop()

# Load data
df = read_file(uploaded_file)
if df.empty:
    st.error("Could not read file. Please check format.")
    st.stop()

# Detect date column
date_col = detect_date_col(df)
if date_col:
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    min_d, max_d = df[date_col].min(), df[date_col].max()
    start, end = st.sidebar.date_input("Date Range", [min_d, max_d])
    df = df[(df[date_col] >= pd.to_datetime(start)) & (df[date_col] <= pd.to_datetime(end))]

# Calculate metrics
metrics, pdf = calculate_metrics(df)

# ---------- Summary Cards ----------
st.header("LinkedIn Summary")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Impressions", f"{metrics['total_impressions']:,}")
col2.metric("Engagements", f"{metrics['total_engagements']:,}", f"{metrics['engagement_rate_pct']}%")
col3.metric("Clicks", f"{metrics['total_clicks']:,}", f"{metrics['ctr_pct']}% CTR")
col4.metric("Leads", metrics['total_forms'])

col5, col6, col7 = st.columns(3)
col5.metric("Avg Likes", metrics['avg_likes'])
col6.metric("Avg Comments", metrics['avg_comments'])
col7.metric("Video Completion", f"{metrics['video_completion_rate_pct']}%")

# ---------- Charts ----------
st.subheader("Charts")
if date_col and metrics['detected']['impressions']:
    tdf = df.copy()
    tdf[date_col] = pd.to_datetime(tdf[date_col], errors='coerce')
    agg = tdf.groupby(tdf[date_col].dt.to_period('D'))[metrics['detected']['impressions']].sum().reset_index()
    agg[date_col] = agg[date_col].dt.to_timestamp()
    st.plotly_chart(px.line(agg, x=date_col, y=metrics['detected']['impressions'], title="Impressions Over Time", markers=True))

# ---------- Custom Chart Builder ----------
st.subheader("Custom Chart")
numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
x_col = st.selectbox("X-axis", df.columns)
y_col = st.selectbox("Y-axis", numeric_cols)
if x_col and y_col:
    st.plotly_chart(px.line(df, x=x_col, y=y_col, title=f"{y_col} vs {x_col}"))

# ---------- Export ----------
st.subheader("Export Processed Data")
if st.button("Download CSV"):
    buf = BytesIO()
    pdf.to_csv(buf, index=False)
    buf.seek(0)
    st.download_button("Download", buf, file_name="processed.csv", mime="text/csv")

st.write("---")
st.info("Upload any LinkedIn analytics Excel/CSV/JSON file and the dashboard auto-detects columns and builds KPIs + Charts.")