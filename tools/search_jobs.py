"""
Tool: Search Jobs
Called by Claude Code to pull live job listings.
Two sources: JSearch (full JDs) + Adzuna (salary/market data).

Usage: python tools/search_jobs.py "data analyst" "New York" 15
       python tools/search_jobs.py --usage    (JSearch quota this month; costs no request)
"""

import sys
import os
import json
import re
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

# Employer applicant-tracking systems; an apply link on one of these is the employer's own posting
ATS_DOMAINS = {
    "myworkdayjobs.com": "Workday", "myworkdaysite.com": "Workday",
    "greenhouse.io": "Greenhouse", "lever.co": "Lever", "icims.com": "iCIMS",
    "ashbyhq.com": "Ashby", "oraclecloud.com": "Oracle", "smartrecruiters.com": "SmartRecruiters",
}


def _host(url):
    host = (urlparse(url or "").hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def employer_links(r):
    # First apply link on a known ATS, and first apply link on the employer's own website domain
    links = [r.get("job_apply_link")] + [o.get("apply_link") for o in r.get("apply_options") or []]
    links = [u for u in links if u]
    site = _host(r.get("employer_website"))
    ats = next(((u, name) for u in links for d, name in ATS_DOMAINS.items()
                if _host(u) == d or _host(u).endswith("." + d)), (None, None))
    own = next((u for u in links if site and (_host(u) == site or _host(u).endswith("." + site))), None)
    return {"ats_link": ats[0], "ats": ats[1], "employer_site_link": own}


def jsearch_usage():
    # OpenWeb Ninja usage endpoint: plan quota for the current billing period (not a search request)
    api_key = os.environ.get("JSEARCH_API_KEY") or os.environ.get("RAPIDAPI_KEY")
    if not api_key:
        sys.exit("ERROR: JSEARCH_API_KEY is missing from .env")
    resp = requests.get("https://api.openwebninja.com/usage", headers={"x-api-key": api_key},
                        params={"api_id": "jsearch"}, timeout=30)
    resp.raise_for_status()
    q = resp.json()["data"]["quotas"][0]
    return {"limit": q["limit"], "used": q["used"], "remaining": q["remaining"], "reset_at": q["reset_at"],
            "stop_at_80pct": int(q["limit"] * 0.8)}


def search_jsearch(role, location, max_results=10):
    api_key = os.environ.get("JSEARCH_API_KEY") or os.environ.get("RAPIDAPI_KEY")
    if not api_key:
        return []

    resp = requests.get(
        "https://api.openwebninja.com/jsearch/search-v2",
        headers={"x-api-key": api_key},
        params={"query": f"{role} in {location}", "country": "us", "date_posted": "month"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json().get("data", {})

    jobs = []
    for r in (data.get("jobs", []) if isinstance(data, dict) else data)[:max_results]:
        jobs.append({
            "id": r.get("job_id", ""),
            "title": r.get("job_title", ""),
            "company": r.get("employer_name", "Unknown"),
            "location": f"{r.get('job_city', '')}, {r.get('job_state', '')}",
            "description": r.get("job_description", ""),
            "url": r.get("job_apply_link") or r.get("job_google_link", ""),
            "employer_website": r.get("employer_website"),
            "publisher": r.get("job_publisher"),
            **employer_links(r),
            "salary_min": r.get("job_min_salary"),
            "salary_max": r.get("job_max_salary"),
            "posted": r.get("job_posted_at_datetime_utc", ""),
            "source": "jsearch",
            "type": r.get("job_employment_type", ""),
            "required_skills": r.get("job_required_skills") or [],
            "qualifications": (r.get("job_highlights") or {}).get("Qualifications", []),
            "responsibilities": (r.get("job_highlights") or {}).get("Responsibilities", []),
        })
    return jobs


def search_adzuna(role, location, max_results=10):
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        return []

    resp = requests.get(
        "https://api.adzuna.com/v1/api/jobs/us/search/1",
        params={"app_id": app_id, "app_key": app_key, "what": role, "where": location,
                "results_per_page": max_results, "sort_by": "relevance",
                "max_days_old": 30},  # same window as JSearch's date_posted=month
        timeout=15,
    )
    resp.raise_for_status()

    jobs = []
    for r in resp.json().get("results", []):
        jobs.append({
            "id": str(r.get("id", "")),
            "title": r.get("title", ""),
            "company": r.get("company", {}).get("display_name", "Unknown"),
            "location": r.get("location", {}).get("display_name", ""),
            "description": r.get("description", ""),
            "url": r.get("redirect_url", ""),
            "employer_website": None, "publisher": "Adzuna",
            "ats_link": None, "ats": None, "employer_site_link": None,
            "salary_min": r.get("salary_min"),
            "salary_max": r.get("salary_max"),
            "posted": r.get("created", ""),
            "source": "adzuna",
            "type": "",
            "required_skills": [],
            "qualifications": [],
            "responsibilities": [],
        })
    return jobs


COMPANY_SUFFIXES = {"inc", "incorporated", "llc", "ltd", "limited", "corp", "corporation", "co", "plc", "lp", "llp"}


def normalize_company(name):
    # Lowercase, "&" -> "and", punctuation removed, legal suffixes dropped: "Acme, Inc." -> "acme"
    words = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower().replace("&", " and ")).split()
    while words and words[-1] in COMPANY_SUFFIXES:
        words.pop()
    return " ".join(words)


def apply_skip_list(jobs):
    # Drops postings the student has already handled outside the agent (my_job_data_center/skip_list.json)
    skip_file = Path(__file__).parent.parent / "my_job_data_center" / "skip_list.json"
    if not skip_file.exists():
        return jobs
    rules = json.loads(skip_file.read_text())

    # Compare whole normalized company names, never substrings: "art" must not match "Start" or
    # "Art of Problem Solving" (same fix as the duplicate check in /job-hunt step 5)
    def skipped(job):
        company = normalize_company(job["company"])
        return any(normalize_company(r["company"]) == company
                   and r.get("title_contains", "").lower() in job["title"].lower() for r in rules)

    kept = [j for j in jobs if not skipped(j)]
    if len(kept) < len(jobs):
        print(f"Skipped {len(jobs) - len(kept)} listing(s) matching skip_list.json", file=sys.stderr)
    return kept


if __name__ == "__main__":
    if sys.argv[1:2] == ["--usage"]:
        print(json.dumps(jsearch_usage(), indent=2))
        sys.exit()
    role = sys.argv[1] if len(sys.argv) > 1 else "data analyst intern"
    location = sys.argv[2] if len(sys.argv) > 2 else "United States"
    max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    jsearch_skipped = False
    try:
        jobs = search_jsearch(role, location, max_results)
    except requests.HTTPError as e:
        # JSearch's free tier has a monthly quota; once it's used up (429), fall back to Adzuna alone
        if e.response is None or e.response.status_code != 429:
            raise
        print("WARNING: JSearch quota or rate limit hit (HTTP 429); skipping JSearch and using Adzuna only",
              file=sys.stderr)
        jobs, jsearch_skipped = [], True
    if len(jobs) < max_results:
        # Adzuna is optional: a bad key or outage shouldn't discard the JSearch results
        try:
            jobs.extend(search_adzuna(role, location, max_results - len(jobs)))
        except requests.RequestException as e:
            if jsearch_skipped:
                sys.exit(f"ERROR: JSearch is out of quota and Adzuna failed too ({e})")
            print(f"WARNING: Adzuna search failed, using JSearch results only ({e})", file=sys.stderr)

    print(json.dumps(apply_skip_list(jobs), indent=2, ensure_ascii=False))
