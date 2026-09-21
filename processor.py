import os
import textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    CompositeAudioClip,
    ImageClip,
    ColorClip,
    CompositeVideoClip,
    concatenate_videoclips,
    afx,
)
from config import CLIP_DURATION_SEC, OUTPUT_FILE, DOWNLOADS_DIR, WATERMARK_FILE
import audio_separator
import music_generator

# 9:16 portrait — required by YouTube Shorts and TikTok. Facebook Reels
# additionally rejects any video under 960px tall.
FRAME_W, FRAME_H = 1080, 1920

MUSIC_PATH = str(DOWNLOADS_DIR / "comedy_music.wav")
LAUGH_PATH = str(DOWNLOADS_DIR / "laugh_sfx.wav")
MUSIC_VOLUME = 0.15  # low bed under clip audio, not the main track

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

def assemble(videos: list[dict]) -> None:
    music_generator.generate_laugh(LAUGH_PATH)

    clips = []
    for v in sorted(videos, key=lambda x: x["rank"], reverse=True):
        clip = _process_clip(v)
        if clip:
            clips.append(clip)

    if not clips:
        print("[processor] No clips to assemble.")
        return

    final = concatenate_videoclips(clips, method="compose")

    # Low-volume music bed under the real clip audio (voices/reactions/SFX).
    music_generator.generate(final.duration, MUSIC_PATH)
    music = (
        AudioFileClip(MUSIC_PATH)
        .with_duration(final.duration)
        .with_effects([afx.MultiplyVolume(MUSIC_VOLUME)])
    )
    final_audio = CompositeAudioClip([final.audio, music]) if final.audio else music
    final = final.with_audio(final_audio)

    final.write_videofile(OUTPUT_FILE, fps=30, codec="libx264", audio_codec="aac")
    print(f"[processor] Done → {OUTPUT_FILE}")


def _process_clip(video: dict) -> CompositeVideoClip | None:
    path = video.get("local_path")
    if not path or not os.path.exists(path):
        print(f"[processor] Skipping #{video['rank']} — missing: {path}")
        return None

    try:
        raw = VideoFileClip(path)
        trimmed = raw.subclipped(0, min(CLIP_DURATION_SEC, raw.duration))
        duration = trimmed.duration

        clip_id = f"{video['platform']}_{video['id']}"
        vocals_path = audio_separator.extract_non_music_audio(path, clip_id, duration)

        audio_layers = []
        if vocals_path:
            audio_layers.append(AudioFileClip(vocals_path).with_duration(duration))

        laugh = AudioFileClip(LAUGH_PATH)
        laugh_dur = min(laugh.duration, duration)
        laugh = laugh.subclipped(0, laugh_dur).with_start(duration - laugh_dur)
        audio_layers.append(laugh)

        trimmed = trimmed.with_audio(CompositeAudioClip(audio_layers).with_duration(duration))

        # Letterbox into the 9:16 frame without cropping or distorting.
        scaled = trimmed.resized(width=FRAME_W)
        if scaled.h > FRAME_H:
            scaled = trimmed.resized(height=FRAME_H)

        layers = [
            ColorClip((FRAME_W, FRAME_H), color=(0, 0, 0)).with_duration(duration),
            scaled.with_position("center"),
            _make_overlay(video, duration),
        ]
        wm = _get_watermark(FRAME_W, duration)
        if wm:
            layers.append(wm)
        return CompositeVideoClip(layers, size=(FRAME_W, FRAME_H))
    except Exception as e:
        print(f"[processor] Error #{video['rank']}: {e}")
        return None


def _make_overlay(video: dict, duration: float) -> ImageClip:
    rank = f"#{video['rank']}"
    credit = textwrap.shorten(
        f"{video['platform'].upper()}  |  Credit: @{video['creator']}",
        width=54,
        placeholder="…",
    )

    bar_h = 150
    img = Image.new("RGBA", (FRAME_W, bar_h), (0, 0, 0, 190))
    draw = ImageDraw.Draw(img)

    try:
        rank_font = ImageFont.truetype("arialbd.ttf", 84)
        credit_font = ImageFont.truetype("arial.ttf", 34)
    except OSError:
        rank_font = ImageFont.load_default()
        credit_font = ImageFont.load_default()

    draw.text((40, 24), rank, font=rank_font, fill=(255, 214, 0, 255))
    draw.text((200, 56), credit, font=credit_font, fill=(255, 255, 255, 255))

    # Sit above the bottom edge so platform UI chrome does not cover it.
    return (
        ImageClip(np.array(img))
        .with_duration(duration)
        .with_position((0, FRAME_H - bar_h - 220))
    )
