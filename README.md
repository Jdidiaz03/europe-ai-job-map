# Europe's AI Job Map

**Live page:** https://jdidiaz03.github.io/europe-ai-job-map/

In September 2026, 15% of job postings in Ireland mentioned AI, up from 4.3% in November 2022. The UK went from 2.3% to 9.8% while its total postings fell by more than half. This page maps that change across seven European countries and shows who is hiring for AI roles, in which industries, for what kind of work and at what level.

## What it shows

| Figure | What | Source |
|---|---|---|
| 1. Map | Share of postings that mention AI, by country and month, Jan 2019 to Sep 2026 | Indeed Hiring Lab AI Tracker |
| 2. Small multiples | The same series, one chart per country | Indeed Hiring Lab AI Tracker |
| 3. Table | Estimated change in AI postings since Nov 2022 | AI share x total postings index |
| 4. Matrix | Employers with AI roles open in the most countries | LinkedIn sample, Oct 2026 |
| 5. Industries | Share of AI roles by the employer's industry | LinkedIn sample, Oct 2026 |
| 6. Top employers | Top six AI employers per country, and the share from consulting firms | LinkedIn sample, Oct 2026 |
| 7. Role types | Engineering, data, consulting and implementation, business, from the job title | LinkedIn sample, Oct 2026 |
| 8. Graduate roles | Share of AI roles with a junior, graduate, intern or trainee title | LinkedIn sample, Oct 2026 |

## Method

- **AI share.** Indeed's [AI Tracker](https://github.com/hiring-lab/ai-tracker) gives the daily share of postings that mention AI terms. It covers the UK, Ireland, Germany, France, Italy and the Netherlands, but not Spain. I average it by month.
- **Total postings.** Indeed's [Job Postings Tracker](https://github.com/hiring-lab/job_postings_tracker) is an index where February 2020 = 100. It includes Spain.
- **Estimated AI postings** = AI share x total postings index. It compares change over time; it is not a count of jobs.
- **Employers.** One LinkedIn search for "artificial intelligence" per country (past month, up to 700 results), plus a local-language search in Germany, France and Italy. 5,001 postings in total, collected 15 October 2026.
  - Counted as **distinct roles**: the same job title at the same employer counts once, because many firms repost one role per city.
  - **Recruitment agencies removed** (116 postings), since they hide the real employer.
  - **Country branches grouped** (Accenture Italia and Accenture España count as Accenture).
  - **Industry** comes from the first industry tag on the employer's LinkedIn page. **Role type** and **graduate roles** come from keywords in the job title. The keyword lists cover six languages and are in `build/companies.py`. Run `python3 build/companies.py --samples` to print sample titles from each group.
  - Only employer names and counts are published, not the listings.

## Rebuild

Needs Python 3 only. The raw data is not in this repo.

```
# 1. Indeed data: download AI_posting.csv and aggregate_job_postings_<CC>.csv
#    from the two Hiring Lab repos above into data/
# 2. LinkedIn sample (needs an Apify token in the macOS Keychain, service "apify-api")
python3 build/fetch_linkedin.py
# 3. Count employers, then inline everything into index.html
python3 build/companies.py
python3 build/build.py
```

`index.src.html` is the page source. `build/build.py` writes `index.html`, a single file with the data inlined. D3 and TopoJSON load from cdnjs.

## Credits

Data: Indeed Hiring Lab (CC BY 4.0). Map outlines: Natural Earth via world-atlas. Built by [Julian Diaz](https://www.linkedin.com/in/julian-diaz1) with Claude Code.
