import shutil
import uuid
import json
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import JOBS_DIR, TEMPLATES_DIR, STATIC_DIR, settings
from .db import Base, SessionLocal, engine, get_db
from .models import Job
from .queue import enqueue_video_job
from .schemas import JobCreateResponse, JobDetailResponse, JobListResponse

app = FastAPI(title=settings.app_name, default_response_class=ORJSONResponse)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": settings.app_name})


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "title": settings.app_name})


@app.get("/result/{job_id}", response_class=HTMLResponse)
def result_page(job_id: str, request: Request):
    return templates.TemplateResponse("result.html", {"request": request, "title": settings.app_name, "job_id": job_id})


@app.post("/api/jobs/upload", response_model=JobCreateResponse)
def upload_job(
    file: UploadFile = File(...),
    asr_model: str = Form(default_factory=lambda: settings.default_asr_model),
    transcription_mode: str = Form(default_factory=lambda: settings.default_transcription_mode),
    language: str = Form(default_factory=lambda: settings.default_language),
    summary_mode: str = Form(default_factory=lambda: settings.default_summary_mode),
    vocabulary_hint: str = Form(default=""),
    db: Session = Depends(get_db),
):
    suffix = Path(file.filename or "video.mp4").suffix or ".mp4"
    job_id = str(uuid.uuid4())
    stored_filename = f"{job_id}{suffix}"
    job_dir = JOBS_DIR / job_id
    input_dir = job_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    target_path = input_dir / stored_filename
    request_path = job_dir / "request.json"

    with target_path.open("wb") as out_file:
        shutil.copyfileobj(file.file, out_file)

    request_path.write_text(
        json.dumps(
            {
                "transcription_mode": transcription_mode,
                "vocabulary_hint": vocabulary_hint.strip(),
                "highlight_min_duration_sec": settings.highlight_min_duration_sec,
                "highlight_target_duration_sec": settings.highlight_target_duration_sec,
                "highlight_max_duration_sec": settings.highlight_max_duration_sec,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    job = Job(
        id=job_id,
        original_filename=file.filename or stored_filename,
        stored_filename=stored_filename,
        source_path=str(target_path),
        status="uploaded",
        progress=5,
        asr_model=asr_model,
        language=language,
        summary_mode=summary_mode,
        result_payload=None,
    )
    db.add(job)
    db.commit()

    try:
        enqueue_video_job(job_id)
        job.status = "queued"
        job.progress = 10
        db.commit()
    except Exception as exc:
        job.status = "failed"
        job.error_message = f"Не удалось поставить задачу в очередь: {exc}"
        db.commit()
        raise HTTPException(status_code=503, detail="Не удалось поставить задачу в очередь") from exc

    return JobCreateResponse(id=job_id, status=job.status, progress=job.progress)


@app.get("/api/jobs", response_model=JobListResponse)
def list_jobs(db: Session = Depends(get_db)):
    items = db.execute(select(Job).order_by(Job.created_at.desc())).scalars().all()
    return JobListResponse(items=items)


@app.get("/api/jobs/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/files/{job_id}/{file_path:path}")
def get_result_file(job_id: str, file_path: str):
    base_dir = (JOBS_DIR / job_id).resolve()
    candidate = (base_dir / file_path).resolve()
    if base_dir not in candidate.parents and candidate != base_dir:
        raise HTTPException(status_code=400, detail="Invalid path")
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(candidate)
