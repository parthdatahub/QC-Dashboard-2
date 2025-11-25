# generate_sample_data.py
from pathlib import Path
import pandas as pd, random
from datetime import datetime, timedelta

root = Path("data")
root.mkdir(exist_ok=True)

agents = ["Sayeed Ahmad","Jabilo Jose","Damian Rochowski","Don Goodliffe","Luke Wilson","David Loo","Beth Anglin","Fred Luddy"]
assignment_groups = ["KD-L1-ServiceDesk","IBM-APP-SUPPORT-MS","KD-DESKSIDE-XX-CTS15","Service Desk","Network","Hardware"]
categories = ["Application and Software","MS Office 365","Hardware","Network","Inquiry / Help","Database"]
subcats = ["Functional Issue","Outlook Issue","VPN","Disk Issue","Inquiry / Help","Performance"]
priorities = ["P1 - Critical","P2 - High","P3 - Medium","P4 - Low","P5 - Planning"]
close_codes = ["Resolved","Closed/Resolved by Caller","Corrective Action Performed","Solved (Permanently)","Canceled"]

def rand_date(start, end):
    delta = end - start
    sec = random.randrange(int(delta.total_seconds()))
    return start + timedelta(seconds=sec)

start = datetime(2023,1,1)
end = datetime(2025,9,1)

rows = []
for i in range(50):
    num = f"INC{1000000 + i}"
    opened = rand_date(start, end)
    resolved = opened + timedelta(hours=random.randint(1,240))
    closed = resolved + timedelta(hours=random.randint(0,48))
    agent = random.choice(agents)
    group = random.choice(assignment_groups)
    cat = random.choice(categories)
    sub = random.choice(subcats)
    priority = random.choice(priorities)
    if random.random() < 0.5:
        res_notes = f"Problem: {sub} reported. Steps: Performed diagnostic, restarted service. Resolution: Verified with user. KB: KB{random.randint(100,999)}"
    else:
        res_notes = random.choice(["Fixed","Resolved by restart","Closed before close notes were mandatory","Recreated profile and fixed issue","User confirmed."])
    work_notes = f"{opened.strftime('%Y-%m-%d %H:%M:%S')} - {agent} (Work notes)\n{res_notes}\nAttachment: screenshot.png" if random.random() < 0.6 else f"{opened.strftime('%Y-%m-%d %H:%M:%S')} - {agent} (Work notes)\n{res_notes}"
    close_code = random.choice(close_codes)
    reopen_count = 0 if random.random() < 0.85 else random.randint(1,3)
    reassignment_count = 0 if random.random() < 0.7 else random.randint(1,5)
    rows.append({
        "number": num,
        "opened": opened.strftime("%Y-%m-%d %H:%M:%S"),
        "short_description": f"{cat} - {sub} issue for user",
        "affected_user": "Karunagaran Kothandaraman",
        "mobile_phone": "+91 9941437413",
        "priority": priority,
        "configuration_item": "SC"+str(random.randint(1000,9999)),
        "location": "IN.TN.Chennai.1.Zenith Building",
        "category": cat,
        "state": "Closed",
        "assignment_group": group,
        "assigned_to": agent,
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_by": "system",
        "work_notes": work_notes,
        "WSP or Wood User": "Wood",
        "timeline": "",
        "subcategory": sub,
        "resolution_notes": res_notes,
        "resolution_code": close_code,
        "Parent Incident": "",
        "Comments and Work notes": work_notes,
        "Comments": "",
        "attachments": "screenshot.png" if "Attachment" in work_notes else "",
        "reopen_count": reopen_count,
        "reassignment_count": reassignment_count
    })

df50 = pd.DataFrame(rows)
df50.to_excel(root / "raw_export.xlsx", index=False)
print("Created data/raw_export.xlsx with 50 rows")
