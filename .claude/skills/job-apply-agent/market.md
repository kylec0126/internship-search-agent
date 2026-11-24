# Job Application Agent — Market intel (steps 2–3)

**Purpose:** find real openings and extract what the market actually wants. This becomes the student's personal Job Data Center — run it weekly to track trends.

Run everything from the repository root (your current directory).

1. **Search jobs:** `python tools/search_jobs.py "{role}" "{location}" 15`
   - Calls JSearch + Adzuna, returns JSON with real listings (full JD text). Each JSearch listing also carries `ats_link`/`ats` (an apply link on the employer's ATS) and `employer_site_link` (an apply link on the employer's own website), used for verification (rule 11).
   - **Check the quota before searching:** `python tools/search_jobs.py --usage` prints the JSearch plan's `limit`, `used`, `remaining` and `reset_at` for this billing period. It costs no search request. Tell the student how many requests are left, and stop searching once `used` reaches 80% of `limit` (`stop_at_80pct`).
   - Drops postings listed in `my_job_data_center/skip_list.json` (roles the student already handled on their own) and reports how many it skipped on stderr. To skip another, add `{"company": ..., "title_contains": ..., "reason": ...}`.
   - Needs API keys in `.env`. If they are missing or the call errors, **stop and say exactly what is missing** and point at the setup section of the README. Do not invent listings and do not continue with placeholder jobs — every later step (Job Data Center, skill map, fit scores) is only as real as this data.
2. **Extract skill frequencies** (YOU do this from the JD text): hard skills + how many JDs mention each, soft skills + freq, tools/software + freq, certifications if any.
3. **Save the snapshot:** `python tools/save_jdc.py "{role}" '{market_profile_json}' {n_jobs}` → writes to `my_job_data_center/`.

**Output:** a short "the market wants ___" summary — the top demanded hard skills, tools, and any recurring domain context (e.g. many roles are policy / finance / healthcare).

## Ranking rules for all job searches

These apply to every search and every ranked list of postings: JSearch, Simplify, combined searches, re-ranks, and the top-5 table in `apply.md`. Follow them without being asked.

1. **Always find the posting date.** Use the company's own posting date from its careers site when available (for example Workday `startDate`, Greenhouse `first_published`, Oracle `ExternalPostedStartDate`, Lever `createdAt`, Ashby `publishedAt`, JSON-LD `datePosted`, amazon.jobs `posted_date`). Fall back to Simplify's `date_posted` or JSearch's posted date only if the company doesn't show one, and mark which source was used: (company), (Simplify) or (JSearch). JSearch dates are often aggregator reposts, so never trust them alone.
2. **Rank in this order:**
   1. Deadline within the next 10 days (soonest first)
   2. Posted in the last 14 days
   3. Then fit score

   Within each tier, break ties by fit score.
3. **Include a "Days since posted" column** in every results table, with the date source in parentheses, e.g. `12 (company)`.
4. **Drop postings older than 60 days** unless the company's site shows a future deadline. List what was dropped and why.
5. **Company cap: 3 applications per parent company.** Count rows in `my_job_data_center/tracker.db` with status other than `drafted`. Skip companies with 3 or more applications, unless the student says otherwise, and name them in the output.
   - **A 4th is allowed for a clearly different team.** If a company has exactly 3 applications and the posting is clearly a different team or function from all three, don't skip it. List it in a **"Capped but strong fit"** section, with the same columns as the main tables, plus the company's existing applications (title and status from the tracker) so the student can decide. Companies with 4 or more applications are skipped.
   - **Count by parent company.** Subsidiaries and brands that share one employer or careers system count as one company:
     - **Marsh McLennan** = Marsh, Mercer, Oliver Wyman, NERA (also Marsh McLennan Agency, Guy Carpenter)
     - **PACCAR** = PACCAR, PACCAR Parts, Kenworth, Peterbilt
     - **TikTok** = TikTok, ByteDance
     - **Allstate** = Allstate, Arity (also National General)
     - **News Corp** = Dow Jones, The Wall Street Journal, Barron's, MarketWatch, New York Post, HarperCollins, Realtor.com. Fox Corporation is a separate company.
     - **Comcast** = NBCUniversal, DreamWorks Animation, Peacock, Sky, Comcast. Simplify files some NBCUniversal postings under "DreamWorks Animation".
   - Also merge spelling variants of one employer (for example "Health Care Service Corporation" = "HCSC", "EY" = "Ernst & Young").
   - Apply the same grouping to any other subsidiaries you notice that share one careers system, and say which grouping you added.
6. **Title screen: drop only pure software engineering, hardware and PhD-only roles.** Drop titles that are pure software engineering (software engineer/SWE, backend, frontend, full-stack, mobile, embedded, SRE/DevOps), hardware (hardware, firmware, electrical, mechanical, chip/ASIC/RF and similar), and roles open only to PhD students. **Keep everything else** (data engineering, data science, ML/AI, quant research, product analyst, research and similar) and score it normally, with a one-line stretch note when it leans technical. If a dropped title contains "data" or "analyst" (any case), list it in a **"Filtered by title"** section with company, title, city, link and the reason, instead of dropping it silently.
7. **Show every role scoring 55+.** Group them as **Strong (75+)**, **Possible (65–74)** and **Stretch (55–64)**, each ordered by rule 2 (deadline, then recency, then fit). Give every Stretch role one line on its main gap. Count roles under 55 in the output, without listing them.
9. **Drop graduate-level titles.** Drop any posting whose title contains "Graduate Intern", "MBA" or "Master's" (including "Master's only") unless the posting explicitly says undergraduates may apply. "Undergraduate Intern" titles are not affected. List each drop with its reason. (Added 2026-11-12 after an application to a graduate-only role was rejected.)
8. **Hard requirements never loosen:** Summer 2027 term, open to undergraduates, in the student's US target cities (or US remote), still open on the employer's site, and no invented experience in scoring or notes. **Target cities:** New York City (including Brooklyn), Long Island (e.g. Melville, Hicksville, Stony Brook), Boston/Cambridge, Chicago, the San Francisco Bay Area and the rest of California, and Seattle. Flag other cities as relocation and include them only when the student asks. (Long Island added 2026-11-23.)
10. **Where to aim (from outcomes, 2026-11-16 review).** Prioritize **consulting, advisory, strategy and operations roles at structured campus programs, especially in financial services** (banks, payments, credit, insurance, Big 4/advisory): 5 of the first 7 responses came from these. Keep marketing analytics at media/tech companies in the main lanes. **Deprioritize generic data science, data engineering and ML roles at tech companies** (0 for about 30): score them about 10 points lower and list them only when the domain fit is unusual (e.g. fintech/tokenization, sports/games data, healthcare tied to the student's interests), with that reason stated.

11. **JSearch: budget and verification (2026-11-23).**
   - **Budget:** up to 10 searches per `/job-hunt jsearch` run (about once a week). Search role keywords (business analyst, data analyst, risk, operations, strategy, consulting, financial analyst, analytics) across the target cities in rule 8; `/job-hunt` has the search plan and keyword rotation. Check `--usage` first and never go past 80% of the monthly quota.
   - **Verify by apply link first:** if a result's `ats_link` is on the employer's own ATS (Workday, Greenhouse, Lever, iCIMS, Ashby, Oracle, SmartRecruiters), or `employer_site_link` is on the employer's own domain, count the posting as found on the employer's site. Open that link (the lead's one ATS query) for the date, deadline and eligibility, and confirm it's open. An ATS board belonging to a staffing agency or recruiter doesn't count. Web search only if neither link works.
   - **Unverified JSearch leads** scoring 65+ go in a separate **"JSearch – verify by hand"** section, with fit scored from the JSearch description and the aggregator link marked as not official. Lower-scoring ones are only counted. They never appear in the main tables.

12. **Company-first sweep (2026-11-23).** Every `/job-hunt` run also checks the careers sites of the companies in `my_job_data_center/target_companies.md` (second-step companies, financial-services and advisory campus programs, and the student's own picks). Companies at the 3-application cap are left out. Gmail digests are read in full, never triaged by subject. Recruiter messages go in a **Recruiter outreach** section.

**Note on "fresh postings" searches:** when a search is limited to recent postings (for example "posted since Nov 3"), also include **actuarial** roles posted in the previous 30 days. Actuarial programs post earlier than other internships, so a short window misses most of them. All other rules above still apply to those roles, including the 60-day cutoff and the 3-application cap.
