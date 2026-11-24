# Target companies (company-first sweep) — TEMPLATE

`/job-hunt` checks each company's own careers site for new Summer 2027 intern postings in the target cities (`market.md` rule 8) before reading the aggregator sources. Copy this file to `my_job_data_center/target_companies.md` (gitignored) and fill in your own list.

- **Why a company is here:** (A) it gave you a second step (response, assessment, interview); (B) it's a campus program in your strongest lane (`market.md` rule 10); (C) new this week, with a live program found on its own site; (S) suggested by the agent, with no history in your tracker; (K) added by you.
- **Slots left:** the 3-per-company cap minus your applications that count (any status except `drafted`). Note a firm's own limit where it states one.
- **How:** the careers-site API to query. "Workday" means the `cxs` jobs search on the listed tenant; "Greenhouse" means `boards-api.greenhouse.io/v1/boards/{board}/jobs`; "Ashby" means the public job-board API for the listed org.

| Company | Why | Slots left | Careers site / how to sweep |
|---|---|---|---|
| Example Bank | B | 3 | Workday `examplebank.wd5/Campus` |
| Example Fintech | B | 3 | Greenhouse `examplefintech` |
| Example Advisory | A: assessment | 2 | Ashby `exampleadvisory` |
| Example Insurer | S | 3 | Oracle `xxxx.fa.us2` |
| Example Utility | K | 3 | web search (careers site has no public API) |

**Left out (at or over the cap):** list parent companies here so the sweep skips them.
