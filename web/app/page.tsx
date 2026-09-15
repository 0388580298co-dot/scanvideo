"use client";

import { FormEvent, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Job = { job_id:string; status:string; source_url:string; progress:number; message:string; output_path?:string|null; error?:string|null; };
type Schedule = { id:number; job_id:string; platform:string; scheduled_at:string; status:string; title:string; description:string; account_id:number|null };
type Published = { id:number; platform:string; external_id:string|null; published_at:string|null; metrics:Record<string,unknown> };
type Summary = { total_jobs:number; by_status:Record<string,number> };
type AnalyticsSummary = { published_total:number; by_platform:Record<string,number> };

export default function Home() {
  const [jobs,setJobs]=useState<Job[]>([]); const [summary,setSummary]=useState<Summary>({total_jobs:0,by_status:{}});
  const [schedules,setSchedules]=useState<Schedule[]>([]); const [published,setPublished]=useState<Published[]>([]); const [analytics,setAnalytics]=useState<AnalyticsSummary>({published_total:0,by_platform:{}});
  const [url,setUrl]=useState(""); const [loading,setLoading]=useState(false); const [error,setError]=useState("");
  async function refresh(){const [j,s,sc,p,a]=await Promise.all([fetch(`${API}/api/v1/jobs`,{cache:"no-store"}),fetch(`${API}/api/v1/dashboard/summary`,{cache:"no-store"}),fetch(`${API}/api/v1/schedule`,{cache:"no-store"}),fetch(`${API}/api/v1/analytics/published?limit=20`,{cache:"no-store"}),fetch(`${API}/api/v1/analytics/summary`,{cache:"no-store"})]); if(!j.ok||!s.ok||!sc.ok||!p.ok||!a.ok) throw new Error("API unavailable"); setJobs(await j.json()); setSummary(await s.json()); setSchedules(await sc.json()); setPublished(await p.json()); setAnalytics(await a.json());}
  useEffect(()=>{refresh().catch(e=>setError(e.message)); const timer=setInterval(()=>refresh().catch(()=>{}),5000); return()=>clearInterval(timer)},[]);
  async function submit(e:FormEvent){e.preventDefault(); if(!url.trim()) return; setLoading(true);setError(""); try{const r=await fetch(`${API}/api/v1/jobs`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({source_url:url.trim(),target_language:"vi",auto_publish:false})}); if(!r.ok) throw new Error(await r.text()); setUrl(""); await refresh()}catch(e){setError(e instanceof Error?e.message:"Request failed")}finally{setLoading(false)}}
  async function cancel(id:number){setError(""); try{const r=await fetch(`${API}/api/v1/schedule/${id}/cancel`,{method:"POST"}); if(!r.ok) throw new Error(await r.text()); await refresh()}catch(e){setError(e instanceof Error?e.message:"Cancel failed")}}
  const statuses=["DOWNLOADING","TRANSCRIBING","TRANSLATING","SYNTHESIZING","RENDERING","COMPLETED","FAILED"];
  return <main><h1>ScanVideo</h1><p className="muted">Local-first AI video automation</p>{error&&<div className="card">{error}</div>}
    <form className="form" onSubmit={submit}><input value={url} onChange={e=>setUrl(e.target.value)} placeholder="https://source-video-url"/><button className="button" disabled={loading}>{loading?"Queueing…":"Create job"}</button></form>
    <section className="grid"><div className="card"><div className="muted">Total jobs</div><h2>{summary.total_jobs}</h2></div>{statuses.slice(0,3).map(s=><div className="card" key={s}><div className="muted">{s}</div><h2>{summary.by_status[s]??0}</h2></div>)}<div className="card"><div className="muted">Published</div><h2>{analytics.published_total}</h2></div></section>
    <h2>Jobs</h2><table className="table"><thead><tr><th>Job</th><th>Status</th><th>Progress</th><th>Message</th></tr></thead><tbody>{jobs.map(j=><tr key={j.job_id}><td>{j.job_id.slice(0,12)}</td><td><span className="badge">{j.status}</span></td><td>{j.progress}%</td><td>{j.message}</td></tr>)}</tbody></table>
    <h2>Schedule</h2><table className="table"><thead><tr><th>Platform</th><th>Job</th><th>When</th><th>Status</th><th></th></tr></thead><tbody>{schedules.map(s=><tr key={s.id}><td>{s.platform}</td><td>{s.job_id.slice(0,12)}</td><td>{new Date(s.scheduled_at).toLocaleString()}</td><td><span className="badge">{s.status}</span></td><td>{s.status==="SCHEDULED"&&<button className="button" onClick={()=>cancel(s.id)}>Cancel</button>}</td></tr>)}</tbody></table>
    <h2>Published & Analytics</h2><table className="table"><thead><tr><th>Platform</th><th>External ID</th><th>Published</th><th>Views</th><th>Likes</th><th>Comments</th></tr></thead><tbody>{published.map(p=>{const m=p.metrics||{}; return <tr key={p.id}><td>{p.platform}</td><td>{p.external_id||"—"}</td><td>{p.published_at?new Date(p.published_at).toLocaleString():"—"}</td><td>{String(m.views??"—")}</td><td>{String(m.likes??"—")}</td><td>{String(m.comments??"—")}</td></tr>})}</tbody></table>
  </main>;
}
