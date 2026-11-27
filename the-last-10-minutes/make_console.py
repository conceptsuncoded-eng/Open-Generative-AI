#!/usr/bin/env python3
"""Builds console.html: a self-contained, mobile-first shot renderer.

Everything runs in the user's browser, which is outside this sandbox's egress
filter. Regenerate after editing shots.csv or prompts/.
"""
import csv, json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(ROOT, "shots.csv"))))

shots = []
for r in rows:
    sid = r["shot"]
    prompt = open(os.path.join(ROOT, "prompts", sid + ".txt")).read().strip()
    refs = [n.strip() for n in r["reference_images"].split(",")
            if n.strip().lower() not in ("", "none")]
    shots.append({
        "id": sid, "seq": int(r["sequence"].split()[-1]), "start": r["start"], "end": r["end"],
        "model": r["primary_model"], "dur": int(round(float(r["avg_clip_seconds"]))),
        "refs": refs, "prompt": prompt, "act": r["action"], "audio": r["audio"],
    })

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>THE LAST 10 MINUTES — shot console</title>
<style>
:root{--bg:#0b0d10;--card:#14181d;--line:#242a31;--ink:#e8edf2;--dim:#8c98a4;--lime:#c6f24e;--red:#ff5f56;--amber:#ffb020}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;padding-bottom:60px}
header{position:sticky;top:0;z-index:9;background:rgba(11,13,16,.94);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:12px 14px}
h1{font-size:15px;margin:0 0 2px;letter-spacing:.14em;text-transform:uppercase}
.sub{color:var(--dim);font-size:12px;margin-bottom:10px}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
input[type=password],input[type=text]{flex:1;min-width:150px;background:#0e1116;border:1px solid var(--line);color:var(--ink);padding:10px;border-radius:9px;font-size:14px}
button{background:var(--lime);color:#0b0d10;border:0;font-weight:700;padding:10px 14px;border-radius:9px;font-size:14px;cursor:pointer}
button.ghost{background:transparent;color:var(--ink);border:1px solid var(--line);font-weight:500}
button:disabled{opacity:.45;cursor:not-allowed}
main{max-width:760px;margin:0 auto;padding:14px}
.seq{margin:22px 0 10px;font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--lime);border-bottom:1px solid var(--line);padding-bottom:6px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin-bottom:12px}
.top{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
.sid{font-weight:800;letter-spacing:.04em}
.tc{color:var(--dim);font-size:12px;margin-left:6px;font-weight:400}
.model{font-size:11px;color:var(--dim);margin-top:3px;word-break:break-all}
.act{margin:9px 0;font-size:14px}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}
.chip{font-size:11px;border:1px solid var(--line);border-radius:20px;padding:3px 9px;color:var(--dim)}
.thumb{width:64px;height:38px;object-fit:cover;border-radius:6px;border:1px solid var(--line)}
details{margin:8px 0}
summary{cursor:pointer;color:var(--dim);font-size:12px}
pre{white-space:pre-wrap;word-break:break-word;font-size:11.5px;line-height:1.45;color:#b9c4cf;background:#0e1116;padding:10px;border-radius:9px;border:1px solid var(--line);max-height:230px;overflow:auto}
.status{font-size:12px;margin-top:8px;color:var(--dim);min-height:16px}
.status.err{color:var(--red)}
.status.ok{color:var(--lime)}
video{width:100%;border-radius:10px;margin-top:10px;background:#000}
a.dl{display:inline-block;margin-top:8px;font-size:12px;color:var(--lime)}
.warn{background:#1c1508;border:1px solid #4a3608;color:var(--amber);padding:10px 12px;border-radius:10px;font-size:12.5px;margin-bottom:12px}
.bar{display:flex;gap:8px;margin-top:8px}
</style></head><body>
<header>
  <h1>The Last 10 Minutes</h1>
  <div class="sub" id="sub">31 shots · 82 clips · 10:00</div>
  <div class="row">
    <input type="password" id="key" placeholder="MuAPI key (stays on this device)" autocomplete="off">
    <button class="ghost" id="save">Save</button>
  </div>
  <div class="bar">
    <button class="ghost" id="seqBtn">Render Sequence 1</button>
    <button class="ghost" id="stopBtn" hidden>Stop</button>
  </div>
</header>
<main>
  <div class="warn" id="warn" hidden></div>
  <div id="list"></div>
</main>
<script>
const SHOTS = __SHOTS__;
const REF_FILE = {ETHAN:"ETHAN_COLE_reference_sheet.png",VICTOR:"VICTOR_HALE_reference_sheet.png",MAYA:"MAYA_REED_reference_sheet.png",DANIEL:"DANIEL_COLE_reference_sheet.png"};
const REF_DIR = "01_CHARACTER_REFERENCES/";
const SPEC = {
  "minimax-h3-reference-to-video":{ref:"reference_images",list:true,extra:{resolution:"2k"},min:5,max:12},
  "seedance-2.5-omni-reference-1080p":{ref:"images_list",list:true,extra:{omni_reference_task_type:"reference"},min:4,max:30},
  "veo-4-text-to-video":{ref:null,list:false,extra:{},min:5,max:30},
  "wan3.0-image-to-video":{ref:"image_url",list:false,extra:{resolution:"1080p"},min:2,max:30}
};
// same-origin when served by serve.py (proxy mode); direct API otherwise
const BASE = (location.hostname === "localhost" || location.hostname === "127.0.0.1" || location.protocol === "file:") ? "" : "https://api.muapi.ai";
const store = {
  get k(){return localStorage.getItem("muapi_key")||""},
  set k(v){localStorage.setItem("muapi_key",v)},
  clips(){try{return JSON.parse(localStorage.getItem("tlm_clips")||"{}")}catch(e){return {}}},
  save(id,url){const c=this.clips();c[id]=url;localStorage.setItem("tlm_clips",JSON.stringify(c))}
};
const $ = (s,r=document)=>r.querySelector(s);
let stopped=false;

// ---- build UI ----
const keyEl=$("#key"); keyEl.value=store.k;
$("#save").onclick=()=>{store.k=keyEl.value.trim();flash("Key saved on this device");};
if(!store.k) $("#warn").hidden=false;
if(location.protocol==="https:" && BASE.startsWith("https")){
  $("#warn").hidden=false;
  $("#warn").textContent="Calling api.muapi.ai from this page. If generation fails with a network/CORS error, run `python3 the-last-10-minutes/serve.py` on your computer and open the page from there — it proxies the API same-origin.";
}
let html="",lastSeq=0;
for(const s of SHOTS){
  if(s.seq!==lastSeq){html+=`<div class="seq">Sequence ${s.seq}</div>`;lastSeq=s.seq;}
  html+=`<div class="card" id="c_${s.id}">
    <div class="top"><div>
      <div class="sid">${s.id}<span class="tc">${s.start}–${s.end} · ${s.dur}s</span></div>
      <div class="model">${s.model}</div>
    </div></div>
    <div class="act">${esc(s.act)}</div>
    <div class="chips">${s.refs.map(r=>`<span class="chip">${r}</span>`).join("")||'<span class="chip">no cast</span>'}
      ${s.audio?`<span class="chip">${esc(s.audio)}</span>`:""}</div>
    ${s.refs.length?`<div class="chips">${s.refs.map(r=>`<img class="thumb" src="${REF_DIR+REF_FILE[r]}" alt="${r}">`).join("")}</div>`:""}
    <details><summary>Prompt</summary><pre>${esc(s.prompt)}</pre></details>
    <button data-go="${s.id}">Generate</button>
    <div class="status" id="st_${s.id}"></div>
    <div id="out_${s.id}"></div>
  </div>`;
}
$("#list").innerHTML=html;
$("#sub").textContent=`${SHOTS.length} shots · ${SHOTS.filter(s=>s.seq===1).length} in Sequence 1`;

const clips=store.clips();
for(const id in clips) showClip(id, clips[id]);

document.addEventListener("click",e=>{
  const id=e.target.dataset?.go;
  if(id) generate(id).catch(err=>setStatus(id,err.message,true));
});
$("#seqBtn").onclick=async()=>{
  stopped=false; $("#stopBtn").hidden=false; $("#seqBtn").disabled=true;
  for(const s of SHOTS.filter(x=>x.seq===1)){
    if(stopped) break;
    if(store.clips()[s.id]) continue;
    try{ await generate(s.id); }catch(err){ setStatus(s.id, err.message, true); }
  }
  $("#stopBtn").hidden=true; $("#seqBtn").disabled=false;
};
$("#stopBtn").onclick=()=>{stopped=true;};

// ---- helpers ----
function esc(t){return String(t).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]))}
function flash(m){const w=$("#warn");w.hidden=false;w.style.color="var(--lime)";w.textContent=m;setTimeout(()=>{w.hidden=true},1600)}
function setStatus(id,msg,err){const el=$("#st_"+id);el.textContent=msg;el.className="status"+(err?" err":"");}
function setOk(id,msg){const el=$("#st_"+id);el.textContent=msg;el.className="status ok";}
function showClip(id,url){
  $("#out_"+id).innerHTML=`<video controls playsinline preload="metadata" src="${url}"></video><a class="dl" href="${url}" download="${id}.mp4" target="_blank" rel="noopener">Download ${id}.mp4</a>`;
}
function auth(){const k=(keyEl.value||"").trim();if(!k) throw new Error("Paste your MuAPI key at the top first.");return k}

async function api(path, opts={}){
  const res=await fetch(BASE+path,{...opts,headers:{...(opts.headers||{}),"x-api-key":auth()}});
  const txt=await res.text();
  let body={}; try{body=JSON.parse(txt)}catch(e){}
  if(!res.ok){
    if(res.status===401||res.status===403) throw new Error("Key rejected (401/403). Check it and its credit balance.");
    if(res.status===402) throw new Error("Insufficient credits (402). Top up at muapi.ai.");
    throw new Error(`${res.status}: ${txt.slice(0,140)}`);
  }
  return body;
}

async function uploadRef(character){
  const path=REF_DIR+REF_FILE[character];
  const blob=await (await fetch(path)).blob();
  const fd=new FormData();
  fd.append("file",blob,REF_FILE[character]);
  const d=await api("/api/v1/upload_file",{method:"POST",body:fd});
  const url=d.url||d.file_url||(d.data&&d.data.url);
  if(!url) throw new Error("Upload returned no URL");
  return url;
}

const refCache={};
async function generate(sid){
  const s=SHOTS.find(x=>x.id===sid), spec=SPEC[s.model];
  const btn=document.querySelector(`[data-go="${sid}"]`); btn.disabled=true;
  try{
    const body={prompt:s.prompt,aspect_ratio:"16:9",duration:Math.max(spec.min,Math.min(spec.max,s.dur)),...spec.extra};
    if(spec.ref && s.refs.length){
      const urls=[];
      for(const r of s.refs){
        setStatus(sid,`Uploading ${r}…`);
        urls.push(refCache[r] || (refCache[r]=await uploadRef(r)));
      }
      body[spec.ref]=spec.list?urls:urls[0];
    }
    setStatus(sid,"Submitting…");
    const sub=await api(`/api/v1/${s.model}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
    const rid=sub.request_id||sub.id;
    if(!rid) throw new Error("No request id returned");
    const t0=Date.now();
    while(Date.now()-t0 < 25*60*1000){
      await new Promise(r=>setTimeout(r,5000));
      const r=await api(`/api/v1/predictions/${rid}/result`);
      const st=String(r.status||"").toLowerCase();
      if(["completed","succeeded","success"].includes(st)){
        const url=(r.outputs&&r.outputs[0])||r.url||(r.output&&r.output.url);
        if(!url) throw new Error("Completed but no video URL");
        store.save(sid,url); showClip(sid,url); setOk(sid,"Done ✓");
        return url;
      }
      if(["failed","error","cancelled","canceled"].includes(st)) throw new Error("Generation failed: "+JSON.stringify(r).slice(0,160));
      setStatus(sid,`${st||"queued"} · ${Math.round((Date.now()-t0)/1000)}s`);
    }
    throw new Error("Timed out after 25 minutes");
  }finally{ btn.disabled=false; }
}
</script></body></html>
"""

html = TEMPLATE.replace("__SHOTS__", json.dumps(shots, indent=1))
open(os.path.join(ROOT, "console.html"), "w").write(html)
print(f"console.html written: {len(html)} bytes, {len(shots)} shots")
