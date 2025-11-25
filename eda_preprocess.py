#!/usr/bin/env python3
"""
EDA + Preprocessing with automatic QC checkpoint scoring (0-5).
Usage:
    python eda_preprocess.py
    python eda_preprocess.py --input data/raw_export.xlsx --output data/processed_tickets.csv
"""
import argparse, pandas as pd, numpy as np, re
from pathlib import Path
from datetime import timedelta

# --- Patterns / keywords
KEYWORD_STEPS = ['step','steps','restart','restarted','reboot','reinstalled','applied','rollback']
KEYWORD_CONFIRMED = ['confirm','confirmed','user confirmed','validated','verified by user','user confirmed']
TIMESTAMP_REGEX = r'\b\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\b|\b\d{1,2}:\d{2}\s*(AM|PM|am|pm)?\b'
KB_REGEX = r'\bKB\d{3,}|\bKB\b|confluence|knowledge base|kb00|kb0'
IMG_EXT_REGEX = r'\.(png|jpg|jpeg|bmp|gif)\b'
ATTACHMENT_WORDS = ['attachment:','attached:','attachment','file:','screenshot']

# --- helpers
def text_stats(text):
    s = str(text or "")
    chars = len(s); words = len(s.split()); sentences = max(1, s.count('.')+s.count('!')+s.count('?'))
    return chars, words, sentences

def contains_any(text, keywords):
    t = str(text or "").lower()
    return any(k in t for k in keywords)

def find_timestamp(text):
    return bool(re.search(TIMESTAMP_REGEX, str(text or ""), flags=re.IGNORECASE))

def find_kb(text):
    return bool(re.search(KB_REGEX, str(text or ""), flags=re.IGNORECASE))

def find_image_attachment(text):
    t = str(text or "").lower()
    if any(w in t for w in ATTACHMENT_WORDS):
        return True
    if re.search(IMG_EXT_REGEX, t):
        return True
    return False

def compute_mttr(opened, resolved, closed):
    try:
        op = pd.to_datetime(opened) if pd.notna(opened) else None
        res = pd.to_datetime(resolved) if pd.notna(resolved) else None
        clo = pd.to_datetime(closed) if pd.notna(closed) else None
        end = res if (res is not None and (op is None or res >= op)) else clo
        if op is None or end is None:
            return np.nan
        return (end - op).total_seconds() / 3600.0
    except:
        return np.nan

# --- scoring helpers: return integer 0..5
def score_presence_flag(flag):
    # boolean-ish flag -> 5 if True else 0
    return 5 if flag else 0

def score_yes_maybe(flag_strong, flag_weak):
    # strong evidence ->5, weak evidence->3, none->0
    if flag_strong:
        return 5
    if flag_weak:
        return 3
    return 0

def score_reassignment(reassign_count):
    try:
        n = int(reassign_count)
    except:
        return 3
    if n == 0:
        return 5
    if n <= 2:
        return 3
    return 0

def score_ownership(assigned_to, reassignment_count):
    if pd.isna(assigned_to) or str(assigned_to).strip()=="":
        return 0
    if int(reassignment_count) == 0:
        return 5
    if int(reassignment_count) <= 2:
        return 3
    return 2

def score_timely(opened, first_update_text):
    # simple: if first update text timestamp within 8 hours ->5, within 24 ->3, else 0
    try:
        op = pd.to_datetime(opened)
    except:
        return 3
    if pd.isna(first_update_text) or first_update_text=="":
        return 0
    # find earliest timestamp in work notes -> approximate
    m = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', str(first_update_text))
    if m:
        try:
            t = pd.to_datetime(m.group(1))
            delta = t - op
            hours = delta.total_seconds()/3600.0
            if hours <= 8: return 5
            if hours <= 24: return 3
            return 0
        except:
            return 3
    return 3

def score_priority_consistency(priority, mttr_hours):
    # If priority high and mttr small -> 5 ; if mismatch -> 3 ; missing ->0
    if pd.isna(priority) or str(priority).strip()=="":
        return 0
    try:
        mttr = float(mttr_hours) if not pd.isna(mttr_hours) else None
    except:
        mttr = None
    p = str(priority).lower()
    if "critical" in p or "p1" in p.lower():
        if mttr is not None and mttr <= 4: return 5
        return 3
    if "high" in p or "p2" in p.lower():
        if mttr is not None and mttr <= 8: return 5
        return 3
    return 5 if mttr is None or mttr >= 4 else 4

def score_email_format(text):
    # presence of typical polite email format or KB or template words
    t = str(text or "").lower()
    if any(w in t for w in ["dear ", "regards", "please refer", "please find", "kind regards"]): return 5
    if find_kb(text): return 5
    if len(t) > 100: return 3
    return 0

def score_teams_transcription(text):
    t = str(text or "").lower()
    if "teams" in t or "teams chat" in t or "microsoft teams" in t: return 5
    if find_timestamp(text) and ("confirmed" in t or "user confirmed" in t): return 5
    return 0

def score_attachment_presence(work_notes, attachments_col):
    if find_image_attachment(work_notes): return 5
    if pd.notna(attachments_col) and str(attachments_col).strip()!="":
        return 5
    return 0

def score_document_sharing(text):
    t = str(text or "").lower()
    if any(x in t for x in ["sharepoint","confluence","drive.google","s3.","\\share\\","\\\\"]): return 5
    if "http" in t and ("confluence" in t or "kb" in t): return 5
    return 0

def score_compliance(text, mttr_hours, unsupported_apps=None):
    # if profanity => 0; if mentions non-supported app => 0; if SLA missed reduce
    t = str(text or "").lower()
    profanity = ["idiot","stupid","fuck","shit","bastard"]  # example — extend per policy
    if any(p in t for p in profanity): return 0
    if unsupported_apps:
        for a in unsupported_apps:
            if a.lower() in t: return 0
    if mttr_hours and not pd.isna(mttr_hours) and float(mttr_hours) > 72:
        return 2
    return 5

def score_client_notes(text):
    t = str(text or "").lower()
    if any(w in t for w in ["user confirmed","confirmed by","user said","client confirmed","client said"]): return 5
    if "thanks" in t or "thank you" in t: return 4
    return 0

# --- Main preprocess
def preprocess(df):
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    # safe-get columns
    def getcol(*candidates):
        for c in candidates:
            if c in df.columns: return df[c]
        return pd.Series([pd.NA]*len(df))

    # unify some names
    resolution_notes = getcol('close_notes','resolution_notes','resolution notes','resolution')
    work_notes = getcol('work notes','work_notes','Comments and Work notes','comments')
    attachments = getcol('attachments','attachment','attachments_list')
    opened = getcol('opened','opened_at','sys_created_on')

    # output frame
    proc = pd.DataFrame()
    proc['number'] = getcol('number','ticket number','Ticket number').astype(str)
    proc['agent_name'] = getcol('assigned_to','assigned to')
    proc['assignment_group'] = getcol('assignment_group')
    proc['short_description'] = getcol('short_description','short description')
    proc['priority'] = getcol('priority')
    proc['category'] = getcol('category')
    proc['subcategory'] = getcol('subcategory')
    proc['opened_at'] = opened
    proc['resolved_at'] = getcol('resolved_at','resolved_at')
    proc['closed_at'] = getcol('closed_at','closed_at')
    proc['close_code'] = getcol('close_code','resolution_code','resolution code')
    proc['resolution_notes'] = resolution_notes.fillna("").astype(str)
    proc['work_notes'] = work_notes.fillna("").astype(str)
    proc['attachments'] = attachments.fillna("").astype(str)
    proc['reopen_count'] = pd.to_numeric(getcol('reopen_count','reopen_count'), errors='coerce').fillna(0).astype('Int64')
    proc['reassignment_count'] = pd.to_numeric(getcol('reassignment_count','reassignment_count'), errors='coerce').fillna(0).astype('Int64')

    # text metrics
    proc['res_chars'],proc['res_words'],proc['res_sentences'] = zip(*proc['resolution_notes'].map(text_stats))
    proc['work_chars'],proc['work_words'],proc['work_sentences'] = zip(*proc['work_notes'].map(text_stats))
    proc['mttr_hours'] = proc.apply(lambda r: compute_mttr(r['opened_at'], r['resolved_at'], r['closed_at']), axis=1)

    # derived boolean flags
    proc['has_steps_keyword'] = proc['resolution_notes'].apply(lambda t: contains_any(t, KEYWORD_STEPS))
    proc['has_confirm_keyword'] = proc['resolution_notes'].apply(lambda t: contains_any(t, KEYWORD_CONFIRMED))
    proc['has_kb_keyword'] = proc['resolution_notes'].apply(find_kb)
    proc['has_timestamp'] = proc['resolution_notes'].apply(find_timestamp) | proc['work_notes'].apply(find_timestamp)
    proc['has_attachment'] = proc['work_notes'].apply(find_image_attachment) | proc['attachments'].str.strip().ne("")

    # --- Auto QC checkpoint scoring (0..5)
    # keys matching your requested checkpoint list
    proc['qc_category'] = proc.apply(lambda r: 5 if (pd.notna(r['category']) and (str(r['category']).lower() in str(r['resolution_notes']).lower())) else (3 if pd.notna(r['category']) else 0), axis=1)
    proc['qc_sub_cat'] = proc.apply(lambda r: 5 if (pd.notna(r['subcategory']) and (str(r['subcategory']).lower() in str(r['resolution_notes']).lower())) else (3 if pd.notna(r['subcategory']) else 0), axis=1)
    proc['qc_read_prev_comments'] = proc.apply(lambda r: score_yes_maybe(find_timestamp(r['work_notes']) or ("deployment" in str(r['work_notes']).lower()), (r['work_chars']>0)), axis=1)
    proc['qc_correct_routing'] = proc.apply(lambda r: score_reassignment(r['reassignment_count']), axis=1)
    proc['qc_ownership'] = proc.apply(lambda r: score_ownership(r['agent_name'], r['reassignment_count']), axis=1)
    proc['qc_timely_communication'] = proc.apply(lambda r: score_timely(r['opened_at'], r['work_notes']), axis=1)
    proc['qc_priority'] = proc.apply(lambda r: score_priority_consistency(r['priority'], r['mttr_hours']), axis=1)
    proc['qc_email_kba_format'] = proc.apply(lambda r: score_email_format(r['resolution_notes'] + " " + r['work_notes']), axis=1)
    proc['qc_teams_transcription'] = proc.apply(lambda r: score_teams_transcription(r['work_notes'] + " " + r['resolution_notes']), axis=1)
    proc['qc_screenshot_attached'] = proc.apply(lambda r: score_attachment_presence(r['work_notes'], r['attachments']), axis=1)
    proc['qc_document_shared_location'] = proc.apply(lambda r: score_document_sharing(r['resolution_notes'] + " " + r['work_notes']), axis=1)
    proc['qc_compliance'] = proc.apply(lambda r: score_compliance(r['resolution_notes'] + " " + r['work_notes'], r['mttr_hours'], unsupported_apps=[]), axis=1)
    proc['qc_client_notes'] = proc.apply(lambda r: score_client_notes(r['work_notes'] + " " + r['resolution_notes']), axis=1)

    # ensure 0..5 ints
    for c in [c for c in proc.columns if c.startswith('qc_')]:
        proc[c] = proc[c].fillna(0).astype(int).clip(0,5)

    # also keep earlier auto TQI columns (if you want both)
    def clarity_from_chars(n):
        if pd.isna(n): return 1
        if n >= 200: return 5
        if n >= 100: return 3
        return 1
    proc['clarity_score_auto'] = proc['res_chars'].apply(clarity_from_chars)
    proc['completeness_score_auto'] = proc.apply(lambda r: 5 if (r['has_steps_keyword'] and r['has_confirm_keyword']) else (3 if r['has_steps_keyword'] else 1), axis=1)
    proc['accuracy_score_auto'] = proc.apply(lambda r: 4 if (pd.notna(r['category']) and (str(r['category']).lower() in str(r['resolution_notes']).lower())) else 2, axis=1)
    proc['actionability_score_auto'] = proc['has_steps_keyword'].apply(lambda x: 4 if x else 2)
    proc['professionalism_score_auto2'] = proc['resolution_notes'].apply(lambda t: 5 if str(t).strip() and str(t).strip()[0].isupper() else 3)
    proc['ticket_quality_index_auto'] = ((proc['clarity_score_auto']*0.2 + proc['completeness_score_auto']*0.3 + proc['professionalism_score_auto2']*0.1 + proc['accuracy_score_auto']*0.2 + proc['actionability_score_auto']*0.2) * 20).round(0).astype('Int64')

    # final output columns
    out_cols = ['number','agent_name','assignment_group','short_description','priority','category','subcategory','opened_at','resolved_at','closed_at','mttr_hours','close_code','resolution_notes','work_notes','res_chars','res_words','res_sentences','has_steps_keyword','has_confirm_keyword','has_kb_keyword','has_timestamp','has_attachment','kb_linked','reopen_count','reassignment_count','clarity_score_auto','completeness_score_auto','professionalism_score_auto2','accuracy_score_auto','actionability_score_auto','ticket_quality_index_auto']
    out_cols += sorted([c for c in proc.columns if c.startswith('qc_')])
    for c in out_cols:
        if c not in proc.columns:
            proc[c] = pd.NA
    return proc[out_cols]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input','-i', default='data/raw_export.xlsx')
    parser.add_argument('--output','-o', default='data/processed_tickets.csv')
    args = parser.parse_args()

    inp = Path(args.input)
    if not inp.exists():
        raise SystemExit(f"Input file not found: {inp} (place your ServiceNow export here)")

    if inp.suffix.lower() in ('.xlsx', '.xls'):
        df = pd.read_excel(inp, dtype=str)
    else:
        df = pd.read_csv(inp, dtype=str)

    proc = preprocess(df)
    outp = Path(args.output)
    outp.parent.mkdir(parents=True, exist_ok=True)
    proc.to_csv(outp, index=False)
    print(f"✅ Processed {len(proc)} rows -> {outp}")

if __name__ == '__main__':
    main()
