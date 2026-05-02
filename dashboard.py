# dashboard.py - Streamlit Dashboard (Alternative to Flask)
import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
import datetime
import os
import json
from config import Config

st.set_page_config(page_title="Trading Bot Dashboard", layout="wide", page_icon="📈")

st.title("📈 Trading Bot Dashboard")
st.markdown("---")

# Database connection
@st.cache_resource
def get_connection():
    conn = sqlite3.connect('trading_bot.db', check_same_thread=False)
    return conn

@st.cache_data(ttl=5)
def load_trades():
    try:
        conn = get_connection()
        df = pd.read_sql_query("SELECT * FROM trades ORDER BY trade_id DESC", conn)
        conn.close()
        return df if not df.empty else pd.DataFrame()
    except:
        return pd.DataFrame()

# Display metrics
trades_df = load_trades()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📊 Total Trades", len(trades_df))
with col2:
    total_pnl = trades_df['pnl'].sum() if not trades_df.empty else 0
    st.metric("💰 Total P&L", f"₹{total_pnl:,.2f}")
with col3:
    winning = len(trades_df[trades_df['pnl'] > 0]) if not trades_df.empty else 0
    win_rate = (winning / len(trades_df) * 100) if not trades_df.empty else 0
    st.metric("🏆 Win Rate", f"{win_rate:.1f}%")
with col4:
    st.metric("📋 Open Positions", 0)

st.markdown("---")

# Trades table
st.subheader("📋 Recent Trades")
if not trades_df.empty:
    st.dataframe(trades_df[['trade_id', 'symbol', 'entry_price', 'quantity', 'pnl', 'strategy']].head(20), use_container_width=True)
else:
    st.info("No trades yet")

# Run: streamlit run dashboard.py --server.address 0.0.0.0