from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from .config import DB_PATH, SITE_DIR, SGT
from .storage import connect, init_db, stats

INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>ActiveSG Gym Crowd Analytics</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root{--bg:#f6f7fb;--card:#fff;--ink:#18202a;--muted:#657386;--line:#dde3ea;--accent:#1667d9;--good:#12a150;--warn:#e69500;--bad:#d92d20;--shadow:0 8px 28px rgba(27,39,51,.08)}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;line-height:1.45} header{padding:28px 20px 18px;background:linear-gradient(135deg,#10233f,#1667d9);color:#fff}.wrap{max-width:1180px;margin:0 auto}h1{font-size:clamp(1.7rem,4vw,3rem);margin:0 0 6px}.subtitle{opacity:.88;max-width:850px}.grid{display:grid;gap:16px}.cards{grid-template-columns:repeat(4,minmax(0,1fr));margin-top:-28px;padding:0 20px}.card{background:var(--card);border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow);padding:18px}.metric{font-size:1.7rem;font-weight:800}.label{font-size:.83rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}.main{padding:18px 20px 40px}.panel{background:var(--card);border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow);padding:18px;margin-bottom:16px}.panel h2{margin:0 0 12px;font-size:1.15rem}.controls{display:flex;gap:12px;flex-wrap:wrap;align-items:end}.field{display:flex;flex-direction:column;gap:5px}.field label{font-size:.78rem;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.04em}select,input{min-height:38px;border:1px solid var(--line);border-radius:10px;padding:8px 10px;background:#fff;color:var(--ink)}button{min-height:38px;border:0;border-radius:10px;padding:8px 14px;background:var(--accent);color:#fff;font-weight:700;cursor:pointer}.chart{height:420px}.chart.small{height:320px}.latest{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px}.gym-card{border:1px solid var(--line);border-radius:14px;padding:12px;background:#fbfcfe}.gym-name{font-weight:800;font-size:.92rem}.status{font-size:.85rem;color:var(--muted);margin-top:4px}.pill{display:inline-flex;border-radius:999px;padding:2px 8px;font-size:.74rem;font-weight:800;margin-top:8px}.pill.closed{background:#eef0f2;color:#596474}.pill.good{background:#e8f7ee;color:var(--good)}.pill.warn{background:#fff4df;color:var(--warn)}.pill.bad{background:#ffebe8;color:var(--bad)}.note{color:var(--muted);font-size:.9rem}.footer{color:var(--muted);font-size:.85rem;padding:10px 0 30px}.two{grid-template-columns:1fr 1fr}@media(max-width:900px){.cards,.two{grid-template-columns:1fr 1fr}.chart{height:360px}}@media(max-width:620px){.cards,.two{grid-template-columns:1fr}.main,header{padding-left:14px;padding-right:14px}}
</style>
</head>
<body>
<header><div class="wrap"><h1>ActiveSG Gym Crowd Analytics</h1><div class="subtitle">Silent 6am–10pm Singapore-time logger for ActiveSG gym availability. Dashboard updates from collected snapshots and becomes more useful after a few days of data.</div></div></header>
<main class="wrap main">
<section class="grid cards"><div class="card"><div class="label">Snapshots</div><div class="metric" id="mSnapshots">—</div></div><div class="card"><div class="label">Gyms tracked</div><div class="metric" id="mGyms">—</div></div><div class="card"><div class="label">Records</div><div class="metric" id="mRecords">—</div></div><div class="card"><div class="label">Latest scrape</div><div class="metric" id="mLatest" style="font-size:1.1rem">—</div></div></section>
<section class="panel"><h2>Controls</h2><div class="controls"><div class="field"><label for="gymSelect">Gym</label><select id="gymSelect"><option value="__ALL__">All gyms</option></select></div><div class="field"><label for="windowSelect">Time window</label><select id="windowSelect"><option value="48h">Last 48 hours</option><option value="7d">Last 7 days</option><option value="30d" selected>Last 30 days</option><option value="all">All data</option></select></div><div class="field"><label for="metricSelect">Metric</label><select id="metricSelect"><option value="crowd_score">Crowd score / occupancy</option><option value="is_open">Open status</option></select></div><button id="refreshBtn">Refresh charts</button></div><p class="note">Crowd score uses real percentages/counts when available; otherwise status labels are scored: Closed=0, Low/Available=25, Moderate=50, Crowded/Limited=75, Full=100.</p></section>
<section class="panel"><h2>Trend over time</h2><div id="trendChart" class="chart"></div></section>
<section class="grid two"><section class="panel"><h2>Busiest gyms by average score</h2><div id="rankChart" class="chart small"></div></section><section class="panel"><h2>Average crowd by hour</h2><div id="hourChart" class="chart small"></div></section></section>
<section class="panel"><h2>Gym × hour heatmap</h2><div id="heatmapChart" class="chart"></div></section>
<section class="panel"><h2>Latest snapshot</h2><div id="latestGrid" class="latest"></div></section>
<div class="footer">Source: <a href="https://activesg.gov.sg/gym-pool-crowd">ActiveSG gym/pool crowd page</a>. Data collected by JY's Mac mini for personal analysis; no personal user data is collected.</div>
</main>
<script>
let DATA=null; const $=id=>document.getElementById(id);
function parseTime(x){return new Date(x)}
function scoreValue(row, metric){ if(metric==='is_open') return row.is_open===null?null:(row.is_open?100:0); return row.crowd_score ?? row.occupancy_pct ?? null; }
function fmtTime(s){ if(!s) return '—'; return new Date(s).toLocaleString('en-SG',{timeZone:'Asia/Singapore',month:'short',day:'2-digit',hour:'2-digit',minute:'2-digit'}); }
function filterRows(){ const gym=$('gymSelect').value, win=$('windowSelect').value; let rows=DATA.observations.slice(); if(gym!=='__ALL__') rows=rows.filter(r=>r.gym_name===gym); if(win!=='all' && rows.length){ const latest=Math.max(...DATA.observations.map(r=>parseTime(r.fetched_at_sgt).getTime())); const hours=win==='48h'?48:win==='7d'?24*7:24*30; const cutoff=latest-hours*3600*1000; rows=rows.filter(r=>parseTime(r.fetched_at_sgt).getTime()>=cutoff); } return rows; }
function initControls(){ const gyms=[...new Set(DATA.observations.map(r=>r.gym_name))].sort(); for(const g of gyms){ const opt=document.createElement('option'); opt.value=g; opt.textContent=g; $('gymSelect').appendChild(opt); } for(const id of ['refreshBtn','gymSelect','windowSelect','metricSelect']) $(id).addEventListener(id==='refreshBtn'?'click':'change', renderAll); }
function renderMetrics(){ $('mSnapshots').textContent=DATA.meta.snapshot_count.toLocaleString(); $('mGyms').textContent=DATA.meta.gym_count.toLocaleString(); $('mRecords').textContent=DATA.meta.observation_count.toLocaleString(); $('mLatest').textContent=fmtTime(DATA.meta.last_fetched_at_sgt); }
function avg(arr){return arr.length?arr.reduce((a,b)=>a+b,0)/arr.length:null}
function renderTrend(rows){ const metric=$('metricSelect').value, gym=$('gymSelect').value; if(gym==='__ALL__'){ const buckets=new Map(); for(const r of rows){ const v=scoreValue(r,metric); if(v===null) continue; const k=r.fetched_at_sgt; if(!buckets.has(k)) buckets.set(k,[]); buckets.get(k).push(v); } const x=[...buckets.keys()].sort(), y=x.map(k=>avg(buckets.get(k))); Plotly.newPlot('trendChart',[{x,y,type:'scatter',mode:'lines+markers',line:{color:'#1667d9'},name:'Average score'}],{margin:{t:20,r:20,l:45,b:45},yaxis:{title:'Score',range:[0,100]},xaxis:{title:'Time (SGT)'}},{responsive:true,displayModeBar:false}); } else { const x=rows.map(r=>r.fetched_at_sgt), y=rows.map(r=>scoreValue(r,metric)); Plotly.newPlot('trendChart',[{x,y,type:'scatter',mode:'lines+markers',line:{color:'#1667d9'},name:gym}],{margin:{t:20,r:20,l:45,b:45},yaxis:{title:'Score',range:[0,100]},xaxis:{title:'Time (SGT)'}},{responsive:true,displayModeBar:false}); } }
function renderRank(rows){ const metric=$('metricSelect').value, by=new Map(); for(const r of rows){ const v=scoreValue(r,metric); if(v===null) continue; if(!by.has(r.gym_name)) by.set(r.gym_name,[]); by.get(r.gym_name).push(v); } const ranked=[...by.entries()].map(([g,vals])=>[g,avg(vals)]).sort((a,b)=>b[1]-a[1]).slice(0,12).reverse(); Plotly.newPlot('rankChart',[{x:ranked.map(x=>x[1]),y:ranked.map(x=>x[0]),type:'bar',orientation:'h',marker:{color:'#1667d9'}}],{margin:{t:8,r:20,l:150,b:35},xaxis:{range:[0,100],title:'Avg score'}},{responsive:true,displayModeBar:false}); }
function hourOf(r){return new Date(r.fetched_at_sgt).toLocaleString('en-SG',{timeZone:'Asia/Singapore',hour:'2-digit',hour12:false})}
function renderHours(rows){ const metric=$('metricSelect').value, by=new Map(); for(const r of rows){ const v=scoreValue(r,metric); if(v===null) continue; const h=hourOf(r); if(!by.has(h)) by.set(h,[]); by.get(h).push(v); } const hours=[...by.keys()].sort(), vals=hours.map(h=>avg(by.get(h))); Plotly.newPlot('hourChart',[{x:hours,y:vals,type:'bar',marker:{color:vals.map(v=>v>70?'#d92d20':v>45?'#e69500':'#12a150')}}],{margin:{t:8,r:20,l:45,b:35},yaxis:{range:[0,100],title:'Avg score'},xaxis:{title:'Hour'}},{responsive:true,displayModeBar:false}); }
function renderHeatmap(rows){ const metric=$('metricSelect').value, gyms=[...new Set(rows.map(r=>r.gym_name))].sort(), hours=[...new Set(rows.map(hourOf))].sort(); const matrix=gyms.map(g=>hours.map(h=>avg(rows.filter(r=>r.gym_name===g && hourOf(r)===h).map(r=>scoreValue(r,metric)).filter(v=>v!==null)))); Plotly.newPlot('heatmapChart',[{z:matrix,x:hours,y:gyms,type:'heatmap',colorscale:[[0,'#e8f7ee'],[.45,'#fff4df'],[.75,'#ffb86b'],[1,'#d92d20']],zmin:0,zmax:100,colorbar:{title:'Score'}}],{margin:{t:10,r:20,l:190,b:45},xaxis:{title:'Hour'},height:Math.max(420,gyms.length*22+120)},{responsive:true,displayModeBar:false}); }
function escapeHtml(s){return String(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));}
function renderLatest(){ const latestTs=DATA.meta.last_fetched_at_sgt, latest=DATA.observations.filter(r=>r.fetched_at_sgt===latestTs).sort((a,b)=>a.gym_name.localeCompare(b.gym_name)); $('latestGrid').innerHTML=latest.map(r=>{ const s=r.crowd_score??r.occupancy_pct; const klass=(r.is_open===false)?'closed':s>=75?'bad':s>=45?'warn':'good'; const label=r.is_open===false?'Closed':(s==null?'Open / unknown':Math.round(s)+' score'); const loc=r.gym_location?`<div class="status"><strong>Location:</strong> ${escapeHtml(r.gym_location)}</div>`:''; return `<div class="gym-card"><div class="gym-name">${escapeHtml(r.gym_name)}</div>${loc}<div class="status">${escapeHtml(r.status_text)}</div><span class="pill ${klass}">${label}</span></div>`}).join(''); }
function renderAll(){ const rows=filterRows(); renderTrend(rows); renderRank(rows); renderHours(rows); renderHeatmap(rows); renderLatest(); }
fetch('data/observations.json?ts='+Date.now()).then(r=>r.json()).then(d=>{DATA=d; renderMetrics(); initControls(); renderAll();}).catch(err=>{document.body.innerHTML='<main class="wrap main"><section class="panel"><h1>Data load failed</h1><pre>'+String(err)+'</pre></section></main>';});
</script>
</body>
</html>
"""

def export_data(db_path: Path = DB_PATH, site_dir: Path = SITE_DIR) -> dict:
    init_db(db_path)
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "data").mkdir(parents=True, exist_ok=True)
    st = stats(db_path)
    with connect(db_path) as conn:
        rows = conn.execute("""
            SELECT fetched_at_utc, fetched_at_sgt, gym_name, gym_location, status_text, is_open,
                   capacity_current, capacity_total, occupancy_pct, crowd_score, source_detail
            FROM observations ORDER BY fetched_at_sgt, gym_name
        """).fetchall()
    obs = []
    for r in rows:
        item = dict(r)
        item["is_open"] = None if item["is_open"] is None else bool(item["is_open"])
        obs.append(item)
    payload = {"generated_at_sgt": datetime.now(timezone.utc).astimezone(SGT).isoformat(), "meta": st, "observations": obs}
    (site_dir / "data" / "observations.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (site_dir / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    return payload
