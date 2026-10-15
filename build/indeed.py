"""Download the Indeed Hiring Lab data and average it by month into build/data.json.

Run from the project folder:  python3 build/indeed.py
Free: both sources are public CSVs on GitHub (CC BY 4.0).
"""
import collections
import csv
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent.parent
AI_URL = "https://raw.githubusercontent.com/hiring-lab/ai-tracker/main/AI_posting.csv"
JPT_URL = "https://raw.githubusercontent.com/hiring-lab/job_postings_tracker/master/{cc}/aggregate_job_postings_{cc}.csv"
AI_COUNTRIES = ["GB", "IE", "DE", "FR", "IT", "NL"]  # the AI tracker has no Spain
IDX_COUNTRIES = ["ES", "DE", "FR", "GB", "IE", "IT", "NL"]


def download(url, path):
    # curl, not urllib: the python.org build on this Mac has no CA certificates installed.
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-sS", "--fail", "-L", "-o", str(path), url], check=True, timeout=180)


def monthly_mean(rows):
    by_month = collections.defaultdict(list)
    for month, value in rows:
        by_month[month].append(value)
    return {k: sum(v) / len(v) for k, v in by_month.items()}


ai_csv = root / "data" / "AI_posting.csv"
download(AI_URL, ai_csv)
for cc in IDX_COUNTRIES:
    download(JPT_URL.format(cc=cc), root / "data" / "postings" / f"aggregate_job_postings_{cc}.csv")

rows = list(csv.DictReader(ai_csv.open()))
ai = {cc: monthly_mean((r["date"][:7], float(r["AI_share_postings"])) for r in rows if r["jobcountry"] == cc)
      for cc in AI_COUNTRIES}
months = sorted(ai["GB"])
out = {"months": months, "ai": {cc: [round(ai[cc][m], 2) for m in months] for cc in AI_COUNTRIES}}

idx = {}
for cc in IDX_COUNTRIES:
    f = root / "data" / "postings" / f"aggregate_job_postings_{cc}.csv"
    idx[cc] = {k: round(v, 1) for k, v in monthly_mean(
        (r["date"][:7], float(r["indeed_job_postings_index_SA"]))
        for r in csv.DictReader(f.open()) if r["variable"] == "total postings").items()}
out["idx"] = {cc: [idx[cc].get(m) for m in months] for cc in idx}
out["idxLatest"] = {cc: [max(idx[cc]), idx[cc][max(idx[cc])]] for cc in idx}

(root / "build" / "data.json").write_text(json.dumps(out, separators=(",", ":")))
print(f"data.json: {len(months)} months, {months[0]} to {months[-1]}")
