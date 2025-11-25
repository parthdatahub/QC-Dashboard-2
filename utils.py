# utils.py
import numpy as np

def compute_kpis(df):
    kpis = {}
    kpis['Closure Note Completeness'] = (df['clarity_score_auto'] >= 3).mean() * 100 if 'clarity_score_auto' in df.columns else np.nan
    kpis['Correct Resolution Code'] = (df['accuracy_score_auto'] >= 4).mean() * 100 if 'accuracy_score_auto' in df.columns else np.nan
    kpis['SLA Compliance'] = df['sla_met'].mean() * 100 if 'sla_met' in df.columns else np.nan
    kpis['Reopen Rate'] = (df['reopen_count'] > 0).mean() * 100 if 'reopen_count' in df.columns else np.nan
    kpis['Median MTTR (hrs)'] = df['mttr_hours'].median() if 'mttr_hours' in df.columns else np.nan
    kpis['KB Linkage'] = df['kb_linked'].mean() * 100 if 'kb_linked' in df.columns else np.nan
    return kpis

def generate_recommendation(row):
    tqi = row.get('ticket_quality_index_auto') or 0
    if tqi >= 70:
        return "✅ Ticket meets quality standards."
    msgs = []
    if row.get('clarity_score_auto',0) < 3:
        msgs.append("Improve closure note clarity.")
    if row.get('completeness_score_auto',0) < 3:
        msgs.append("Add detailed steps & resolution.")
    if row.get('professionalism_score_auto2',0) < 3:
        msgs.append("Use professional tone & formatting.")
    if not row.get('has_attachment', False):
        msgs.append("Attach screenshots or evidence.")
    return "⚠️ " + " ".join(msgs) if msgs else "Needs improvement."
