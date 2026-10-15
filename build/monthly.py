"""Monthly refresh: new LinkedIn snapshot, new Indeed data, rebuilt page.

Run from anywhere:  python3 build/monthly.py                 run now
                    python3 build/monthly.py --no-linkedin   Indeed only, costs nothing
                    python3 build/monthly.py --scheduled     what launchd runs every day at 09:00:
                      it only works from the 5th of the month (Apify's free credit resets
                      on the 4th) and only if this month's summary doesn't exist yet,
                      so a Mac that was off on the 5th catches up the next day.

It does NOT push to GitHub. The page text quotes numbers ("15.0%", "+89%"),
so a person checks the summary, updates the text, then publishes.
The summary goes to data/monthly/<YYYY-MM>.md and a macOS notification says it's ready.

Cost: Indeed is free. The LinkedIn snapshot is about $1.60 of Apify's free $5 a month.
It is skipped if this month's snapshot already exists or less than $3.10 of credit
is left (10 searches capped at $0.30 each, so one run can never cost more than $3.00).
"""
import datetime
import json
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
build = root / "build"
month = datetime.date.today().strftime("%Y-%m")
MIN_CREDIT_USD = 3.10


def run(script, *args):
    print(f"\n$ {script} {' '.join(args)}", flush=True)
    subprocess.run([sys.executable, str(build / script), *args], check=True, cwd=root)


def apify_credit_left():
    token = subprocess.run(["security", "find-generic-password", "-s", "apify-api", "-w"],
                           capture_output=True, text=True, check=True).stdout.strip()
    out = subprocess.run(["curl", "-sS", "--fail", "https://api.apify.com/v2/users/me/limits",
                          "-H", f"Authorization: Bearer {token}"],
                         capture_output=True, text=True, check=True, timeout=60).stdout
    d = json.loads(out)["data"]
    return d["limits"]["maxMonthlyUsageUsd"] - d["current"]["monthlyUsageUsd"]


def key_numbers():
    """The numbers the page text quotes, so old and new can be compared."""
    d = json.loads((build / "data.json").read_text())
    c = json.loads((build / "companies.json").read_text())
    m = d["months"]
    gpt, last = m.index("2022-11"), len(m) - 1
    k = {"Latest Indeed month": m[last]}
    for cc, v in d["ai"].items():
        chg = (v[last] * d["idx"][cc][last]) / (v[gpt] * d["idx"][cc][gpt]) - 1
        k[f"{cc} AI share"] = f"{v[last]:.1f}%"
        k[f"{cc} AI postings since Nov 2022"] = f"{chg:+.0%}"
    s = c["summary"]
    k["LinkedIn snapshot"] = c["snapshot"]
    k["Roles / employers"] = f"{s['roles']:,} / {s['employers']:,}"
    shares = {cc: x["consultingShare"] for cc, x in c["countries"].items()}
    k["Consulting share range"] = f"{min(shares.values()):.0%} to {max(shares.values()):.0%}"
    k["Business-facing (all)"] = f"{(s['roleType']['consulting'] + s['roleType']['business']) / s['roles']:.1%}"
    k["Junior titles (all)"] = f"{s['junior'] / s['roles']:.1%}"
    for cc, x in c["countries"].items():
        k[f"{cc} business-facing"] = f"{(x['roleType']['consulting'] + x['roleType']['business']) / x['roles']:.0%}"
    return k


def notify(text):
    subprocess.run(["osascript", "-e", f'display notification "{text}" with title "Europe AI Job Map"'])


def main():
    before = key_numbers()
    notes = []

    if "--no-linkedin" in sys.argv:
        notes.append("LinkedIn skipped (--no-linkedin).")
    elif (root / "data" / "linkedin" / month).exists():
        notes.append(f"LinkedIn skipped: data/linkedin/{month} already exists, so no credit was spent.")
    else:
        left = apify_credit_left()
        if left < MIN_CREDIT_USD:
            notes.append(f"LinkedIn skipped: only ${left:.2f} of Apify credit left this month.")
        else:
            run("fetch_linkedin.py")
            notes.append(f"LinkedIn snapshot {month} fetched (credit before: ${left:.2f}).")

    run("indeed.py")
    run("companies.py")
    run("build.py")

    after = key_numbers()
    rows = "\n".join(f"| {k} | {before.get(k, '')} | {v} |{' changed' if before.get(k) != v else ''}"
                     for k, v in after.items())
    report = (f"# Monthly refresh {month}\n\n" + "\n".join(f"- {n}" for n in notes) +
              "\n\nindex.html is rebuilt locally but NOT pushed. Next: update the numbers the page "
              "text quotes (lede, Fig. 2 to 8 paragraphs, 'What this means', sources block dates), "
              "check the page, then commit and push. In Claude Code, say \"update the AI job map "
              f"for {month}\".\n\n| Number | Before | Now |\n|---|---|---|\n{rows}\n")
    out = root / "data" / "monthly" / f"{month}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report)
    print("\n" + report)
    notify(f"Monthly refresh done. Summary in data/monthly/{month}.md")


if __name__ == "__main__":
    if "--scheduled" in sys.argv and (datetime.date.today().day < 5
                                      or (root / "data" / "monthly" / f"{month}.md").exists()):
        sys.exit(0)
    print(f"=== {datetime.datetime.now():%Y-%m-%d %H:%M} monthly refresh ===", flush=True)
    try:
        main()
    except Exception:
        notify("Monthly refresh failed. See data/monthly/run.log")
        raise
