import os
import textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    concatenate_videoclips,
)
from config import CLIP_DURATION_SEC, OUTPUT_FILE, DOWNLOADS_DIR, WATERMARK_FILE
import music_generator

_WATERMARK_CLIP: ImageClip | None = None


def _get_watermark(video_w: int, duration: float) -> ImageClip | None:
    global _WATERMARK_CLIP
    if not os.path.exists(WATERMARK_FILE):
        return None
    try:
        img = Image.open(WATERMARK_FILE).convert("RGBA")
        wm_w = max(80, video_w // 6)
        ratio = wm_w / img.width
        wm_h = int(img.height * ratio)
        img = img.resize((wm_w, wm_h), Image.LANCZOS)
        # Apply 80% opacity
        r, g, b, a = img.split()
        a = a.point(lambda v: int(v * 0.80))
        img.putalpha(a)
        arr = np.array(img)
        pad = 18
        return (
            ImageClip(arr)
            .with_duration(duration)
            .with_position((video_w - wm_w - pad, pad))
        )
    except Exception as e:
        print(f"[processor] Watermark error: {e}")
        return None

MUSIC_PATH = str(DOWNLOADS_DIR / "comedy_music.wav")


def assemble(videos: list[dict]) -> None:
    clips = []
    for v in sorted(videos, key=lambda x: x["rank"], reverse=True):
        clip = _process_clip(v)
        if clip:
            clips.append(clip)

    if not clips:
        print("[processor] No clips to assemble.")
        return

    final = concatenate_videoclips(clips, method="compose")

    # Ensure downloads dir exists before writing music file into it
    DOWNLOADS_DIR.mkdir(exist_ok=True)

    # Generate original comedy music matching the exact video duration
    music_generator.generate(final.duration, MUSIC_PATH)
    audio = AudioFileClip(MUSIC_PATH).with_duration(final.duration)
    final = final.with_audio(audio)

    final.write_videofile(OUTPUT_FILE, fps=30, codec="libx264", audio_codec="aac")
    print(f"[processor] Done → {OUTPUT_FILE}")


def _process_clip(video: dict) -> CompositeVideoClip | None:
    path = video.get("local_path")
    if not path or not os.path.exists(path):
        print(f"[processor] Skipping #{video['rank']} — missing: {path}")
        return None

    try:
        raw = VideoFileClip(path)
        trimmed = raw.subclipped(0, min(CLIP_DURATION_SEC, raw.duration)).without_audio()
        overlay = _make_overlay(video, trimmed.w, trimmed.h, trimmed.duration)
        layers = [trimmed, overlay]
        wm = _get_watermark(trimmed.w, trimmed.duration)
        if wm:
            layers.append(wm)
        return CompositeVideoClip(layers)
    except Exception as e:
        print(f"[processor] Error #{video['rank']}: {e}")
        return None


def _make_overlay(video: dict, w: int, h: int, duration: float) -> ImageClip:
    label = (
        f"#{video['rank']}  |  {video['platform'].upper()}"
        f"  |  Credit: @{video['creator']}"
    )
    label = textwrap.shorten(label, width=72, placeholder="…")

    bar_h = 50
    img = Image.new("RGBA", (w, bar_h), (0, 0, 0, 180))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()

    draw.text((12, 12), label, font=font, fill=(255, 255, 255, 255))

    return (
        ImageClip(np.array(img))
        .with_duration(duration)
        .with_position(("left", h - bar_h))
    )
