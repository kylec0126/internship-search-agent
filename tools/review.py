"""
Tool: Weekly Self-Learning Review
Reads tracker.db, segments applications by outcome, and computes conversion
signals so YOU (Claude) can interpret them into next-week direction + resume
fine-tune targets. Also appends a dated snapshot to learnings.jsonl for
week-over-week trend tracking.

Usage:
  python tools/review.py            # print review + append weekly snapshot
  python tools/review.py --no-save  # print only, don't append a snapshot
"""

import sys
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

DB_PATH = Path(__file__).parent.parent / "my_job_data_center" / "tracker.db"
LEARN_PATH = Path(__file__).parent.parent / "my_job_data_center" / "learnings.jsonl"

SUBMITTED = {"applied", "responded", "assessment", "interview", "offer", "rejected"}
RESPONDED = {"responded", "assessment", "interview", "offer"}  # assessment = employer sent a test (e.g. HireVue)
INTERVIEWED = {"interview", "offer"}


def days_since(iso):
    try:
        d = datetime.fromisoformat(iso)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - d).days
    except Exception:
        return None


def fit_band(f):
    if f is None:
        return "unknown"
    if f >= 90: return "90-100"
    if f >= 80: return "80-89"
    if f >= 70: return "70-79"
    if f >= 60: return "60-69"
    return "<60"


def rate(num, den):
    return round(100 * num / den) if den else 0


def main():
    if not DB_PATH.exists():
        print(f"No tracker DB at {DB_PATH}")
        return
    db = sqlite3.connect(str(DB_PATH))
    rows = [dict(zip(["applied_at", "title", "company", "fit_score", "status", "notes"], r))
            for r in db.execute("SELECT applied_at,title,company,fit_score,status,notes FROM applications")]
    for r in rows:
        r["status"] = (r["status"] or "").lower()

    submitted = [r for r in rows if r["status"] in SUBMITTED]
    responded = [r for r in rows if r["status"] in RESPONDED]
    interviewed = [r for r in rows if r["status"] in INTERVIEWED]
    silent = [r for r in submitted if r["status"] == "applied"]

    # conversion by fit band
    band = defaultdict(lambda: {"submitted": 0, "responded": 0})
    for r in submitted:
        b = fit_band(r["fit_score"])
        band[b]["submitted"] += 1
        if r["status"] in RESPONDED:
            band[b]["responded"] += 1

    stale = [r for r in silent if (days_since(r["applied_at"]) or 0) >= 14]

    out = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "totals": {
            "logged": len(rows),
            "submitted": len(submitted),
            "responded": len(responded),
            "interviewed": len(interviewed),
            "response_rate_pct": rate(len(responded), len(submitted)),
            "interview_rate_pct": rate(len(interviewed), len(submitted)),
        },
        "by_fit_band": {b: {**v, "response_rate_pct": rate(v["responded"], v["submitted"])}
                        for b, v in sorted(band.items(), reverse=True)},
        "responded_roles": [f"{r['title']} @ {r['company']} (fit {r['fit_score']}, {r['status']})" for r in responded],
        "silent_roles": [f"{r['title']} @ {r['company']} (fit {r['fit_score']})" for r in silent],
        "stale_followups": [f"{r['title']} @ {r['company']} ({days_since(r['applied_at'])}d silent)" for r in stale],
    }

    # ---- print human-readable summary for Claude to interpret ----
    t = out["totals"]
    print(f"=== Weekly Review ({out['generated']}) ===")
    print(f"Submitted: {t['submitted']} | Responded: {t['responded']} ({t['response_rate_pct']}%) | "
          f"Interviews: {t['interviewed']} ({t['interview_rate_pct']}%)")
    print("\nConversion by fit band (does fit score predict responses?):")
    for b, v in out["by_fit_band"].items():
        print(f"  {b:>7}: {v['responded']}/{v['submitted']} responded ({v['response_rate_pct']}%)")
    print("\nResponded / advanced:")
    for s in out["responded_roles"] or ["  (none yet)"]:
        print(f"  + {s}")
    print("\nSilent (applied, no reply):")
    for s in out["silent_roles"] or ["  (none)"]:
        print(f"  - {s}")
    if out["stale_followups"]:
        print("\nStale >=14d (follow up or write off):")
        for s in out["stale_followups"]:
            print(f"  ! {s}")

    print("\n--- JSON ---")
    print(json.dumps(out, ensure_ascii=False))

    if "--no-save" not in sys.argv:
        with open(LEARN_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({"date": out["generated"], **out["totals"]}, ensure_ascii=False) + "\n")
        print(f"\nAppended weekly snapshot to {LEARN_PATH.name}")


if __name__ == "__main__":
    main()
