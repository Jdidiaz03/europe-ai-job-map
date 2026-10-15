"""Snapshot of AI job postings on LinkedIn, one search per country, via Apify.

Run once a month from the project folder:  python3 build/fetch_linkedin.py
Saves data/linkedin/<YYYY-MM>/<CC>.json. The Apify token is read from the
macOS Keychain (service "apify-api"), never from a file.

Actor: meka.im/linkedin-jobs-scraper, $0.30 per 1,000 jobs.
7 countries x 700 jobs is about $1.50, inside Apify's free $5 a month.
"""
import datetime
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ACTOR = "meka.im~linkedin-jobs-scraper"
KEYWORDS = "artificial intelligence"
PER_COUNTRY = 700
MAX_USD_PER_RUN = 0.30
COUNTRIES = {"ES": "Spain", "IE": "Ireland", "GB": "United Kingdom", "DE": "Germany",
             "FR": "France", "IT": "Italy", "NL": "Netherlands"}
# Second search in the local language, where an English query misses many postings.
LOCAL = {"DE": "Künstliche Intelligenz", "FR": "intelligence artificielle", "IT": "intelligenza artificiale"}
KEEP = ["id", "link", "title", "companyName", "companyLinkedinUrl", "location", "postedAt",
        "seniorityLevel", "employmentType", "jobFunction", "industries", "salary",
        "applicantsCount", "descriptionText"]

TOKEN = subprocess.run(["security", "find-generic-password", "-s", "apify-api", "-w"],
                       capture_output=True, text=True, check=True).stdout.strip()
OUT = Path(__file__).resolve().parent.parent / "data" / "linkedin" / datetime.date.today().strftime("%Y-%m")


def api(method, url, body=None):
    # curl, not urllib: the python.org build on this Mac has no CA certificates installed.
    cmd = ["curl", "-sS", "--fail", "-X", method, f"https://api.apify.com/v2/{url}",
           "-H", f"Authorization: Bearer {TOKEN}", "-H", "Content-Type: application/json"]
    if body:
        cmd += ["-d", json.dumps(body)]
    return json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=180).stdout)


def snapshot(code, country, keywords=KEYWORDS, suffix=""):
    run = api("POST", f"acts/{ACTOR}/runs?maxTotalChargeUsd={MAX_USD_PER_RUN}", {
        "keywords": keywords, "location": country, "datePosted": "pastMonth",
        "limitPerSource": PER_COUNTRY, "scrapeCompany": False})["data"]
    while run["status"] in ("READY", "RUNNING"):
        time.sleep(15)
        run = api("GET", f"actor-runs/{run['id']}?waitForFinish=60")["data"]
    items = api("GET", f"datasets/{run['defaultDatasetId']}/items?clean=true&format=json")
    jobs = [{k: j.get(k) for k in KEEP} for j in items]
    (OUT / f"{code}{suffix}.json").write_text(json.dumps(jobs, ensure_ascii=False))
    cost = run.get("usageTotalUsd") or 0
    return f"{code}{suffix}: {run['status']}, {len(jobs)} jobs, ${cost:.3f}"


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    args = sys.argv[1:]
    only_local = "--local" in args
    codes = [a for a in args if a != "--local"] or list(COUNTRIES)
    jobs = [] if only_local else [(c, COUNTRIES[c], KEYWORDS, "") for c in codes]
    jobs += [(c, COUNTRIES[c], LOCAL[c], "-local") for c in codes if c in LOCAL]
    with ThreadPoolExecutor(max_workers=4) as pool:  # free plan allows 5 concurrent runs
        for line in pool.map(lambda j: snapshot(*j), jobs):
            print(line, flush=True)
