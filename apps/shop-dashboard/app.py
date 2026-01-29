import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import time
import os

# --- Configurations ---
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "app")
DB_PORT = os.getenv("DB_PORT", "5432")

st.set_page_config(
    page_title="Shopping Analytics",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #1E1E1E;
        border: 1px solid #333;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        color: white;
    }
    .stMetric label { color: #888 !important; }
    .stMetric div { color: #fff !important; }
</style>
""", unsafe_allow_html=True)

# --- Database Connection ---
@st.cache_resource
def get_db_connection():
    db_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(db_url)

engine = get_db_connection()

# --- Data Loading Functions ---
def get_realtime_metrics():
    try:
        # Fetch key-value metrics
        df = pd.read_sql("SELECT * FROM shop_realtime_metrics", engine)
        metrics = {row['metric_name']: row['metric_value'] for _, row in df.iterrows()}
        return metrics
    except:
        return {}

def get_hourly_sales():
    try:
        return pd.read_sql("SELECT * FROM shop_hourly_sales WHERE window_start >= NOW() - INTERVAL '24 HOURS' ORDER BY window_start", engine)
    except:
        return pd.DataFrame()

def get_funnel_stats():
    try:
        # Get latest window funnel
        return pd.read_sql("SELECT * FROM shop_funnel_stats ORDER BY window_start DESC LIMIT 1", engine)
    except:
        return pd.DataFrame()

def get_brand_stats():
    try:
        return pd.read_sql("SELECT * FROM shop_brand_stats WHERE window_start >= NOW() - INTERVAL '1 HOUR' ORDER BY total_revenue DESC LIMIT 5", engine)
    except:
        return pd.DataFrame()

# --- Main Layout ---
st.title("🛍️ Shop Real-time Analytics")
st.caption("Live Data from Spark Structured Streaming & Kafka")

# Auto-refresh loop placeholder (Streamlit usually handles this via st.empty or rerun)
if st.button("Refresh Data 🔄"):
    st.rerun()

# 1. Real-time KPIs
metrics = get_realtime_metrics()
col1, col2, col3, col4 = st.columns(4)

with col1:
    val = int(metrics.get('active_users_5m', 0))
    st.metric("Active Users (5m)", f"{val:,}", delta="Live")

with col2:
    val = metrics.get('total_revenue_today', 0)
    st.metric("Revenue (Today)", f"${val:,.0f}")

with col3:
    val = int(metrics.get('total_orders_today', 0))
    st.metric("Orders (Today)", f"{val:,}")

with col4:
    # Calculated Conversion Rate
    funnel = get_funnel_stats()
    if not funnel.empty:
        cr = funnel.iloc[0]['conversion_rate']
        st.metric("Conversion Rate", f"{cr:.1f}%")
    else:
        st.metric("Conversion Rate", "0.0%")

st.divider()

# 2. Charts Row 1
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("Revenue Trend by Category")
    sales_df = get_hourly_sales()
    if not sales_df.empty:
        fig = px.bar(sales_df, x="window_start", y="total_revenue", color="category", 
                     title="Hourly Revenue Stack", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Waiting for sales data...")

with c2:
    st.subheader("Session Funnel (Last 1h)")
    if not funnel.empty:
        row = funnel.iloc[0]
        data = dict(
            number=[row['view_count'], row['cart_count'], row['purchase_count']],
            stage=["View", "Add to Cart", "Purchase"]
        )
        fig = px.funnel(data, x='number', y='stage', title="Conversion Funnel", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Waiting for funnel data...")

# 3. Charts Row 2
c3, c4 = st.columns(2)

with c3:
    st.subheader("Top 5 Brands (Revenue)")
    brand_df = get_brand_stats()
    if not brand_df.empty:
        fig = px.pie(brand_df, values='total_revenue', names='brand_name', 
                     title="Brand Market Share", hole=0.4, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Waiting for brand data...")

with c4:
    st.subheader("Raw Data Feed (Latest 5)")
    # Optional: Direct query to log table for debugging
    try:
        logs = pd.read_sql("SELECT * FROM shop_realtime_metrics_log ORDER BY last_updated DESC LIMIT 5", engine)
        st.dataframe(logs, use_container_width=True)
    except:
        st.info("No logs yet")
