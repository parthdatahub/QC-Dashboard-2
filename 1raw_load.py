# raw_load.py
# ---------------------------------------------------------
# PURPOSE:
#   ✔ Load real ServiceNow raw dataset (7Lakh+ rows)
#   ✔ Standardize column names
#   ✔ Basic cleaning + datetime fixes
#   ✔ Build helper columns needed for scoring logic
#   ✔ Save output as cleaned_intermediate.csv
#
# INPUT FILE:
#   data/tickets_raw.xlsx   (put your real SN data here)
#
# OUTPUT FILE:
#   data/cleaned_intermediate.csv
# ---------------------------------------------------------

import pandas as pd
import numpy as np
from pathlib import Path

RAW_FILE = "data/tickets_raw.xlsx"
OUT_FILE = "data/cleaned_intermediate.csv"
Path("data").mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# ✅ 1. Load raw file
# ---------------------------------------------------------
def load_raw():
    print("📂 Loading raw dataset...")
    return pd.read_excel(RAW_FILE)

# ---------------------------------------------------------
# ✅ 2. Normalize column names
# ---------------------------------------------------------
def normalize_columns(df):
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("/", "_")
        .str.replace("-", "_")
    )
    return df

# ---------------------------------------------------------
# ✅ 3. Clean text fields
# ---------------------------------------------------------
TEXT_COLS = [
    "short_description", "work_notes", "comments", "comments_and_work_notes", 
    "resolution_notes", "timeline"
]

def clean_text(df):
    for c in TEXT_COLS:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str)
    return df

# ---------------------------------------------------------
# ✅ 4. Fix date/time columns + derive MTTR
# ---------------------------------------------------------
def process_datetime(df):

    def to_dt(x):
        try: return pd.to_datetime(x)
        except: return pd.NaT

    date_cols = ["opened", "updated", "resolved_at", "closed_at"]

    for c in date_cols:
        if c in df.columns:
            df[c] = df[c].apply(to_dt)

    # MTTR = resolved_at - opened
    if "resolved_at" in df.columns and "opened" in df.columns:
        df["mttr_hours"] = (df["resolved_at"] - df["opened"]).dt.total_seconds() / 3600
    else:
        df["mttr_hours"] = np.nan

    # response time = updated - opened
    if "updated" in df.columns and "opened" in df.columns:
        df["response_time_hours"] = (df["updated"] - df["opened"]).dt.total_seconds() / 3600
    else:
        df["response_time_hours"] = np.nan

    return df

# ---------------------------------------------------------
# ✅ 5. Merge notes into a unified large text block
# ---------------------------------------------------------
def build_unified_notes(df):
    df["unified_text"] = (
        df.get("work_notes", "") + "\n" +
        df.get("resolution_notes", "") + "\n" +
        df.get("comments_and_work_notes", "") + "\n" +
        df.get("comments", "")
    )
    return df

# ---------------------------------------------------------
# ✅ MAIN PIPELINE
# ---------------------------------------------------------
def main():
    df = load_raw()
    df = normalize_columns(df)
    df = clean_text(df)
    df = process_datetime(df)
    df = build_unified_notes(df)

    df.to_csv(OUT_FILE, index=False)
    print("✅ Raw loading complete!")
    print(f"✅ Cleaned dataset → {OUT_FILE}")
    print(f"✅ Total rows: {len(df)}")

if __name__ == "__main__":
    main()
