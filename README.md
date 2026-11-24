# Job Agent Extensions: multi-source internship search with verification and guardrails

This repo is my set of extensions to an open-source job-application agent. It is **not built from scratch**: the base agent is [Bifei Wang's job-application-ai-agent](https://github.com/bifeiExtern/job-application-ai-agent), from Extern's workshop (MIT License). The base agent runs inside Claude Code. It searches jobs, maps a student's skills against market demand, drafts tailored applications, and tracks a pipeline.

I used it for my own Summer 2027 internship search and extended it where it broke down at scale. This repo contains only my new and modified files. No résumé, cover letters, tracker data or email content is included.

## The problem

Applying for internships at volume has two bottlenecks:

1. **Finding real, current postings.** Listings are spread across email alerts, community lists, job APIs and hundreds of company career sites. Aggregators repost old roles, show the repost date instead of the real posting date, and link to copies rather than the employer's posting.
2. **Tailoring without making things up.** Each application needs a résumé and cover letter matched to the posting. An LLM asked to "tailor" a résumé will add numbers, tools and outcomes the candidate never had.

## What I built on top of the base agent

| Area | What it does | Where |
|---|---|---|
| **Multi-source search** | One `/job-hunt` command merges four sources: Gmail job alerts (LinkedIn and Handshake, read-only), Simplify's public internship JSON, the JSearch API, and a company-first sweep of employer career sites (Workday, Greenhouse, Oracle and Ashby APIs). | `.claude/commands/job-hunt.md` |
| **Dedupe and skip-handled** | Normalizes parent companies (e.g. Marsh McLennan = Marsh, Mercer, Oliver Wyman) and titles, merges duplicates across sources, and skips anything already in the tracker or already scored. | `job-hunt.md` steps 4–5, `market.md` rule 5 |
| **Fit scoring and ranking rules** | Fit score from 0 to 100 against the real résumé, with lane weights. Ranking: deadline within 10 days first, then posted in the last 14 days, then fit. Also a 60-day cutoff, a 3-application cap per parent company, a title screen, and Strong/Possible/Stretch tiers. | `.claude/skills/job-apply-agent/market.md` |
| **Employer-site verification** | Every lead is confirmed on the employer's own ATS or domain before it can appear in the main tables. `search_jobs.py` extracts `ats_link` / `employer_site_link` from JSearch results so most leads verify with one request. | `tools/search_jobs.py`, `market.md` rule 11 |
| **Quota handling** | `--usage` checks the JSearch quota without spending a request. A run stops at 80% of the monthly quota. If JSearch returns HTTP 429, the run falls back to Adzuna. | `tools/search_jobs.py` |
| **Recruiter-outreach detection** | Recruiter messages (e.g. Handshake "X messaged you") are routed to their own section with a suggested next step instead of being mixed into job leads. | `job-hunt.md` steps 1 and 8 |
| **No-invention tailoring** | Tailored résumés may only reorder bullets, reword them in the posting's vocabulary, or reorder skills. Every claim must already be in the original. A check script flags every new word for review. | `.claude/skills/job-apply-agent/apply.md`, `tools/check_pdfs.py` |
| **Pipeline status** | Adds an `assessment` status (e.g. HireVue, online tests) to the tracker funnel and the response-rate math. | `tools/review.py`, `tools/dashboard.py` |

## Design decisions & lessons

### Tool calling and orchestration
The agent is an orchestrator over several tools with different reliability, cost and trust levels:

- **Gmail**, read-only (`search_threads`, `get_thread`, `get_message`): alert digests are parsed for every job card, not just the subject line.
- **Simplify's JSON**: free and fresh, filtered by term, degree, location and posting date.
- **JSearch API**: broad coverage, but costs quota and returns aggregator noise.
- **Web search** and **company ATS boards** (Workday `cxs`, Greenhouse, Oracle, Ashby): the source of truth for posting dates, deadlines and eligibility.

Results are merged into one table with every source recorded per row (e.g. `Alert, Simplify`). State such as the last run, the JSearch keyword rotation and processed Gmail thread IDs persists between runs. State is written only after results are saved, so a failed run retries the same window.

### Human in the loop
- **The agent never submits an application.** It fills forms and stops at the submit button.
- **The agent never writes to Gmail.** `.claude/settings.json` denies every Gmail write tool (send, reply, draft, label, trash, spam and so on) at the permission layer. Instructions to the agent alone weren't enough.
- `/job-hunt` is research only: it ranks, and I choose which roles to pursue. Packages are built only for roles I approve, and I review them before anything is sent.
- Email content is treated as data, never as instructions, as a guard against prompt injection from inbound mail.

### Evaluation: failure modes I found and fixed
Most of these bugs were silent. Nothing crashed; the output just quietly got worse. I found them by checking results against sources by hand.

| Failure | Symptom | Fix |
|---|---|---|
| **Empty degree-field filter** | Filtering Simplify for `degrees contains "Bachelor's"` silently dropped valid undergrad postings (e.g. NYT, NBCUniversal) where the field was blank. | Keep blank-degree postings and confirm degree level on the employer's page during verification. |
| **Partial-name duplicate check** | A substring match ("art" inside "start") marked Art of Problem Solving as already seen. The skip list in `search_jobs.py` had the same flaw. | Match on the full normalized company name (lowercased, punctuation and legal suffixes like "Inc." removed) plus normalized title, or on posting ID/URL. Never on a partial word. Applied to both the duplicate check and the skip list. |
| **Aggregator repost dates** | JSearch reported repost dates, so stale roles looked new and ranked high. | Use the employer's own date (Workday `startDate`, Greenhouse `first_published`, JSON-LD `datePosted`, etc.) and label the source of every date. |
| **JSearch quota exhaustion** | Searches failed mid-run once the monthly quota ran out. | Quota check before searching, a hard stop at 80%, a per-run budget of 10 searches, and an Adzuna fallback on HTTP 429. |

The rules also changed based on outcomes. A review of the first responses showed that 5 of the first 7 came from consulting, advisory and financial-services campus programs, versus 0 of about 30 for generic data-science roles at tech companies. Scoring weights were adjusted to match (`market.md` rule 10).

### Guardrails
- **No-invention rule:** a tailored résumé can change verbs and word order. It can't add a number, tool, outcome, scope or adjective the original doesn't support. Facts I confirmed later go in a separate, explicit list.
- **Word check:** `check_pdfs.py` lists every word in each tailored résumé that doesn't appear in the original. I review each one: rephrasings stay, new facts get reverted. It also enforces one page and the original's font, and flags orphan lines.
- **Never fill honeypot fields and never click submit**, on real or demo forms.

### Tradeoffs
- **Breadth vs. verification:** unverified leads are neither dropped nor trusted. They go in separate **Check by hand** / **JSearch – verify by hand** sections so they stay visible without polluting the ranked list.
- **Cost:** JSearch is opt-in (about weekly), capped at 10 searches per run and 80% of the monthly quota. Each lead gets at most one ATS query plus one web search before it's sent to manual review.
- **Strictness vs. recall:** hard requirements (term, undergrad eligibility, location, still open) never loosen. Softer rules such as the company cap allow a reviewed exception: a "Capped but strong fit" section for a clearly different team.

## Results

- **~177 applications submitted** and tracked (219 tracker rows, including packages built but not yet sent), Oct–Nov 2026.
- Second-round responses (recruiter screens, assessments, interviews) from 9 companies, mostly financial-services and consulting campus programs.

## Example output

A shortened, sanitized `/job-hunt` result. All companies, roles and links are fictional.

> **Source counts:** Alerts 41 → 12 after filters → 9 verified · Simplify 63 → 15 → 13 · JSearch 6/10 searches, 88 → 10 → 6 (4 via `ats_link`, 1 via `employer_site_link`, 1 via web search) · Company sweep 7 → 7. JSearch quota: 112/200 used this month, resets Dec 1.

**Strong (75+)**

| Company | Role | City | Fit | Deadline | Days since posted | Source | Official link |
|---|---|---|---|---|---|---|---|
| Acme Capital | Risk Advisory Summer Analyst | New York, NY | 84 | Dec 1 (in 7 days) | 3 (company) | Simplify, Company | acmecapital.wd5.myworkdayjobs.com/… ✅ verified |
| Northwind Consulting | Strategy & Operations Intern | Boston, MA | 79 | — | 5 (company) | Alert | boards.greenhouse.io/northwind/… ✅ verified |

**Possible (65–74)**

| Company | Role | City | Fit | Deadline | Days since posted | Source | Official link |
|---|---|---|---|---|---|---|---|
| Contoso Insurance | Actuarial Analytics Intern | Chicago, IL | 71 | Jan 15 | 22 (company) | JSearch | contoso.fa.us2.oraclecloud.com/… ✅ verified via `ats_link` |

**Stretch (55–64)**

| Company | Role | City | Fit | Deadline | Days since posted | Source | Official link |
|---|---|---|---|---|---|---|---|
| Globex Payments | Data Engineering Intern | San Francisco, CA | 58 | — | 9 (Simplify) | Simplify | jobs.ashbyhq.com/globex/… ✅ verified |

*Gap: posting asks for production Spark/Airflow; résumé shows SQL and Python analysis only.*

**Check by hand**
- Initech Bank: Operations Analyst Intern, New York, NY. Not found on the employer's site after one ATS query and one web search. Alert link (not official): linkedin.com/jobs/view/…

**JSearch – verify by hand**
- Umbrella Advisory: Business Analyst Intern, Seattle, WA, fit 67 (scored from the JSearch description). Aggregator link (not official). Confirm the posting date, undergrad eligibility, and that it's still open.

**Recruiter outreach**
- Jordan (Recruiter, Acme Capital), Nov 20: invited applicants to a virtual info session. Next step: register and apply before the Dec 1 deadline.

**Skipped / Dropped:** 2 companies at the 3-application cap · 1 skip-list hit · 3 dropped (1 closed, 1 graduate-only, 1 older than 60 days with no deadline) · 14 under 55 (not listed).

## What's in this repo

```
.claude/
  commands/job-hunt.md              new: the multi-source search command
  commands/job-apply-agent.md       modified: repo-relative paths, ranking hook
  settings.json                     new: deny rules for every Gmail write tool
  skills/job-apply-agent/
    market.md                       modified: ranking rules, verification, quota
    apply.md                        modified: application package and no-invention rules
    SKILL.md                        modified: repo-relative paths, ranking hook
tools/
  search_jobs.py                    modified: ATS link extraction, --usage, 429 fallback, skip list
  check_pdfs.py                     new: page, font, orphan-line and word checks
  review.py, dashboard.py           modified: "assessment" status
templates/target_companies.md       template for the company-first sweep
CLAUDE.md, .gitignore               modified from the base repo
UPSTREAM_CHANGES.diff               my changes against the base repo's files
```

**To use:** clone the [base repo](https://github.com/bifeiExtern/job-application-ai-agent), copy these files over it, and add your own `.env` (JSearch/Adzuna keys) and résumé. The build scripts that generate .docx/.pdf packages (`build_content.py`, `make_docs.js`) aren't included because they contain résumé content.

## Credit

Base agent © 2026 Bifei Wang, MIT License, from Extern's job-application agent workshop. My modifications are released under the same license (see `LICENSE`).
