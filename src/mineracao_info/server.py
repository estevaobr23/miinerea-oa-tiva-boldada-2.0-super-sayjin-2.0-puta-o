from __future__ import annotations

import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

from .config import get_settings
from .models import JobSpec
from .pipeline import prepare_job, run_job
from .skill import load_skill
from .storage import Storage

app = FastAPI(title="MINERACAO INFO ENGINE", version="1.0.0")


def _storage() -> Storage:
    return Storage(get_settings(require_token=False).db_path)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/skill/status")
def skill_status() -> dict[str, str]:
    settings = get_settings(require_token=False)
    skill = load_skill(settings.skill_path, settings.runtime_path)
    return {"version": skill.version, "sha256": skill.sha256, "path": str(settings.skill_path)}


@app.post("/mine", status_code=202)
def start_mine(request: JobSpec) -> dict[str, str]:
    job_id = prepare_job(request)

    def worker() -> None:
        try:
            run_job(request, job_id=job_id, precreated=True)
        except Exception as exc:
            _storage().update_job_status(job_id, "failed", error=str(exc))

    threading.Thread(target=worker, daemon=True, name=f"mineracao-{job_id}").start()
    return {"job_id": job_id, "status": "queued"}


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = _storage().get_job(job_id)
    if not job:
        raise HTTPException(404, "job nao encontrado")
    return job


@app.get("/jobs/{job_id}/report", response_class=PlainTextResponse)
def get_job_report(job_id: str) -> str:
    report_path = _storage().get_report_path(job_id)
    if not report_path:
        if not _storage().get_job(job_id):
            raise HTTPException(404, "job nao encontrado")
        raise HTTPException(409, "report ainda nao disponivel")
    path = Path(report_path)
    if not path.is_file():
        raise HTTPException(404, "arquivo de report nao encontrado")
    return path.read_text(encoding="utf-8")
