from fastapi.testclient import TestClient

from app.config import JOBS_DIR
from app.main import app


def test_health_endpoint():
    with TestClient(app) as cli:
        res = cli.get("/api/health")

    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_index_page_opens():
    with TestClient(app) as cli:
        res = cli.get("/")

    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


def test_dashboard_page_opens():
    with TestClient(app) as cli:
        res = cli.get("/dashboard")

    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


def test_result_page_opens():
    with TestClient(app) as cli:
        res = cli.get("/result/test-job-id")

    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


def test_jobs_list_empty():
    with TestClient(app) as cli:
        res = cli.get("/api/jobs")

    assert res.status_code == 200
    assert res.json() == {"items": []}


def test_upload_job_without_real_worker(monkeypatch):
    monkeypatch.setattr("app.main.enqueue_video_job", lambda job_id: None)

    data = {
        "asr_model": "base",
        "transcription_mode": "accurate",
        "language": "ru",
        "summary_mode": "extractive",
        "vocabulary_hint": "VideoDigest, ВШЭ",
    }

    files = {
        "file": ("sample.mp4", b"fake video content", "video/mp4"),
    }

    with TestClient(app) as cli:
        upload_res = cli.post("/api/jobs/upload", data=data, files=files)

    assert upload_res.status_code == 200

    body = upload_res.json()
    assert "id" in body
    assert body["status"] == "queued"
    assert body["progress"] == 10

    job_id = body["id"]

    with TestClient(app) as cli:
        detail_res = cli.get(f"/api/jobs/{job_id}")
        list_res = cli.get("/api/jobs")

    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == job_id

    assert list_res.status_code == 200
    assert len(list_res.json()["items"]) == 1


def test_get_missing_job_returns_404():
    with TestClient(app) as cli:
        res = cli.get("/api/jobs/not-existing-job")

    assert res.status_code == 404


def test_result_file_endpoint_returns_existing_file():
    job_id = "file-test-job"
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    result_file = job_dir / "summary.txt"
    result_file.write_text("summary text", encoding="utf-8")

    with TestClient(app) as cli:
        res = cli.get(f"/files/{job_id}/summary.txt")

    assert res.status_code == 200
    assert res.text == "summary text"


def test_result_file_endpoint_blocks_path_traversal():
    job_id = "safe-job"
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    with TestClient(app) as cli:
        res = cli.get(f"/files/{job_id}/../secret.txt")

    assert res.status_code in {400, 404}
