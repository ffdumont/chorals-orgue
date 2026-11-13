"""Extract a time->note onset map from a MIDI file for the OSMD/YouTube sync prototype.

Output JSON format:
    {"onsets": [0.0, 1.234, 2.456, ...]}

Each onset is a unique absolute time in seconds where at least one note-on
occurred on a played channel. This list is meant to map 1:1 to OSMD cursor
positions ("time steps") when the MusicXML is rendered.
"""
import json
import sys
from pathlib import Path

import mido

MIDI_PATH = Path(__file__).parent.parent / "assets" / "midi" / "bwv572_gravement.mid"
OUT_PATH = Path(__file__).parent / "timemap.json"

# Channels on which notes are actually played (see CLAUDE.md)
# mido channels are 0-indexed: GO = 1, Pedal = 0
PLAYED_CHANNELS = {0, 1}


def extract_onsets(midi_path: Path) -> list[float]:
    mid = mido.MidiFile(midi_path)
    onsets: set[float] = set()

    # Walk the merged event stream so tempo changes are honored.
    abs_time = 0.0
    for msg in mid:  # mid.__iter__ yields messages with .time in seconds already
        abs_time += msg.time
        if msg.type == "note_on" and msg.velocity > 0 and getattr(msg, "channel", None) in PLAYED_CHANNELS:
            # Round to 3ms to deduplicate chord notes that are nominally simultaneous
            onsets.add(round(abs_time, 3))

    return sorted(onsets)


def main() -> int:
    if not MIDI_PATH.exists():
        print(f"MIDI file not found: {MIDI_PATH}", file=sys.stderr)
        return 1

    onsets = extract_onsets(MIDI_PATH)
    OUT_PATH.write_text(json.dumps({"onsets": onsets}, indent=None))
    total = onsets[-1] if onsets else 0.0
    print(f"Extracted {len(onsets)} unique onsets, last at {total:.2f}s -> {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
