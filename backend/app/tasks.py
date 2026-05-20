import json
from functools import lru_cache
from pathlib import Path

from faster_whisper import WhisperModel

from .config import JOBS_DIR, settings
from .db import SessionLocal
from .models import Job
from .utils.ffmpeg import FFmpegError, compact_ffmpeg_error, concat_clips, cut_clip, extract_audio
from .utils.text import choose_highlights, extract_topic_keywords, sanitize_segments, summarize_text

_UNSET = object()


@lru_cache(maxsize=2)
def get_whisper_model(model_name: str) -> WhisperModel:
    return WhisperModel(model_name, device="cpu", compute_type="int8")


def update_job(
    job: Job,
    *,
    status: str | None = None,
    progress: int | None = None,
    error_message: str | None | object = _UNSET,
    result_payload: dict | None | object = _UNSET,
) -> None:
    if status is not None:
        job.status = status
    if progress is not None:
        job.progress = progress
    if error_message is not _UNSET:
        job.error_message = error_message
    if result_payload is not _UNSET:
        job.result_payload = result_payload


def build_initial_prompt(language: str, vocabulary_hint: str) -> str | None:
    hints = vocabulary_hint.strip()
    if language == "ru":
        base = "Точная русская расшифровка речи с пунктуацией. Сохраняй названия брендов, моделей, имен и технических терминов."
    elif language == "en":
        base = "Accurate English speech transcription with punctuation. Preserve brand names, model names and technical terms."
    else:
        base = ""

    if hints:
        hint_prefix = " Важные термины: " if language == "ru" else " Important terms: "
        return f"{base}{hint_prefix}{hints}"
    return base or None


def transcribe(
    audio_path: Path,
    model_name: str,
    language: str,
    *,
    transcription_mode: str,
    vocabulary_hint: str,
) -> list[dict]:
    model = get_whisper_model(model_name)

    mode = transcription_mode if transcription_mode in {"fast", "accurate"} else settings.default_transcription_mode

    beam_size = 1 if mode == "fast" else 5
    best_of = 1 if mode == "fast" else 5

    vad_parameters = {
        "min_silence_duration_ms": 500,
        "speech_pad_ms": 250,
    }

    try:
        segments, _ = model.transcribe(
            str(audio_path),
            language=None if language == "auto" else language,
            vad_filter=True,
            vad_parameters=vad_parameters,
            beam_size=beam_size,
            best_of=best_of,
            patience=1.2 if mode == "accurate" else 1.0,
            repetition_penalty=1.05 if mode == "accurate" else 1.0,
            no_speech_threshold=0.45 if mode == "accurate" else 0.6,
            compression_ratio_threshold=2.2 if mode == "accurate" else 2.4,
            condition_on_previous_text=True,
            temperature=0.0,
            hallucination_silence_threshold=1.8 if mode == "accurate" else None,
            initial_prompt=build_initial_prompt(language, vocabulary_hint),
            hotwords=vocabulary_hint.strip() or None,
        )

        segments = list(segments)

    except Exception as e:
        raise Exception("В видео нет звука или Whisper не смог распознать речь") from e

    prepared = []

    for seg in segments:
        text = seg.text.strip()

        if not text:
            continue

        prepared.append(
            {
                "start": round(float(seg.start), 2),
                "end": round(float(seg.end), 2),
                "text": text,
            }
        )

    if not prepared:
        raise Exception("В видео нет распознаваемой речи")

    return prepared


def process_video_job(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            raise RuntimeError(f"Job {job_id} not found")

        job_dir = JOBS_DIR / job_id
        clips_dir = job_dir / "clips"
        job_dir.mkdir(parents=True, exist_ok=True)
        clips_dir.mkdir(parents=True, exist_ok=True)

        source_path = Path(job.source_path)
        audio_path = job_dir / "audio.wav"
        transcript_path = job_dir / "transcript.txt"
        segments_path = job_dir / "segments.json"
        summary_path = job_dir / "summary.txt"
        highlights_path = job_dir / "highlights.json"
        final_video_path = job_dir / "highlights.mp4"
        request_path = job_dir / "request.json"
        request_payload = {}
        if request_path.exists():
            request_payload = json.loads(request_path.read_text(encoding="utf-8"))

        transcription_mode = request_payload.get("transcription_mode", settings.default_transcription_mode)
        vocabulary_hint = request_payload.get("vocabulary_hint", "")
        highlight_min_duration_sec = int(request_payload.get("highlight_min_duration_sec", settings.highlight_min_duration_sec))
        highlight_target_duration_sec = int(request_payload.get("highlight_target_duration_sec", settings.highlight_target_duration_sec))
        highlight_max_duration_sec = int(request_payload.get("highlight_max_duration_sec", settings.highlight_max_duration_sec))

        update_job(job, status="transcribing", progress=25, error_message=None, result_payload=None)
        db.commit()

        extract_audio(source_path, audio_path)
        segments = transcribe(
            audio_path,
            job.asr_model,
            job.language,
            transcription_mode=transcription_mode,
            vocabulary_hint=vocabulary_hint,
        )
        segments = sanitize_segments(segments)
        transcript_text = "\n".join(item["text"] for item in segments)
        transcript_path.write_text(transcript_text, encoding="utf-8")
        segments_path.write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")

        update_job(job, status="summarizing", progress=60)
        db.commit()

        summary_text = summarize_text(transcript_text, max_sentences=5)
        summary_path.write_text(summary_text, encoding="utf-8")

        highlights = choose_highlights(
            segments,
            max_items=3,
            min_duration=highlight_min_duration_sec,
            target_duration=highlight_target_duration_sec,
            max_duration=highlight_max_duration_sec,
        )
        highlights_path.write_text(json.dumps(highlights, ensure_ascii=False, indent=2), encoding="utf-8")
        topic_keywords = extract_topic_keywords(transcript_text, max_items=8)

        update_job(job, status="rendering", progress=82)
        db.commit()

        clip_paths = []
        prepared_highlights = []
        render_warning = None
        try:
            for item in highlights:
                clip_path = clips_dir / f"clip_{item['rank']}.mp4"
                cut_clip(source_path, item["start"], item["end"], clip_path)
                clip_paths.append(clip_path)
                prepared_highlights.append(
                    {
                        **item,
                        "file": f"/files/{job_id}/clips/{clip_path.name}",
                    }
                )
        except FFmpegError as exc:
            render_warning = compact_ffmpeg_error(str(exc), fallback="Не удалось подготовить фрагменты видео.")
            clip_paths = []
            prepared_highlights = [{key: value for key, value in item.items() if key != "file"} for item in highlights]

        files = {
            "source_video": f"/files/{job_id}/input/{source_path.name}",
            "transcript": f"/files/{job_id}/transcript.txt",
            "segments": f"/files/{job_id}/segments.json",
            "summary": f"/files/{job_id}/summary.txt",
            "highlights_json": f"/files/{job_id}/highlights.json",
        }

        if clip_paths:
            try:
                concat_clips(clip_paths, final_video_path)
                files["highlights_video"] = f"/files/{job_id}/highlights.mp4"
            except FFmpegError as exc:
                render_warning = compact_ffmpeg_error(str(exc), fallback="Не удалось собрать итоговое видео.")

        payload = {
            "summary_text": summary_text,
            "transcript_preview": transcript_text[:3000],
            "highlights": prepared_highlights,
            "files": files,
            "metadata": {
                "segments_count": len(segments),
                "highlights_count": len(prepared_highlights),
                "render_warning": render_warning,
                "topic_keywords": topic_keywords,
                "transcription_mode": transcription_mode,
                "highlight_duration_range": [highlight_min_duration_sec, highlight_max_duration_sec],
            },
        }

        update_job(job, status="done", progress=100, result_payload=payload)
        db.commit()
    except Exception as exc:
        failing_job = db.get(Job, job_id)
        if failing_job is not None:
            message = str(exc)
            if isinstance(exc, FFmpegError):
                message = compact_ffmpeg_error(message)
            update_job(failing_job, status="failed", error_message=message)
            db.commit()
        raise
    finally:
        db.close()
