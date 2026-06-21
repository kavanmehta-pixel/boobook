from __future__ import annotations
from pathlib import Path
import json
import pandas as pd

HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Ninox — Source Data Validation Dashboard</title>
<style>
:root { --bg:#04101d; --panel:#0b1f33; --panel2:#102941; --text:#e8eef3; --muted:#9db0be; --accent:#13a89e; --warn:#d85a30; --mid:#e6a23c; --ok:#1d9e75; }
* { box-sizing: border-box; } body { margin:0; background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Arial,sans-serif; }
header { padding:20px 24px; border-bottom:1px solid #173855; background:linear-gradient(90deg,#061523,#0b1f33); }
h1 { margin:0; font-size:24px; letter-spacing:.5px; } .sub { color:var(--muted); margin-top:6px; font-size:13px; max-width:980px; }
.warnbar { margin-top:12px; padding:10px 12px; background:#2a1b12; border:1px solid #72411e; color:#ffd7b0; border-radius:8px; font-size:13px; }
.grid { display:grid; grid-template-columns: 280px 1fr 420px; gap:14px; padding:14px; }
.card { background:var(--panel); border:1px solid #173855; border-radius:12px; padding:14px; box-shadow:0 10px 30px rgba(0,0,0,.18); }
.kpis { display:grid; grid-template-columns:1fr 1fr; gap:10px; } .kpi { background:var(--panel2); border-radius:10px; padding:12px; }
.kpi b { display:block; font-size:24px; color:var(--accent); } .kpi span { color:var(--muted); font-size:12px; }
#map { position:relative; height:620px; overflow:hidden; background:radial-gradient(circle at 60% 45%,#10304b,#061523 70%); border-radius:12px; border:1px solid #173855; }
svg { width:100%; height:100%; display:block; }
.table { width:100%; border-collapse:collapse; font-size:12px; } .table th,.table td { padding:8px; border-bottom:1px solid #173855; text-align:left; vertical-align:top; }
.table th { color:var(--muted); font-weight:600; } .tag { display:inline-block; padding:3px 7px; border-radius:999px; font-size:11px; font-weight:700; }
.HIGH { background:#3a1715; color:#ff9a88; } .MEDIUM { background:#372815; color:#ffd48a; } .LOW { background:#143123; color:#8ce5bd; }
.small { color:var(--muted); font-size:12px; line-height:1.45; } code { color:#b9f3ee; }
.upload { margin-top:10px; border:1px dashed #315875; padding:10px; border-radius:10px; color:var(--muted); font-size:12px; }
input[type=file] { margin-top:8px; width:100%; }
footer { padding:12px 24px 24px; color:var(--muted); font-size:12px; }
@media (max-width:1100px){ .grid{grid-template-columns:1fr;} #map{height:520px;} }
</style>
</head>
<body>
<header>
<h1>NINOX — Source Data Validation Dashboard</h1>
<div class="sub">AIS-only validation MVP using AMSA/CTS-style vessel traffic data. This dashboard validates the analytics workflow before passive RF/TDOA field testing.</div>
<div class="warnbar"><b>SIMULATED / LOCAL SOURCE-DATA MODE:</b> AIS anomalies are not proof of illegal behaviour. Passive RF detection is not shown unless connected to live SDR/field-tested inputs.</div>
</header>
<div class="grid">
<section class="card">
<h3>Validation Summary</h3>
<div class="kpis">
<div class="kpi"><b id="rows">0</b><span>AIS rows</span></div>
<div class="kpi"><b id="vessels">0</b><span>vessels</span></div>
<div class="kpi"><b id="alerts">0</b><span>alerts</span></div>
<div class="kpi"><b id="high">0</b><span>high risk</span></div>
</div>
<div class="upload">
<b>Upload another normalised CSV</b><br />
Columns expected: <code>mmsi,timestamp,lat,lon,sog,cog,vessel_name,vessel_type</code>. For raw AMSA/CTS files, run <code>ninox validate-ais</code> first.
<input type="file" id="fileInput" accept=".csv" />
</div>
<p class="small" style="margin-top:14px">Best investor demo: run the CLI on a real AMSA monthly extract, then regenerate this dashboard with the produced <code>alerts.csv</code>, <code>vessels.csv</code> and <code>tracks.geojson</code>.</p>
</section>
<section class="card"><div id="map"></div></section>
<section class="card">
<h3>Prioritised Alerts</h3>
<table class="table" id="alertTable"><thead><tr><th>Risk</th><th>Alert</th><th>Evidence</th></tr></thead><tbody></tbody></table>
<h3 style="margin-top:18px">Vessels</h3>
<table class="table" id="vesselTable"><thead><tr><th>MMSI</th><th>Name</th><th>Risk</th></tr></thead><tbody></tbody></table>
</section>
</div>
<footer>Ninox MVP v0.3 — AIS validation now, passive RF/TDOA validation next.</footer>
<script>
const DATA = __DATA__;
function project(lon, lat, b, w, h){
  const pad=40; const x=pad+(lon-b.minLon)/(b.maxLon-b.minLon||1)*(w-2*pad); const y=h-pad-(lat-b.minLat)/(b.maxLat-b.minLat||1)*(h-2*pad); return [x,y];
}
function render(data){
  document.getElementById('rows').textContent=data.summary.rows||0; document.getElementById('vessels').textContent=data.summary.vessels||0; document.getElementById('alerts').textContent=data.summary.alerts||0; document.getElementById('high').textContent=data.summary.high_alerts||0;
  const pts=[]; data.tracks.features.forEach(f=>f.geometry.coordinates.forEach(c=>pts.push(c))); let b={minLon:141.7,maxLon:142.7,minLat:-10.9,maxLat:-10.0}; if(pts.length){b.minLon=Math.min(...pts.map(p=>p[0])); b.maxLon=Math.max(...pts.map(p=>p[0])); b.minLat=Math.min(...pts.map(p=>p[1])); b.maxLat=Math.max(...pts.map(p=>p[1])); const dx=(b.maxLon-b.minLon)*.15||.1, dy=(b.maxLat-b.minLat)*.15||.1; b.minLon-=dx;b.maxLon+=dx;b.minLat-=dy;b.maxLat+=dy;}
  const map=document.getElementById('map'); const w=map.clientWidth||800, h=map.clientHeight||600; let svg=`<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg"><defs><filter id="glow"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs><rect width="100%" height="100%" fill="transparent"/>`;
  svg += `<text x="20" y="28" fill="#9db0be" font-size="12">Track map — equirectangular planning view, not nautical chart</text>`;
  data.tracks.features.forEach((f,idx)=>{ const risk=f.properties.risk_score||0; const color=risk>=80?'#d85a30':risk>=55?'#e6a23c':'#13a89e'; const d=f.geometry.coordinates.map((c,i)=>{const p=project(c[0],c[1],b,w,h); return `${i?'L':'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`}).join(' '); svg += `<path d="${d}" fill="none" stroke="${color}" stroke-width="3" opacity=".9" filter="url(#glow)"/>`; const last=f.geometry.coordinates[f.geometry.coordinates.length-1]; if(last){const p=project(last[0],last[1],b,w,h); svg += `<circle cx="${p[0]}" cy="${p[1]}" r="5" fill="${color}"/><text x="${p[0]+8}" y="${p[1]-8}" fill="#e8eef3" font-size="11">${f.properties.mmsi}</text>`; }});
  data.alerts.forEach(a=>{const p=project(+a.lon,+a.lat,b,w,h); svg+=`<circle cx="${p[0]}" cy="${p[1]}" r="11" fill="none" stroke="#ff8a80" stroke-width="2" opacity=".8"><animate attributeName="r" values="8;18;8" dur="2s" repeatCount="indefinite"/></circle>`});
  svg += `</svg>`; map.innerHTML=svg;
  const at=document.querySelector('#alertTable tbody'); at.innerHTML=''; data.alerts.slice(0,12).forEach(a=>{at.insertAdjacentHTML('beforeend',`<tr><td><span class="tag ${a.severity}">${a.risk_score}</span></td><td><b>${a.alert_type}</b><br>${a.title}<br><span class="small">${a.mmsi} · ${a.timestamp}</span></td><td>${a.explanation}<br><span class="small">${a.evidence}</span></td></tr>`)});
  const vt=document.querySelector('#vesselTable tbody'); vt.innerHTML=''; data.vessels.forEach(v=>{const sev=v.risk_score>=80?'HIGH':v.risk_score>=55?'MEDIUM':'LOW'; vt.insertAdjacentHTML('beforeend',`<tr><td>${v.mmsi}</td><td>${v.vessel_name||''}<br><span class="small">${v.vessel_type||''}</span></td><td><span class="tag ${sev}">${v.risk_score}</span></td></tr>`)});
}
render(DATA);
function parseCSV(text){const lines=text.trim().split(/\r?\n/); const headers=lines.shift().split(',').map(h=>h.trim()); return lines.map(line=>{const vals=line.split(','); const o={}; headers.forEach((h,i)=>o[h]=vals[i]); return o;});}
document.getElementById('fileInput').addEventListener('change', async e=>{ const f=e.target.files[0]; if(!f) return; const rows=parseCSV(await f.text()); alert('Uploaded '+rows.length+' rows. For full anomaly detection, run the Python CLI and regenerate the dashboard.'); });
</script>
</body>
</html>
"""


def _read_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def export_dashboard(processed_dir: str | Path, output_path: str | Path) -> Path:
    p = Path(processed_dir)
    alerts = pd.read_csv(p / "alerts.csv").to_dict("records") if (p / "alerts.csv").exists() else []
    vessels = pd.read_csv(p / "vessels.csv").to_dict("records") if (p / "vessels.csv").exists() else []
    tracks = _read_json(p / "tracks.geojson", {"type": "FeatureCollection", "features": []})
    summary = _read_json(p / "summary.json", {"rows": 0, "vessels": 0, "alerts": 0, "high_alerts": 0})
    data = {"summary": summary, "alerts": alerts, "vessels": vessels, "tracks": tracks}
    html = HTML_TEMPLATE.replace("__DATA__", json.dumps(data, default=str))
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out
