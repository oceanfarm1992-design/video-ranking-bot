"""
Generates original comedy background music using pure Python waveform synthesis.
No samples, no copyrighted material — 100% synthesized.

Style: circus/vaudeville, C major, 128 BPM, bouncy and staccato.
"""

import numpy as np
from scipy.io import wavfile

SAMPLE_RATE = 44100
BPM = 128
BEAT = 60.0 / BPM  # seconds per quarter note

# ── Frequencies ──────────────────────────────────────────────────────────────

FREQ: dict[str, float] = {
    "R":  0.0,
    "F2": 87.31,  "G2": 98.00,  "A2": 110.00,
    "C3": 130.81, "D3": 146.83, "E3": 164.81, "F3": 174.61,
    "G3": 196.00, "A3": 220.00, "B3": 246.94,
    "C4": 261.63, "D4": 293.66, "E4": 329.63, "F4": 349.23,
    "G4": 392.00, "A4": 440.00, "B4": 493.88,
    "C5": 523.25, "D5": 587.33, "E5": 659.26, "F5": 698.46,
    "G5": 783.99, "A5": 880.00, "B5": 987.77, "C6": 1046.50,
}

# ── Original comedy melody (one full phrase loop) ─────────────────────────────
# Format: (note, quarter-note beats)

MELODY_LOOP: list[tuple[str, float]] = [
    # Phrase 1 — ascending fanfare
    ("C5", 0.5), ("E5", 0.5), ("G5", 0.5), ("C6", 0.5),
    ("B5", 0.25), ("A5", 0.25), ("G5", 0.5), ("R", 0.5),
    # Phrase 2 — playful descending run
    ("E5", 0.25), ("D5", 0.25), ("C5", 0.25), ("B4", 0.25),
    ("C5", 0.5), ("E5", 0.5), ("G5", 1.0),
    # Phrase 3 — quick staccato bounce
    ("G4", 0.25), ("R", 0.25), ("G4", 0.25), ("R", 0.25),
    ("A4", 0.25), ("R", 0.25), ("A4", 0.25), ("R", 0.25),
    ("B4", 0.5), ("C5", 0.5), ("D5", 1.0),
    # Phrase 4 — ascending scale run (comedy zoom-up)
    ("C4", 0.125), ("D4", 0.125), ("E4", 0.125), ("F4", 0.125),
    ("G4", 0.125), ("A4", 0.125), ("B4", 0.125), ("C5", 0.125),
    ("D5", 0.125), ("E5", 0.125), ("F5", 0.125), ("G5", 0.125),
    ("A5", 0.125), ("B5", 0.125), ("C6", 0.25),
    # Phrase 5 — comic landing and resolve
    ("G5", 0.5), ("E5", 0.5), ("C5", 0.5), ("R", 0.5),
    ("E5", 0.25), ("G5", 0.25), ("E5", 0.25), ("C5", 0.25),
    ("G4", 0.5), ("C5", 1.5),
]

# ── Oompah bass (loops every 4 bars) ─────────────────────────────────────────

BASS_LOOP: list[tuple[str, float]] = [
    ("C3", 0.5), ("G3", 0.5), ("C3", 0.5), ("G3", 0.5),
    ("G2", 0.5), ("D3", 0.5), ("G2", 0.5), ("D3", 0.5),
    ("A2", 0.5), ("E3", 0.5), ("A2", 0.5), ("E3", 0.5),
    ("F2", 0.5), ("C3", 0.5), ("G2", 0.5), ("D3", 0.5),
]

# ── Waveform synthesis ────────────────────────────────────────────────────────

def _adsr(n: int, a: float = 0.006, d: float = 0.04,
          sustain: float = 0.65, r: float = 0.08) -> np.ndarray:
    sr = SAMPLE_RATE
    na = min(int(a * sr), n)
    nd = min(int(d * sr), n - na)
    nr = min(int(r * sr), n - na - nd)
    ns = max(0, n - na - nd - nr)
    return np.concatenate([
        np.linspace(0.0, 1.0, na),
        np.linspace(1.0, sustain, nd),
        np.full(ns, sustain),
        np.linspace(sustain, 0.0, nr),
    ])


def _vibrato_saw(freq: float, n: int, rate: float = 5.5,
                 depth: float = 0.003) -> np.ndarray:
    """Sawtooth with gentle pitch wobble — bright comedy lead sound."""
    t = np.arange(n) / SAMPLE_RATE
    freq_mod = freq * (1.0 + depth * np.sin(2 * np.pi * rate * t))
    phase = np.cumsum(freq_mod) / SAMPLE_RATE
    return 2.0 * (phase % 1.0) - 1.0


def _square(freq: float, n: int) -> np.ndarray:
    t = np.arange(n) / SAMPLE_RATE
    return np.sign(np.sin(2 * np.pi * freq * t)).astype(float)

# ── Track sequencers ─────────────────────────────────────────────────────────

def _sequence_melody(pattern: list[tuple[str, float]], total_n: int) -> np.ndarray:
    track = np.zeros(total_n)
    cursor = 0
    for note, beats in pattern:
        n = min(int(beats * BEAT * SAMPLE_RATE), total_n - cursor)
        if n <= 0:
            break
        freq = FREQ.get(note, 0.0)
        if freq > 0:
            gate = max(1, int(n * 0.82))  # staccato gap
            wave = _vibrato_saw(freq, gate)
            track[cursor:cursor + gate] += wave * _adsr(gate, sustain=0.6)
        cursor += n
    return track


def _sequence_bass(pattern: list[tuple[str, float]], total_n: int) -> np.ndarray:
    track = np.zeros(total_n)
    cursor = 0
    for note, beats in pattern:
        n = min(int(beats * BEAT * SAMPLE_RATE), total_n - cursor)
        if n <= 0:
            break
        freq = FREQ.get(note, 0.0)
        if freq > 0:
            gate = max(1, int(n * 0.78))
            wave = _square(freq, gate)
            track[cursor:cursor + gate] += wave * _adsr(
                gate, a=0.003, d=0.06, sustain=0.5, r=0.05
            )
        cursor += n
    return track


def _generate_drums(total_n: int) -> np.ndarray:
    rng = np.random.default_rng(42)
    track = np.zeros(total_n)
    beat_n = int(BEAT * SAMPLE_RATE)

    for b in range(total_n // beat_n):
        pos = b * beat_n
        if b % 4 in (0, 2):
            _kick(track, pos, total_n)
        if b % 4 in (1, 3):
            _snare(track, pos, total_n, rng)
        _hihat(track, pos, total_n, rng)
        half = pos + beat_n // 2
        if half < total_n:
            _hihat(track, half, total_n, rng)

    return track


def _kick(buf: np.ndarray, pos: int, total_n: int) -> None:
    n = min(int(0.12 * SAMPLE_RATE), total_n - pos)
    t = np.arange(n) / SAMPLE_RATE
    freq_sweep = np.linspace(140, 40, n)
    phase = 2 * np.pi * np.cumsum(freq_sweep) / SAMPLE_RATE
    buf[pos:pos + n] += np.sin(phase) * np.exp(-t * 30) * 0.9


def _snare(buf: np.ndarray, pos: int, total_n: int,
           rng: np.random.Generator) -> None:
    n = min(int(0.08 * SAMPLE_RATE), total_n - pos)
    t = np.arange(n) / SAMPLE_RATE
    noise = rng.uniform(-1, 1, n)
    tone = np.sin(2 * np.pi * 200 * t)
    env = np.exp(-t * 40)
    buf[pos:pos + n] += (noise * 0.6 + tone * 0.4) * env * 0.7


def _hihat(buf: np.ndarray, pos: int, total_n: int,
           rng: np.random.Generator) -> None:
    n = min(int(0.025 * SAMPLE_RATE), total_n - pos)
    t = np.arange(n) / SAMPLE_RATE
    buf[pos:pos + n] += rng.uniform(-1, 1, n) * np.exp(-t * 120) * 0.25

# ── Public API ────────────────────────────────────────────────────────────────

def generate(duration_sec: float, output_path: str) -> None:
    """Generate comedy background music and save as 16-bit PCM WAV."""
    from pathlib import Path
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    total_n = int(duration_sec * SAMPLE_RATE)

    mel_loop_n = sum(int(b * BEAT * SAMPLE_RATE) for _, b in MELODY_LOOP)
    bas_loop_n = sum(int(b * BEAT * SAMPLE_RATE) for _, b in BASS_LOOP)

    mel_reps = int(np.ceil(total_n / mel_loop_n))
    bas_reps = int(np.ceil(total_n / bas_loop_n))

    melody = np.tile(_sequence_melody(MELODY_LOOP, mel_loop_n), mel_reps)[:total_n]
    bass   = np.tile(_sequence_bass(BASS_LOOP, bas_loop_n), bas_reps)[:total_n]
    drums  = _generate_drums(total_n)

    # Fade in / out  (0.5 s)
    fade_n = min(int(0.5 * SAMPLE_RATE), total_n // 4)
    fade_in  = np.linspace(0.0, 1.0, fade_n)
    fade_out = np.linspace(1.0, 0.0, fade_n)
    for track in (melody, bass, drums):
        track[:fade_n]  *= fade_in
        track[-fade_n:] *= fade_out

    mixed = melody * 0.45 + bass * 0.35 + drums * 0.20

    peak = np.max(np.abs(mixed))
    if peak > 0:
        mixed = mixed / peak * 0.85

    wavfile.write(output_path, SAMPLE_RATE, (mixed * 32767).astype(np.int16))
    print(f"[music] Generated {duration_sec:.1f}s comedy music → {output_path}")


if __name__ == "__main__":
    generate(30.0, "preview_music.wav")
    print("Preview saved: preview_music.wav")
