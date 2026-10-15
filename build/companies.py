"""Turn a LinkedIn snapshot into build/companies.json for Fig. 4 and Fig. 5.

Usage:  python3 build/companies.py [YYYY-MM]   (default: latest snapshot)
Prints what it filtered so the choices can be checked by eye.
"""
import collections
import json
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
snaps = sorted((root / "data" / "linkedin").glob("20*"))
snap = root / "data" / "linkedin" / sys.argv[1] if len(sys.argv) > 1 else snaps[-1]
ORDER = ["IE", "GB", "DE", "IT", "FR", "NL", "ES"]

# Country branches of one firm count as that firm. Other brands (Sogeti, T-Systems) stay separate.
GROUPS = ["Accenture", "Capgemini", "NTT DATA", "PwC", "KPMG", "Deloitte", "EY", "CGI", "Amazon", "IBM", "Avanade", "Reply"]

# Recruiters and job boards post on behalf of unnamed clients, so they are not the employer.
AGENCY_NAMES = {"Jobgether", "Harnham", "Oliver Bernard", "Optimus Search", "Urban Linker", "nineDots.io",
                "Jack & Jill", "Client Server", "European Tech Recruit", "Solas IT Recruitment", "Hays", "Cpl",
                "Signify Technology", "Meraki Talent", "QCS Staffing", "Les Nouvelles Recrues", "HeadFirst Group",
                "Arrows", "VIVA Tech Talent", "GloPros", "BEYOND SKILLS", "&Work", "Crossover", "Turing", "Mercor",
                "Outlier", "DataAnnotation", "Alignerr", "micro1", "Toptal", "Braintrust"}
AGENCY_WORDS = ["staffing", "recruit", "dotación", "selección de personal", "personalvermittlung", "personaldienst",
                "recrutement", "selezione", "werving", "uitzend", "intérim", "interim"]
CONSULTING_WORDS = ["consult", "it services", "it-services", "servicios y consultoría", "servizi it", "services et conseil",
                    "it-dienstleistungen", "unternehmensberatung", "bedrijfsconsulting", "consulenza", "professional services",
                    "conseil", "accounting", "contabilidad", "contabilità", "buchhaltung", "boekhouding", "comptabilité"]


def employer(name):
    for g in GROUPS:
        if name == g or name.startswith(g + " ") or name.startswith(g + ","):
            return g
    return name


def is_agency(job):
    ind = (job.get("industries") or "").lower()
    return job["companyName"] in AGENCY_NAMES or any(w in ind for w in AGENCY_WORDS)


def role_key(job):
    """Same title at the same employer = one role. Many firms post one role once per city."""
    t = re.sub(r"\((?:m/w/d|m/f/d|w/m/d|f/m/d|h/f|f/h|all genders|m/f|f/m|w/m|m/w)\)", "", job["title"], flags=re.I)
    t = re.sub(r"\s+(?:in|à|a|en|bei)\s+[A-ZÀ-Ü][\w\-éèüöä]+(?:\s*(?:/|,|or|o|oder|ou)\s*[A-ZÀ-Ü][\w\-éèüöä]+)*\s*$", "", t.strip())
    t = re.sub(r"\s+-\s+(?:UK Wide|Remote|Hybrid|Madrid|Barcelona|London|Dublin|Paris|Milan|Milano|Amsterdam|Berlin|Munich|München)\s*$", "", t, flags=re.I)
    return employer(job["companyName"]), re.sub(r"\s+", " ", t).strip().lower()


def is_consulting(job):
    first = (job.get("industries") or "").split(",")[0].lower()
    return any(w in first for w in CONSULTING_WORDS)


out = {"snapshot": snap.name, "countries": {}, "dropped": collections.Counter()}
by_company = collections.defaultdict(collections.Counter)
for cc in ORDER:
    seen, jobs = set(), []
    for f in sorted(snap.glob(f"{cc}*.json")):
        for j in json.loads(f.read_text()):
            if j.get("companyName") and j["id"] not in seen:
                seen.add(j["id"])
                jobs.append(j)
    kept = []
    for j in jobs:
        if is_agency(j):
            out["dropped"][j["companyName"]] += 1
        else:
            kept.append(j)
    roles = {}
    for j in kept:
        roles.setdefault(role_key(j), j)
    counts = collections.Counter(company for company, _ in roles)
    for name, n in counts.items():
        by_company[name][cc] = n
    out["countries"][cc] = {
        "jobs": len(jobs), "agency": len(jobs) - len(kept), "roles": len(roles), "employers": len(counts),
        "consultingShare": round(sum(is_consulting(j) for j in roles.values()) / len(roles), 3),
        "top": counts.most_common(8),
    }

# Employers ranked by how many countries they hire in, then by total roles.
ranked = sorted(by_company.items(), key=lambda kv: (-len(kv[1]), -sum(kv[1].values())))
out["acrossCountries"] = [{"name": n, "byCountry": dict(c), "total": sum(c.values())} for n, c in ranked[:14]]
out["dropped"] = out["dropped"].most_common()

(root / "build" / "companies.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
for cc, d in out["countries"].items():
    print(cc, d["jobs"], "jobs,", d["roles"], "roles,", d["agency"], "agency,", f"{d['consultingShare']:.0%} consulting/IT services |", d["top"][:6])
print("\nAcross countries:")
for r in out["acrossCountries"]:
    print(f"  {r['name']:<28} {len(r['byCountry'])} countries, {r["total"]} roles  {r['byCountry']}")
print("\nDropped as agencies:", out["dropped"])
