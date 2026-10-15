"""Turn a LinkedIn snapshot into build/companies.json for Fig. 4 and Fig. 5.

Usage:  python3 build/companies.py [YYYY-MM] [--samples]   (default: latest snapshot)
Prints what it filtered so the choices can be checked by eye.
"""
import collections
import json
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
snaps = sorted((root / "data" / "linkedin").glob("20*"))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
snap = root / "data" / "linkedin" / args[0] if args else snaps[-1]
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
                    "conseil", "accounting", "contabilidad", "contabilità", "buchhaltung", "boekhouding", "comptabilité",
                    "servizi professionali", "services professionnels", "freiberufliche dienstleistungen", "professionele services",
                    "servicios profesionales", "rechnungswesen"]


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


# Industry groups from LinkedIn's first industry tag, in 5 languages. Checked in this order.
INDUSTRY = [
    ("tech", ["software", "logiciel", "sviluppo di software", "desarrollo de software", "technolog", "tecnolog", "informat",
              "information", "internet", "intelligen", "künstliche", "kunstmatige", "data infrastructure", "telecom",
              "telekom", "comput", "ordinat", "semicond", "halbleiter", "semi-conducteur", "sécurité informatique",
              "netwerkbeveiliging", "network security", "videogi", "video game", "jeux vidéo", "informaci", "halfgeleider",
              "dateninfrastruktur", "infraestructura y análisis"]),
    ("finance", ["financ", "finanz", "financi", "bank", "banc", "insur", "assur", "assicur", "versicher", "seguro", "verzeker",
                 "investment", "capital market", "kapitaalmarkt", "kapitalmarkt"]),
    ("industry", ["manufactur", "fabbric", "fabric", "herstellung", "pharma", "aerospa", "défense", "defense", "difesa",
                  "automo", "fahrzeug", "veicol", "vehícul", "health", "hospital", "krankenh", "ospedal", "hôpita", "santé",
                  "sanità", "salud", "zorg", "engineering", "ingegner", "ingénierie", "ingeniería", "ingenieur", "transport",
                  "energ", "utilit", "oil", "chemi", "chimi", "químic", "retail", "detailhandel", "einzelhandel", "commerce",
                  "vendita al dettaglio", "venta al por menor", "biotech", "medical", "médic", "medizin", "logist", "construc",
                  "bau", "bouw", "automatis", "maschinenbau", "machin", "maquinaria", "manifattur", "geneesmiddel", "verteidigung",
                  "raumfahrt", "productie", "edilizia", "food", "aliment", "airline", "aviation", "groothandel", "großhandel",
                  "wholesale", "versorgung", "real estate", "immobili", "luchtvaart", "farmac"]),
]
INDUSTRY_NAMES = {"consulting": "Consulting & IT services", "tech": "Software & tech", "finance": "Finance & insurance",
                  "industry": "Industry, health & retail", "other": "Research, public sector & other", "none": "No industry tag"}


def industry(job):
    first = (job.get("industries") or "").split(",")[0].lower().strip()
    if not first:
        return "none"
    if is_consulting(job):  # same rule as the consulting share in Fig. 6
        return "consulting"
    for key, words in INDUSTRY:
        if any(w in first for w in words):
            return key
    return "other"


# Role type from the job title. Checked in this order, so "Data Scientist & AI Consultant" is consulting.
ROLE = [
    ("consulting", r"consult|berater|beratung|consulente|consultor|advisory|solutions? (?:architect|engineer|specialist)"
                   r"|forward[ -]deployed|implementation|deployment|transformation|adoption|enablement|pre-?sales|avant-vente"
                   r"|functional analyst|delivery|deployed|solucion|soluzion"),
    ("business", r"\bsales\b|account (?:manager|executive|director)|business development|go-to-market|\bgtm\b|marketing"
                 r"|product (?:manager|owner|lead|director|marketing)|head of product|customer success|commercial|vertrieb"
                 r"|\bventas?\b|vendite|strateg|partnership|operations manager|recruit|talent acquisition|counsel|lawyer|\bhr\b"
                 r"|content (?:manager|specialist|strategist|creator)|communications"),
    ("data", r"data|analytics|analyst|analyste|analista|statistic|\bbi\b|business intelligence|quant"),
    ("eng", r"engineer|ingénieur|ingenier|ingegner|ingenieur|developer|développeur|desarrollador|sviluppator|entwickler"
            r"|ontwikkelaar|programm|architect|arquitect|tech lead|leader technique|research|scientist|chercheur|investigador|ricercat|forsch|postdoc|ph\.?d"
            r"|doctora|technical staff|machine learning|\bml\b|mlops|devops|\bsre\b|software|full[ -]?stack|back[ -]?end|front[ -]?end"),
]
ROLE_NAMES = {"eng": "Engineering & research", "data": "Data & analytics", "consulting": "Consulting & implementation",
              "business": "Business & product", "other": "Other (managers, specialists)"}
JUNIOR = (r"\bjunior\b|\bjr\.?\b|graduate|\bgrad\b|intern\b|internship|trainee|\bstage\b|stagiaire|alternan|apprenti"
          r"|praktik|werkstudent|working student|tirocin|stagista|becari|prácticas|practicas|\bstagiair|afstudeer|entry[ -]level"
          r"|early careers?|neolaurea|jeune diplômé|young professional|berufseinst")


def role_type(job):
    t = job["title"].lower()
    for key, pattern in ROLE:
        if re.search(pattern, t):
            return key
    return "other"


def is_junior(job):
    return bool(re.search(JUNIOR, job["title"].lower()))


out = {"snapshot": snap.name, "countries": {}, "dropped": collections.Counter(),
       "industryNames": INDUSTRY_NAMES, "roleNames": ROLE_NAMES}
by_company = collections.defaultdict(collections.Counter)
samples = collections.defaultdict(list)
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
        "industry": dict(collections.Counter(industry(j) for j in roles.values())),
        "roleType": dict(collections.Counter(role_type(j) for j in roles.values())),
        "junior": sum(is_junior(j) for j in roles.values()),
        # LinkedIn's own seniority tag, only filled in for some countries; used as a cross-check.
        "tagged": sum(bool(j.get("seniorityLevel")) for j in roles.values()),
        "juniorTag": sum(j.get("seniorityLevel") in ("Entry level", "Associate", "Internship") for j in roles.values()),
    }
    for j in roles.values():
        samples[role_type(j)].append(j["title"])
        if is_junior(j):
            samples["junior"].append(j["title"])

# Employers ranked by how many countries they hire in, then by total roles.
ranked = sorted(by_company.items(), key=lambda kv: (-len(kv[1]), -sum(kv[1].values())))
out["acrossCountries"] = [{"name": n, "byCountry": dict(c), "total": sum(c.values())} for n, c in ranked[:14]]
out["dropped"] = out["dropped"].most_common()
all_roles = sum(d["roles"] for d in out["countries"].values())
out["summary"] = {
    "roles": all_roles, "employers": len(by_company),
    "matrixRoles": sum(r["total"] for r in out["acrossCountries"]),
    "smallEmployers": sum(1 for c in by_company.values() if sum(c.values()) <= 2),
    "roleType": dict(sum((collections.Counter(d["roleType"]) for d in out["countries"].values()), collections.Counter())),
    "industry": dict(sum((collections.Counter(d["industry"]) for d in out["countries"].values()), collections.Counter())),
    "junior": sum(d["junior"] for d in out["countries"].values()),
}

(root / "build" / "companies.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
for cc, d in out["countries"].items():
    print(cc, d["jobs"], "jobs,", d["roles"], "roles,", d["agency"], "agency,", f"{d['consultingShare']:.0%} consulting/IT services |", d["top"][:6])
print("\nAcross countries:")
for r in out["acrossCountries"]:
    print(f"  {r['name']:<28} {len(r['byCountry'])} countries, {r["total"]} roles  {r['byCountry']}")
print("\nDropped as agencies:", out["dropped"])

def pct(part, whole):
    return " ".join(f"{k} {v / whole:.0%}" for k, v in sorted(part.items(), key=lambda kv: -kv[1]))

print("\nIndustry, role type and junior share by country (each country's groups add up to its roles):")
for cc, d in out["countries"].items():
    assert sum(d["industry"].values()) == sum(d["roleType"].values()) == d["roles"]
    print(f"  {cc} industry: {pct(d['industry'], d['roles'])}")
    print(f"     role:     {pct(d['roleType'], d['roles'])}   junior {d['junior'] / d['roles']:.1%}")
s = out["summary"]
print(f"\nAll: {s['roles']} roles, {s['employers']} employers, {s['smallEmployers']} with 1-2 roles; "
      f"matrix covers {s['matrixRoles']} ({s['matrixRoles'] / s['roles']:.0%})")
print("  role:", pct(s["roleType"], s["roles"]), "| junior", f"{s['junior'] / s['roles']:.1%}")
print("  industry:", pct(s["industry"], s["roles"]))
if "--samples" in sys.argv:
    import random
    random.seed(0)
    for k, titles in samples.items():
        print(f"\n[{k}] {len(titles)}:", " | ".join(random.sample(titles, min(25, len(titles)))))
