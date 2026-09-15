"use client";

import { FormEvent, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Job = { job_id:string; status:string; source_url:string; progress:number; message:string; output_path?:string|null; error?:string|null; };

type Summary = { total_jobs:number; by_status:Record<string,number> };

export default function Home() {
  const [jobs,setJobs]=useState<Job[]>([]); const [summary,setSummary]=useState<Summary>({total_jobs:0,by_status:{}}); const [url,setUrl]=useState(""); const [loading,setLoading]=useState(false); const [error,setError]=useState("");
  async function refresh(){const [j,s]=await Promise.all([fetch(`${API}/api/v1/jobs`,{cache:"no-store"}),fetch(`${API}/api/v1/dashboard/summary`,{cache:"no-store"})]); if(!j.ok||!s.ok) throw new Error("API unavailable"); setJobs(await j.json()); setSummary(await s.json());}
  useEffect(()=>{refresh().catch(e=>setError(e.message)); const timer=setInterval(()=>refresh().catch(()=>{}),5000); return()=>clearInterval(timer)},[]);
  async function submit(e:FormEvent){e.preventDefault(); if(!url.trim()) return; setLoading(true);setError(""); try{const r=await fetch(`${API}/api/v1/jobs`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({source_url:url.trim(),target_language:"vi",auto_publish:false})}); if(!r.ok) throw new Error(await r.text()); setUrl(""); await refresh()}catch(e){setError(e instanceof Error?e.message:"Request failed")}finally{setLoading(false)}}
  const statuses=["DOWNLOADING","TRANSCRIBING","TRANSLATING","SYNTHESIZING","RENDERING","COMPLETED","FAILED"];
  return <main><h1>ScanVideo</h1><p className="muted">Local-first AI video automation</p>{error&&<div className="card">{error}</div>}<form className="form" onSubmit={submit}><input value={url} onChange={e=>setUrl(e.target.value)} placeholder="https://source-video-url"/><button className="button" disabled={loading}>{loading?"Queueing…":"Create job"}</button></form><section className="grid"><div className="card"><div className="muted">Total jobs</div><h2>{summary.total_jobs}</h2></div>{statuses.slice(0,3).map(s=><div className="card" key={s}><div className="muted">{s}</div><h2>{summary.by_status[s]??0}</h2></div>)}</section><table className="table"><thead><tr><th>Job</th><th>Status</th><th>Progress</th><th>Message</th></tr></thead><tbody>{jobs.map(j=><tr key={j.job_id}><td>{j.job_id.slice(0,12)}</td><td><span className="badge">{j.status}</span></td><td>{j.progress}%</td><td>{j.message}</td></tr>)}</tbody></table></main>;
}
