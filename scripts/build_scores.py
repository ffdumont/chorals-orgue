"""Generate MusicXML + note-onset timemap for every piece that needs
score/video synchronization.

For each MIDI key listed in MIDI_KEYS:
  - runs MuseScore CLI to convert <key>.mid -> assets/scores/<key>.musicxml
  - extracts a sorted list of unique note-on times (seconds) from the MIDI
    and writes assets/scores/<key>.timemap.json

Both outputs are idempotent. Re-running the script overwrites the files.

Usage:
    python scripts/build_scores.py                 # all keys
    python scripts/build_scores.py bwv639 exemple4 # selected keys only
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import mido

ROOT = Path(__file__).resolve().parent.parent
MIDI_DIR = ROOT / "assets" / "midi"
SCORES_DIR = ROOT / "assets" / "scores"
MUSESCORE_CLI = Path(r"C:/Program Files/MuseScore 4/bin/MuseScore4.exe")

# MIDI keys we want to (pre)render. Each <key>.mid must live in assets/midi/.
MIDI_KEYS = [
    "bwv572_gravement",
    "bwv639",
    "exemple1",
    "exemple2",
    "exemple3",
    "exemple4",
]


def extract_onsets(midi_path: Path) -> list[float]:
    """Return sorted unique absolute onset times (seconds) for all note-ons.
    Channel-agnostic: stops/CCs are ignored because they are not note_on."""
    mid = mido.MidiFile(midi_path)
    onsets: set[float] = set()
    t = 0.0
    for msg in mid:  # iterator yields msg.time already in seconds
        t += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            # Round to 3ms to dedupe chord notes sent a few samples apart
            onsets.add(round(t, 3))
    return sorted(onsets)


def render_musicxml(midi_path: Path, out_path: Path) -> None:
    if not MUSESCORE_CLI.exists():
        raise FileNotFoundError(f"MuseScore CLI not found: {MUSESCORE_CLI}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(MUSESCORE_CLI), str(midi_path), "-o", str(out_path)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def build_one(key: str) -> tuple[int, float]:
    midi_path = MIDI_DIR / f"{key}.mid"
    if not midi_path.exists():
        raise FileNotFoundError(f"MIDI not found: {midi_path}")

    xml_path = SCORES_DIR / f"{key}.musicxml"
    map_path = SCORES_DIR / f"{key}.timemap.json"

    render_musicxml(midi_path, xml_path)
    onsets = extract_onsets(midi_path)
    map_path.write_text(json.dumps({"onsets": onsets}, separators=(",", ":")))

    duration = onsets[-1] if onsets else 0.0
    return len(onsets), duration


def main(argv: list[str]) -> int:
    keys = argv[1:] if len(argv) > 1 else MIDI_KEYS
    unknown = [k for k in keys if k not in MIDI_KEYS and not (MIDI_DIR / f"{k}.mid").exists()]
    if unknown:
        print(f"Unknown keys (no MIDI file found): {unknown}", file=sys.stderr)
        return 2

    SCORES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output dir: {SCORES_DIR}")
    for key in keys:
        n, dur = build_one(key)
        print(f"  {key:30s}  {n:5d} onsets  {dur:7.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
