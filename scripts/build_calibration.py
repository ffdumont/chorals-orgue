"""Genere les assets de la page de calibration sync audio/partition.

Sortie :
  assets/midi/calibration_scale.mid   - 8 notes C4->C5 a 1s chacune
  assets/audio/calibration_scale.mp3  - meme gamme en sinusoides

La MIDI est ensuite convertie en MusicXML + timemap via build_scores.py :
    python scripts/build_scores.py calibration_scale

Piece de reference la plus simple possible pour diagnostiquer la sync :
  - tempo stable (60 BPM, 1 note = 1 seconde)
  - aucun rubato, aucun ornement, aucun accord
  - une seule voix, un seul staff
"""
from __future__ import annotations

import struct
import subprocess
import wave
from pathlib import Path

import mido
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MIDI_PATH = ROOT / "assets" / "midi" / "calibration_scale.mid"
WAV_PATH = ROOT / "assets" / "audio" / "calibration_scale.wav"
MP3_PATH = ROOT / "assets" / "audio" / "calibration_scale.mp3"
FFMPEG = Path(r"C:/Program Files/ffmpeg-7.0.2-essentials_build/bin/ffmpeg.exe")

# C major scale C4 -> C5
MIDI_NOTES = [60, 62, 64, 65, 67, 69, 71, 72]
BPM = 60
NOTE_SECONDS = 1.0
SR = 44100
AMPLITUDE = 0.25


def build_midi() -> None:
    MIDI_PATH.parent.mkdir(parents=True, exist_ok=True)
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    # 60 BPM -> 1 beat = 1 s = 1_000_000 us
    track.append(mido.MetaMessage("set_tempo", tempo=1_000_000, time=0))
    track.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    track.append(mido.Message("program_change", program=0, channel=1, time=0))
    for i, note in enumerate(MIDI_NOTES):
        track.append(mido.Message("note_on", note=note, velocity=80, channel=1, time=0))
        track.append(mido.Message("note_off", note=note, velocity=0, channel=1, time=480))
    track.append(mido.MetaMessage("end_of_track", time=0))
    mid.save(MIDI_PATH)
    print(f"Wrote {MIDI_PATH}")


def midi_to_freq(note: int) -> float:
    return 440.0 * 2 ** ((note - 69) / 12)


def build_audio() -> None:
    WAV_PATH.parent.mkdir(parents=True, exist_ok=True)
    samples = []
    for note in MIDI_NOTES:
        freq = midi_to_freq(note)
        t = np.linspace(0, NOTE_SECONDS, int(SR * NOTE_SECONDS), endpoint=False)
        # Attack+release ramp (20 ms) pour eviter les clics
        ramp = int(SR * 0.02)
        env = np.ones_like(t)
        env[:ramp] = np.linspace(0, 1, ramp)
        env[-ramp:] = np.linspace(1, 0, ramp)
        note_wave = AMPLITUDE * np.sin(2 * np.pi * freq * t) * env
        samples.append(note_wave)
    wave_data = np.concatenate(samples)
    pcm = (wave_data * 32767).astype(np.int16)

    with wave.open(str(WAV_PATH), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"Wrote {WAV_PATH}")

    subprocess.run(
        [str(FFMPEG), "-y", "-i", str(WAV_PATH), "-ab", "96k", str(MP3_PATH)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    WAV_PATH.unlink()
    print(f"Wrote {MP3_PATH}")


def main() -> int:
    build_midi()
    build_audio()
    print()
    print("Next: python scripts/build_scores.py calibration_scale")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
