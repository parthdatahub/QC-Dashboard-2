# app.py — Simple QC Dashboard for Ticket Audit (EPIC 2) — compatible with both column namings
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Ticket Quality Dashboard - EPIC 2", layout="wide")

st.markdown("""
<style>
body {font-family: "Segoe UI", sans-serif;}
.card {background:#ffffff;border-radius:10px;padding:18px;box-shadow:0 4px 10px rgba(0,0,0,0.08);text-align:center;}
.card h2 {margin:0;font-size:26px;color:#0078D7;}
.card p {margin:5px 0 0;color:#555;font-size:14px;}
.section-title {font-size:20px;font-weight:600;color:#444;margin-top:25px;}
</style>
""", unsafe_allow_html=True)

# ---------- Load ----------
try:
    df = pd.read_csv("data/processed_tickets.csv")
except FileNotFoundError:
    st.error("⚠️ File not found: data/processed_tickets.csv\n\nRun raw_load.py then scoring_logic.py first.")
    st.stop()

st.title("🎯 Ticket Quality Dashboard — EPIC 2 (Automated Scoring)")
st.caption(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Source: Automated QC Scoring (0–5 scale)")

# ---------- Column compatibility (map to your old names if needed) ----------
# agent_name fallback
if "agent_name" not in df.columns and "assigned_to" in df.columns:
    df["agent_name"] = df["assigned_to"]

# ensure assignment_group exists
if "assignment_group" not in df.columns:
    df["assignment_group"] = df.get("group", df.get("resolver_group", "N/A"))

# make sure resolution/work notes exist for detail pane
for c in ["resolution_notes", "work_notes"]:
    if c not in df.columns:
        df[c] = ""

# QC column name compatibility map (my scoring -> your old labels)
compat_map = {
    "qc_category": "qc_category",
    "qc_sub_cat": "qc_sub_cat",
    "qc_read_prev": "qc_read_prev_comments",
    "qc_routing": "qc_correct_routing",
    "qc_ownership": "qc_ownership",
    "qc_timely": "qc_timely_communication",
    "qc_priority": "qc_priority",
    "qc_email_format": "qc_email_kba_format",
    "qc_teams": "qc_teams_transcription",
    "qc_screenshot": "qc_screenshot_attached",
    "qc_doc_share": "qc_document_shared_location",
    "qc_compliance": "qc_compliance",
    "qc_client_notes": "qc_client_notes",
}
# if target column missing but source exists, create it
for src, tgt in compat_map.items():
    if tgt not in df.columns and src in df.columns:
        df[tgt] = df[src]

# ---------- Checkpoints (your labels) ----------
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
    "qc_client_notes": "Client Notes & Confirmation",
}

qc_cols = [c for c in checkpoints.keys() if c in df.columns]
if not qc_cols:
    st.warning("No QC checkpoint columns found. Expected columns like 'qc_category', 'qc_email_kba_format', etc.")
    st.stop()

# add totals if present/missing
if "qc_total_65" not in df.columns:
    df["qc_total_65"] = df[qc_cols].sum(axis=1)
if "qc_percent" in df.columns:
    df["qc_percent_100"] = df["qc_percent"]
elif "qc_percent_100" not in df.columns:
    df["qc_percent_100"] = (df["qc_total_65"] / 65 * 100).round(1)

# ---------- Filters ----------
with st.sidebar:
    st.image("assets/logo_placeholder.png", width=180)
    st.markdown("### 🔍 Filters")
    grp_opts = sorted(df['assignment_group'].dropna().unique())
    agent_opts = sorted(df['agent_name'].dropna().unique())
    grp = st.multiselect("Assignment Group", grp_opts)
    agent = st.multiselect("Agent Name", agent_opts)
    st.markdown("---")

filtered = df.copy()
if grp:
    filtered = filtered[filtered['assignment_group'].isin(grp)]
if agent:
    filtered = filtered[filtered['agent_name'].isin(agent)]

# ---------- KPI Cards ----------
st.markdown("## 📊 Overall Checkpoint Averages (Score 0–5)")
cols = st.columns(4)
for i, col in enumerate(qc_cols):
    avg = round(filtered[col].mean(), 2) if len(filtered) else 0.0
    with cols[i % 4]:
        st.markdown(f"<div class='card'><h2>{avg}</h2><p>{checkpoints[col]}</p></div>", unsafe_allow_html=True)
    if (i + 1) % 4 == 0:
        st.markdown("<br>", unsafe_allow_html=True)

# ---------- Ticket Explorer ----------
st.markdown("## 🧾 Ticket Explorer")
st.caption("Each ticket shows automated QC scores (0–5).")
show_cols = ["number", "agent_name", "assignment_group", "short_description"] + qc_cols + ["qc_total_65", "qc_percent_100"]
existing = [c for c in show_cols if c in filtered.columns]
st.dataframe(filtered[existing].fillna(0).sort_values("number", ascending=False), use_container_width=True)

# ---------- Agent Summary ----------
st.markdown("## 👤 Agent Performance Summary")
if "agent_name" in filtered.columns and len(filtered):
    agent_summary = (
        filtered.groupby("agent_name")[qc_cols]
        .mean().reset_index().round(2).sort_values("agent_name")
    )
    st.dataframe(agent_summary, use_container_width=True)
else:
    st.info("No 'agent_name' column found in data.")

# ---------- Detailed Ticket Report Card ----------
st.markdown("## 🔎 Individual Ticket Report Card")
ticket_list = sorted(filtered["number"].dropna().unique()) if "number" in filtered.columns else []
selected_ticket = st.selectbox("Select Ticket Number:", ticket_list)
if selected_ticket:
    row = filtered[filtered["number"] == selected_ticket].iloc[0]
    st.markdown(f"### 🎫 Ticket: `{row.get('number','')}` — {row.get('short_description','')}")
    st.write(f"**Agent:** {row.get('agent_name','N/A')}  |  **Group:** {row.get('assignment_group','N/A')}")
    st.markdown("---")

    left, right = st.columns(2)
    for i, col in enumerate(qc_cols):
        score = int(row[col]) if pd.notna(row[col]) else 0
        label = checkpoints[col]
        (left if i % 2 == 0 else right).markdown(f"**{label}:** {score}")

    st.markdown("---")
    st.markdown("**Resolution Notes:**")
    st.text(row.get("resolution_notes", ""))
    st.markdown("**Work Notes:**")
    st.text(row.get("work_notes", ""))

# ---------- Export ----------
st.markdown("## 📤 Export QC Report")
st.download_button(
    label="Download Processed QC Report (CSV)",
    data=filtered[existing].to_csv(index=False).encode("utf-8"),
    file_name="QC_Report.csv",
    mime="text/csv"
)

st.markdown("---")
st.caption("✅ Automated QC — 13 checkpoints (0–5). Fully rule-based with email/3-strike validation.")
