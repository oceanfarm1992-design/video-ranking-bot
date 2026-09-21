import subprocess
from pathlib import Path

from moviepy import VideoFileClip

from config import DOWNLOADS_DIR

_MODEL = "htdemucs"
_SEP_DIR = DOWNLOADS_DIR / "audio_sep"


def extract_non_music_audio(video_path: str, clip_id: str, duration: float) -> str | None:
    """Isolate voice/reaction/sound-effect audio from a clip's opening
    `duration` seconds via Demucs vocal separation, discarding the music
    stem. Returns a path to the resulting WAV, or None if separation
    was not possible (no audio track, or Demucs failed).
    """
    workdir = _SEP_DIR / clip_id
    workdir.mkdir(parents=True, exist_ok=True)
    raw_wav = workdir / "input.wav"

    try:
        clip = VideoFileClip(video_path).subclipped(0, duration)
        if clip.audio is None:
            return None
        clip.audio.write_audiofile(str(raw_wav), logger=None)
    except Exception as e:
        print(f"[audio] {clip_id}: could not extract source audio: {e}")
        return None

    try:
        subprocess.run(
            [
                "python", "-m", "demucs",
                "-n", _MODEL,
                "--two-stems", "vocals",
                "-o", str(workdir),
                str(raw_wav),
            ],
            check=True,
            capture_output=True,
            timeout=180,
        )
    except Exception as e:
        detail = getattr(e, "stderr", b"")
        detail = detail.decode(errors="ignore")[-300:] if isinstance(detail, bytes) else str(e)
        print(f"[audio] {clip_id}: Demucs separation failed: {detail}")
        return None

    vocals_path = workdir / _MODEL / "input" / "vocals.wav"
    if not vocals_path.exists():
        print(f"[audio] {clip_id}: Demucs did not produce a vocals stem")
        return None

    return str(vocals_path)
