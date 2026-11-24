"""
Tool: Application Dashboard (static HTML)
Reads tracker.db and writes a self-contained dashboard.html — no server, no
external libraries, opens offline in any browser. Ideal for the workshop demo.

Usage:
  python tools/dashboard.py            # writes my_job_data_center/dashboard.html
  python tools/dashboard.py --open     # write + open in default browser
"""

import sys
import json
import sqlite3
import webbrowser
from pathlib import Path
from datetime import datetime
from collections import Counter, OrderedDict

DB_PATH = Path(__file__).parent.parent / "my_job_data_center" / "tracker.db"
OUT_PATH = Path(__file__).parent.parent / "my_job_data_center" / "dashboard.html"

# Canonical pipeline order (funnel). Anything unrecognized falls to the end.
PIPELINE = ["drafted", "applied", "responded", "assessment", "interview", "offer", "rejected"]


def load(db):
    apps = [dict(zip(["id", "applied_at", "title", "company", "url", "fit_score", "status", "notes"], r))
            for r in db.execute(
                "SELECT id,applied_at,title,company,url,fit_score,status,notes FROM applications ORDER BY applied_at")]
    outreach = [dict(zip(["sent_at", "person", "title", "company", "status"], r))
                for r in db.execute(
                    "SELECT sent_at,person_name,person_title,company,status FROM outreach ORDER BY sent_at")]
    return apps, outreach


def build_model(apps, outreach):
    total = len(apps)
    fits = [a["fit_score"] for a in apps if a.get("fit_score") is not None]
    avg_fit = round(sum(fits) / len(fits)) if fits else 0

    # Pipeline counts in canonical order
    status_counts = Counter((a.get("status") or "unknown").lower() for a in apps)
    pipeline = OrderedDict()
    for s in PIPELINE:
        if status_counts.get(s):
            pipeline[s] = status_counts[s]
    for s, c in status_counts.items():
        if s not in pipeline:
            pipeline[s] = c

    # Response rate = anything past "applied" / total
    advanced = sum(status_counts.get(s, 0) for s in ["responded", "assessment", "interview", "offer"])
    resp_rate = round(100 * advanced / total) if total else 0

    # Fit-score buckets
    buckets = OrderedDict([("<60", 0), ("60-69", 0), ("70-79", 0), ("80-89", 0), ("90-100", 0)])
    for f in fits:
        if f < 60: buckets["<60"] += 1
        elif f < 70: buckets["60-69"] += 1
        elif f < 80: buckets["70-79"] += 1
        elif f < 90: buckets["80-89"] += 1
        else: buckets["90-100"] += 1

    # Applications over time (by date)
    by_date = Counter((a["applied_at"] or "")[:10] for a in apps if a.get("applied_at"))
    timeline = OrderedDict(sorted(by_date.items()))

    return {
        "kpis": {"total": total, "avg_fit": avg_fit, "resp_rate": resp_rate, "top_fit": max(fits) if fits else 0},
        "pipeline": pipeline,
        "buckets": buckets,
        "timeline": timeline,
        "apps": apps,
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def render(m):
    data = json.dumps(m, ensure_ascii=False)
    return TEMPLATE.replace("/*DATA*/", data)


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Job Application Dashboard</title>
<style>
:root{--bg:#0f1115;--card:#181b22;--line:#262b36;--txt:#e7eaf0;--mut:#9aa4b2;--accent:#18DD4C;--bar:#3b82f6;}
@media (prefers-color-scheme:light){:root{--bg:#f6f8fa;--card:#fff;--line:#e5e9f0;--txt:#1a1f2b;--mut:#5a6472;--bar:#2563eb;}}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--txt);padding:28px}
h1{font-size:22px;margin:0 0 2px}.sub{color:var(--mut);font-size:13px;margin-bottom:22px}
.grid{display:grid;gap:16px}.kpis{grid-template-columns:repeat(4,1fr)}
@media(max-width:720px){.kpis{grid-template-columns:repeat(2,1fr)}}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.kpi .n{font-size:30px;font-weight:700;letter-spacing:-.5px}.kpi .l{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.5px;margin-top:2px}
.kpi .n.accent{color:var(--accent)}
.cols{grid-template-columns:1fr 1fr;margin-top:16px}@media(max-width:720px){.cols{grid-template-columns:1fr}}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.6px;color:var(--mut);margin:0 0 14px}
.row{display:flex;align-items:center;gap:10px;margin:8px 0}.row .lab{width:92px;font-size:13px;text-transform:capitalize;color:var(--mut)}
.track{flex:1;background:var(--line);border-radius:6px;height:22px;overflow:hidden}
.fill{height:100%;border-radius:6px;background:var(--bar);min-width:2px}
.row .v{width:28px;text-align:right;font-variant-numeric:tabular-nums;font-weight:600}
table{width:100%;border-collapse:collapse;margin-top:16px;font-size:14px}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line)}
th{color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:.5px}
td a{color:var(--bar);text-decoration:none}td a:hover{text-decoration:underline}
.chip{display:inline-block;padding:2px 9px;border-radius:20px;font-size:12px;font-weight:600;text-transform:capitalize}
.fit{font-variant-numeric:tabular-nums;font-weight:600}
.empty{color:var(--mut);text-align:center;padding:30px}
.spark{display:flex;align-items:flex-end;gap:10px;height:90px;margin-top:6px;justify-content:flex-start}
.spark .b{flex:1 1 0;max-width:70px;background:var(--accent);border-radius:4px 4px 0 0;min-height:3px;position:relative}
.spark .b span{position:absolute;bottom:-20px;left:0;right:0;text-align:center;font-size:10px;color:var(--mut)}
</style></head>
<body>
<h1>Job Application Dashboard</h1>
<div class="sub" id="sub"></div>
<div class="grid kpis" id="kpis"></div>
<div class="grid cols">
  <div class="card"><h2>Pipeline by stage</h2><div id="pipeline"></div></div>
  <div class="card"><h2>Fit score distribution</h2><div id="buckets"></div></div>
</div>
<div class="card" style="margin-top:16px"><h2>Applications over time</h2><div class="spark" id="timeline"></div></div>
<div class="card" style="margin-top:16px"><h2>All applications</h2><div id="table"></div></div>
<script>
const M=/*DATA*/;
const STATUS_COLORS={drafted:'#94a3b8',applied:'#3b82f6',responded:'#8b5cf6',assessment:'#ec4899',interview:'#f59e0b',offer:'#18DD4C',rejected:'#ef4444'};
const $=(id)=>document.getElementById(id);
$('sub').textContent=`Generated ${M.generated} · source: tracker.db`;

const k=M.kpis;
$('kpis').innerHTML=[
  ['Applications',k.total,''],
  ['Avg fit score',k.avg_fit,'accent'],
  ['Response rate',k.resp_rate+'%',''],
  ['Top fit score',k.top_fit,'']
].map(([l,n,c])=>`<div class="card kpi"><div class="n ${c}">${n}</div><div class="l">${l}</div></div>`).join('');

function bars(el,obj,colorFn){
  const max=Math.max(1,...Object.values(obj));
  if(!Object.keys(obj).length){el.innerHTML='<div class="empty">No data yet</div>';return;}
  el.innerHTML=Object.entries(obj).map(([lab,v])=>
    `<div class="row"><div class="lab">${lab}</div><div class="track"><div class="fill" style="width:${Math.round(100*v/max)}%;background:${colorFn?colorFn(lab):'var(--bar)'}"></div></div><div class="v">${v}</div></div>`
  ).join('');
}
bars($('pipeline'),M.pipeline,(s)=>STATUS_COLORS[s]||'var(--bar)');
bars($('buckets'),M.buckets);

const tl=M.timeline,tv=Object.values(tl),tmax=Math.max(1,...tv);
$('timeline').innerHTML=Object.keys(tl).length?Object.entries(tl).map(([d,v])=>
  `<div class="b" style="height:${Math.round(100*v/tmax)}%" title="${d}: ${v}"><span>${d.slice(5)}</span></div>`).join(''):'<div class="empty">No data yet</div>';

const rows=M.apps.slice().reverse();
$('table').innerHTML=rows.length?`<table><thead><tr><th>Date</th><th>Title</th><th>Company</th><th>Fit</th><th>Status</th></tr></thead><tbody>${
  rows.map(a=>{const c=STATUS_COLORS[(a.status||'').toLowerCase()]||'#94a3b8';
  const t=a.url?`<a href="${a.url}" target="_blank" rel="noopener">${a.title||''}</a>`:(a.title||'');
  return `<tr><td>${(a.applied_at||'').slice(0,10)}</td><td>${t}</td><td>${a.company||''}</td><td class="fit">${a.fit_score??''}</td><td><span class="chip" style="background:${c}22;color:${c}">${a.status||''}</span></td></tr>`;}).join('')
}</tbody></table>`:'<div class="empty">No applications logged yet. Run: python tools/track.py log \'{...}\'</div>';
</script>
</body></html>"""


if __name__ == "__main__":
    if not DB_PATH.exists():
        print(f"No DB at {DB_PATH}. Log something first with track.py.")
        sys.exit(1)
    db = sqlite3.connect(str(DB_PATH))
    apps, outreach = load(db)
    model = build_model(apps, outreach)
    OUT_PATH.write_text(render(model), encoding="utf-8")
    print(f"Wrote {OUT_PATH}  ({model['kpis']['total']} applications)")
    if "--open" in sys.argv:
        webbrowser.open(OUT_PATH.as_uri())
