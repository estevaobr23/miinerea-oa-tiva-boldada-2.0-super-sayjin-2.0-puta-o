from __future__ import annotations

import threading
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .pipeline import mine
from .config import get_settings
from .skill import load_skill
from .storage import Storage

app=FastAPI(title="MINERACAO INFO ENGINE", version="0.1.0")

class MineRequest(BaseModel):
    seed: str = Field(min_length=2)
    depth: str = "quick"
    sources: list[str] = ["meta","tiktok","google"]
    country: str = "BR"

JOBS: dict[str, dict] = {}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/skill/status")
def skill_status():
    s=get_settings(require_token=False)
    skill=load_skill(s.skill_path, s.runtime_path)
    return {"version":skill.version, "sha256":skill.sha256, "path":str(s.skill_path)}

@app.post("/mine")
def start_mine(req: MineRequest):
    # O pipeline gera o run_id internamente. Job local apenas acompanha a thread.
    import uuid
    job_id=uuid.uuid4().hex[:10]
    JOBS[job_id]={"status":"running"}
    def worker():
        try:
            JOBS[job_id]={"status":"done", "result":mine(req.seed, req.depth, req.sources, req.country)}
        except Exception as exc:
            JOBS[job_id]={"status":"failed", "error":str(exc)}
    threading.Thread(target=worker, daemon=True).start()
    return {"job_id":job_id, "status":"running"}

@app.get("/jobs/{job_id}")
def job(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(404, "job nao encontrado")
    return JOBS[job_id]
