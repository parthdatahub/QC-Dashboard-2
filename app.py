# app.py — Simple QC Dashboard for Ticket Audit (EPIC 2)
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# ----------------- Page Setup -----------------
st.set_page_config(page_title="Ticket Quality Dashboard - EPIC 2", layout="wide")

st.markdown("""
<style>
body {font-family: "Segoe UI", sans-serif;}
.card {
    background: #ffffff;
    border-radius: 10px;
    padding: 18px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.08);
    text-align: center;
}
.card h2 {margin: 0; font-size: 26px; color: #0078D7;}
.card p {margin: 5px 0 0; color: #555; font-size: 14px;}
.section-title {font-size: 20px; font-weight: 600; color: #444; margin-top: 25px;}
</style>
""", unsafe_allow_html=True)

# ----------------- Load Data -----------------
try:
    df = pd.read_csv("data/processed_tickets.csv")
except FileNotFoundError:
    st.error("⚠️ File not found: data/processed_tickets.csv\n\nRun eda_preprocess.py first.")
    st.stop()

st.title("🎯 Ticket Quality Dashboard — EPIC 2 (Automated Scoring)")
st.caption(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Source: Automated QC Scoring (0–5 scale)")

# ----------------- Define Checkpoints -----------------
checkpoints = {
    "qc_category": "Category Understanding",
    "qc_sub_cat": "Subcategory Understanding",
    "qc_read_prev_comments": "Read Previous Comments / Deployment Notes",
    "qc_correct_routing": "Correct Process Followed (Routing)",
    "qc_ownership": "Ownership & Responsibility",
    "qc_timely_communication": "Timely Communication",
    "qc_priority": "Priority Validation",
    "qc_email_kba_format": "Email / KBA Format Guidelines",
    "qc_teams_transcription": "Teams Transcript / Confirmation",
    "qc_screenshot_attached": "Necessary Screenshot Attached",
    "qc_document_shared_location": "Document Sharing (Location)",
    "qc_compliance": "Compliance / SLA Adherence",
    "qc_client_notes": "Client Notes & Confirmation"
}

qc_cols = [c for c in df.columns if c.startswith("qc_") and c in checkpoints]

if not qc_cols:
    st.warning("No QC checkpoint columns found (columns starting with 'qc_'). Check your preprocessing script.")
    st.stop()

# ----------------- Filters -----------------
with st.sidebar:
    st.image("assets/logo_placeholder.png", width=180)
    st.markdown("### 🔍 Filters")
    grp = st.multiselect("Assignment Group", sorted(df['assignment_group'].dropna().unique()), default=None)
    agent = st.multiselect("Agent Name", sorted(df['agent_name'].dropna().unique()), default=None)
    st.markdown("---")

filtered = df.copy()
if grp:
    filtered = filtered[filtered['assignment_group'].isin(grp)]
if agent:
    filtered = filtered[filtered['agent_name'].isin(agent)]

# ----------------- KPI Cards -----------------
st.markdown("## 📊 Overall Checkpoint Averages (Score 0–5)")
cols = st.columns(4)
for i, col in enumerate(qc_cols):
    avg_score = round(filtered[col].mean(), 2)
    with cols[i % 4]:
        st.markdown(f"<div class='card'><h2>{avg_score}</h2><p>{checkpoints[col]}</p></div>", unsafe_allow_html=True)
    if (i+1) % 4 == 0:
        st.markdown("<br>", unsafe_allow_html=True)

# ----------------- Ticket Explorer -----------------
st.markdown("## 🧾 Ticket Explorer")
st.caption("Below table shows each ticket with automatically calculated QC scores (0–5).")

show_cols = ["number", "agent_name", "assignment_group", "short_description"] + qc_cols
st.dataframe(filtered[show_cols].fillna(0).sort_values("number", ascending=False), use_container_width=True)

# ----------------- Agent Summary -----------------
st.markdown("## 👤 Agent Performance Summary")
if "agent_name" in filtered.columns:
    agent_summary = (
        filtered.groupby("agent_name")[qc_cols]
        .mean()
        .reset_index()
        .round(2)
        .sort_values("agent_name")
    )
    st.dataframe(agent_summary, use_container_width=True)
else:
    st.info("No 'agent_name' column found in data.")

# ----------------- Detailed View -----------------
st.markdown("## 🔎 Individual Ticket Report Card")
selected_ticket = st.selectbox("Select Ticket Number:", sorted(filtered["number"].dropna().unique()))
if selected_ticket:
    ticket_row = filtered[filtered["number"] == selected_ticket].iloc[0]
    st.markdown(f"### 🎫 Ticket: `{ticket_row['number']}` — {ticket_row.get('short_description','')}")
    st.write(f"**Agent:** {ticket_row.get('agent_name','N/A')}  |  **Group:** {ticket_row.get('assignment_group','N/A')}")
    st.markdown("---")

    left, right = st.columns(2)
    for i, col in enumerate(qc_cols):
        score = int(ticket_row[col]) if not pd.isna(ticket_row[col]) else 0
        label = checkpoints[col]
        if i % 2 == 0:
            with left:
                st.markdown(f"**{label}:** {score}")
        else:
            with right:
                st.markdown(f"**{label}:** {score}")

    st.markdown("---")
    st.markdown("**Resolution Notes:**")
    st.text(ticket_row.get("resolution_notes", ""))
    st.markdown("**Work Notes:**")
    st.text(ticket_row.get("work_notes", ""))

# ----------------- Export -----------------
st.markdown("## 📤 Export QC Report")
st.download_button(
    label="Download Processed QC Report (CSV)",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="QC_Report.csv",
    mime="text/csv"
)

st.markdown("---")
st.caption("✅ This dashboard automatically evaluates ticket quality checkpoints (0–5) based on predefined rules — no manual input required.")
