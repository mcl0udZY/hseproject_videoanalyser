import subprocess
from pathlib import Path


class FFmpegError(RuntimeError):
    pass


def compact_ffmpeg_error(message: str, fallback: str = "Ошибка ffmpeg") -> str:
    lines = [line.strip() for line in message.splitlines() if line.strip()]
    if not lines:
        return fallback

    priority_markers = (
        "Error opening input file",
        "Error opening input files",
        "Impossible to open",
        "No such file or directory",
        "Invalid data found",
    )
    selected = [line for line in lines if any(marker in line for marker in priority_markers)]
    if selected:
        return " ".join(selected[-2:])

    return lines[-1]


def run_ffmpeg(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise FFmpegError(result.stderr.strip() or "ffmpeg finished with an error")


def extract_audio(video_path: Path, audio_path: Path) -> None:
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg([
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-af", "highpass=f=80,lowpass=f=7600,loudnorm=I=-16:LRA=11:TP=-1.5",
        str(audio_path),
    ])


def cut_clip(video_path: Path, start: float, end: float, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0.1, end - start)
    run_ffmpeg([
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", str(video_path),
        "-t", str(duration),
        "-c:v", "libx264",
        "-c:a", "aac",
        str(output_path),
    ])


def concat_clips(clips: list[Path], output_path: Path) -> None:
    if not clips:
        raise FFmpegError("No clips to concatenate")
    if len(clips) == 1:
        output_path.write_bytes(clips[0].read_bytes())
        return

    file_list = clips[0].parent / "concat.txt"
    file_list.write_text("\n".join(f"file '{clip.name}'" for clip in clips), encoding="utf-8")
    run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(file_list),
        "-c", "copy",
        str(output_path),
    ])
