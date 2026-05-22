import json

import pytest

import app.tasks as video_tasks
from app.config import JOBS_DIR
from app.db import SessionLocal
from app.models import Job


def make_segments():
    segments = []

    for i in range(8):
        text = (
            "видео анализ алгоритм транскрипция summary интерфейс "
            "пользователь задача обработка результат "
        ) * 4

        segments.append(
            {
                "start": i * 10,
                "end": i * 10 + 10,
                "text": f"{text} номер {i}",
            }
        )

    return segments


def create_test_job(job_id="pipeline-job"):
    job_dir = JOBS_DIR / job_id
    input_dir = job_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    source_path = input_dir / "input.mp4"
    source_path.write_bytes(b"fake video")

    request_path = job_dir / "request.json"
    request_path.write_text(
        json.dumps(
            {
                "transcription_mode": "accurate",
                "vocabulary_hint": "VideoDigest",
                "highlight_min_duration_sec": 20,
                "highlight_target_duration_sec": 30,
                "highlight_max_duration_sec": 40,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    db = SessionLocal()
    job = Job(
        id=job_id,
        original_filename="input.mp4",
        stored_filename="input.mp4",
        source_path=str(source_path),
        status="queued",
        progress=10,
        asr_model="tiny",
        language="ru",
        summary_mode="extractive",
        result_payload=None,
    )
    db.add(job)
    db.commit()
    db.close()

    return job_id


def test_build_initial_prompt_ru_with_hint():
    prompt = video_tasks.build_initial_prompt("ru", "VideoDigest, ВШЭ")

    assert prompt is not None
    assert "русская расшифровка" in prompt
    assert "VideoDigest" in prompt


def test_build_initial_prompt_auto_without_hint():
    prompt = video_tasks.build_initial_prompt("auto", "")

    assert prompt is None


def test_update_job_changes_fields():
    job = Job(
        id="update-test",
        original_filename="video.mp4",
        stored_filename="video.mp4",
        source_path="/tmp/video.mp4",
        status="queued",
        progress=10,
        asr_model="tiny",
        language="ru",
        summary_mode="extractive",
    )

    video_tasks.update_job(job, status="done", progress=100, result_payload={"ok": True})

    assert job.status == "done"
    assert job.progress == 100
    assert job.result_payload == {"ok": True}


def test_process_video_job_success_without_real_whisper_and_ffmpeg(monkeypatch):
    job_id = create_test_job()

    def fake_extract_audio(video_path, audio_path):
        audio_path.write_bytes(b"audio")

    def fake_transcribe(audio_path, model_name, language, *, transcription_mode, vocabulary_hint):
        return make_segments()

    def fake_cut_clip(video_path, start, end, output_path):
        output_path.write_bytes(b"clip")

    def fake_concat_clips(clips, output_path):
        output_path.write_bytes(b"final video")

    monkeypatch.setattr(video_tasks, "extract_audio", fake_extract_audio)
    monkeypatch.setattr(video_tasks, "transcribe", fake_transcribe)
    monkeypatch.setattr(video_tasks, "cut_clip", fake_cut_clip)
    monkeypatch.setattr(video_tasks, "concat_clips", fake_concat_clips)

    video_tasks.process_video_job(job_id)

    db = SessionLocal()
    job = db.get(Job, job_id)
    db.close()

    assert job is not None
    assert job.status == "done"
    assert job.progress == 100
    assert job.result_payload is not None
    assert job.result_payload["summary_text"]
    assert job.result_payload["metadata"]["segments_count"] == 8
    assert "transcript" in job.result_payload["files"]
    assert "summary" in job.result_payload["files"]


def test_process_video_job_failure_sets_failed_status(monkeypatch):
    job_id = create_test_job("failed-pipeline-job")

    def fake_extract_audio(video_path, audio_path):
        raise video_tasks.FFmpegError("Error opening input file: missing")

    monkeypatch.setattr(video_tasks, "extract_audio", fake_extract_audio)

    with pytest.raises(video_tasks.FFmpegError):
        video_tasks.process_video_job(job_id)

    db = SessionLocal()
    job = db.get(Job, job_id)
    db.close()

    assert job is not None
    assert job.status == "failed"
    assert job.error_message is not None
