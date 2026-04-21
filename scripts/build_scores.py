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
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
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


def extract_barlines(midi_path: Path) -> list[float]:
    """Return barline times in seconds: [0.0, start_of_m2, ..., end_of_last_m].

    N measures => N+1 entries. Respects tempo and time-signature changes.
    Barlines are *inferred* (MIDI has no explicit barline events): they fall
    every ticks_per_measure ticks from the last time-signature change.
    """
    mid = mido.MidiFile(midi_path)
    tpb = mid.ticks_per_beat
    tempo = 500_000  # MIDI default = 120 BPM
    num, denom = 4, 4
    ticks_per_measure = tpb * num * 4 // denom

    current_tick = 0
    current_time = 0.0
    last_barline_tick = 0
    barlines = [0.0]
    last_note_time = 0.0

    for msg in mido.merge_tracks(mid.tracks):
        delta = msg.time  # ticks between previous event and this one
        while delta > 0:
            to_bar = last_barline_tick + ticks_per_measure - current_tick
            step = min(delta, to_bar)
            current_time += mido.tick2second(step, tpb, tempo)
            current_tick += step
            if step == to_bar:
                last_barline_tick = current_tick
                barlines.append(round(current_time, 4))
            delta -= step

        if msg.type == "set_tempo":
            tempo = msg.tempo
        elif msg.type == "time_signature":
            num, denom = msg.numerator, msg.denominator
            ticks_per_measure = tpb * num * 4 // denom
            last_barline_tick = current_tick  # mid-piece time-sig change resets barline
        elif msg.type == "note_on" and msg.velocity > 0:
            last_note_time = current_time

    # Trim trailing barlines past the music (end-of-track padding etc.),
    # keep exactly one barline >= last note to serve as the closing anchor.
    trimmed = [b for b in barlines if b <= last_note_time + 1e-6]
    for b in barlines:
        if b > last_note_time + 1e-6:
            trimmed.append(b)
            break
    return trimmed


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


def consolidate_musicxml(xml_path: Path) -> tuple[int, int]:
    """Strip empty staves produced by MuseScore's MIDI import.

    MuseScore imports each MIDI track as a Piano part with a full grand staff
    (treble + bass). When a track only plays in one hand, the other staff is
    full of rests, making the rendered score twice as tall as needed.

    This pass:
      - Removes <part> elements whose notes are all rests.
      - For each remaining 2-staff part that only has pitched notes on one
        staff, drops the other staff (clef, <staff> markers, and
        other-staff notes/rests). <backup>/<forward> inside such parts are
        stripped (they serve only the multi-staff layout).

    Returns (parts_dropped, staves_collapsed).
    """
    # Preserve the DOCTYPE / encoding prologue (ElementTree drops them on
    # serialization). We'll concat them back.
    raw = xml_path.read_text(encoding="utf-8")
    m = re.search(r"<score-partwise\b", raw)
    header = raw[: m.start()] if m else '<?xml version="1.0" encoding="UTF-8"?>\n'

    tree = ET.parse(xml_path)
    root = tree.getroot()
    part_list = root.find("part-list")

    parts_dropped = 0
    staves_collapsed = 0

    for part in list(root.findall("part")):
        part_id = part.get("id")

        # Collect staves that actually contain pitched notes
        active_staves: set[int] = set()
        for note in part.iter("note"):
            if note.find("pitch") is None:
                continue
            staff_el = note.find("staff")
            active_staves.add(int(staff_el.text) if staff_el is not None else 1)

        if not active_staves:
            # Entirely silent part: drop it and its part-list entry
            root.remove(part)
            if part_list is not None:
                for sp in part_list.findall("score-part"):
                    if sp.get("id") == part_id:
                        part_list.remove(sp)
                        break
            parts_dropped += 1
            continue

        if len(active_staves) >= 2:
            continue  # grand staff genuinely needed

        keep = next(iter(active_staves))
        staves_collapsed += 1

        for measure in part.findall("measure"):
            for attrs in measure.findall("attributes"):
                staves_el = attrs.find("staves")
                if staves_el is not None:
                    attrs.remove(staves_el)
                for clef in list(attrs.findall("clef")):
                    n = clef.get("number")
                    if n and int(n) != keep:
                        attrs.remove(clef)
                for clef in attrs.findall("clef"):
                    clef.attrib.pop("number", None)

            for child in list(measure):
                if child.tag == "note":
                    staff_el = child.find("staff")
                    staff_num = int(staff_el.text) if staff_el is not None else 1
                    if staff_num != keep:
                        measure.remove(child)
                    elif staff_el is not None:
                        child.remove(staff_el)
                elif child.tag in ("backup", "forward"):
                    measure.remove(child)

    # Serialize without XML declaration (we'll prepend the original header)
    body = ET.tostring(root, encoding="unicode")
    xml_path.write_text(header + body, encoding="utf-8")

    return parts_dropped, staves_collapsed


def build_one(key: str) -> tuple[int, float]:
    midi_path = MIDI_DIR / f"{key}.mid"
    if not midi_path.exists():
        raise FileNotFoundError(f"MIDI not found: {midi_path}")

    xml_path = SCORES_DIR / f"{key}.musicxml"
    map_path = SCORES_DIR / f"{key}.timemap.json"

    render_musicxml(midi_path, xml_path)
    dropped, collapsed = consolidate_musicxml(xml_path)
    onsets = extract_onsets(midi_path)
    barlines = extract_barlines(midi_path)
    map_path.write_text(json.dumps(
        {"onsets": onsets, "barlines": barlines},
        separators=(",", ":"),
    ))

    duration = onsets[-1] if onsets else 0.0
    return len(onsets), duration, len(barlines) - 1, dropped, collapsed


def main(argv: list[str]) -> int:
    keys = argv[1:] if len(argv) > 1 else MIDI_KEYS
    unknown = [k for k in keys if k not in MIDI_KEYS and not (MIDI_DIR / f"{k}.mid").exists()]
    if unknown:
        print(f"Unknown keys (no MIDI file found): {unknown}", file=sys.stderr)
        return 2

    SCORES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output dir: {SCORES_DIR}")
    for key in keys:
        n, dur, nmeas, dropped, collapsed = build_one(key)
        extras = []
        if dropped:
            extras.append(f"{dropped} empty part(s) dropped")
        if collapsed:
            extras.append(f"{collapsed} stave(s) collapsed")
        extra_str = f"  [{', '.join(extras)}]" if extras else ""
        print(f"  {key:30s}  {n:5d} onsets  {nmeas:4d} mes.  {dur:7.2f}s{extra_str}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
