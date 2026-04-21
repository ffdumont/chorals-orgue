"""Recalcule les timemap ET le MIDI pour exemple1/2/3.

Les vidéos YouTube de ces trois exemples ont été capturées en envoyant
des note_on/note_off inline depuis record_all_videos.py (pas a partir
d'un fichier MIDI). Les fichiers `assets/midi/exemple{1,2,3}.mid` ont
des timings differents et ne collent pas a l'audio des videos :
la sync derivait d'une noire sur exemple2 entre autres.

Ici on re-simule play_example1/2/3 en comptabilisant les temps au lieu
d'envoyer les messages MIDI, puis on aggrege les onsets (des notes tres
proches dans le temps = meme accord = 1 seul onset pour le curseur OSMD)
et on ecrase les timemap.json correspondants. Les MusicXML ne sont pas
touches (ils continuent d'afficher des rondes, meme si dans la video
les accords durent 3s au lieu de 6s -- c'est un ecart visuel mineur par
rapport a la notation "propre" des rondes).

Lead-in : record_all_videos.py appelle time.sleep(0.3) entre rec.start()
et play_fn(). On inclut donc 0.3s avant le premier onset.
"""
from __future__ import annotations

import json
import random
import subprocess
import sys
from pathlib import Path

import mido

ROOT = Path(__file__).resolve().parent.parent
SCORES_DIR = ROOT / "assets" / "scores"
MIDI_DIR = ROOT / "assets" / "midi"
LEAD_IN = 0.3           # cf. record_all_videos.py ligne ~95
CHORD_MERGE_TOL = 0.05  # onsets dans la meme fenetre = meme accord
TICKS_PER_SEC = 480     # avec tempo=1_000_000 us/beat, 1 beat = 1 sec


class Clock:
    def __init__(self) -> None:
        self.t: float = 0.0
        self.events: list[float] = []

    def sleep(self, d: float) -> None:
        self.t += d

    def on(self) -> None:
        self.events.append(self.t)


def chord3_sap(clock: Clock, dur: float) -> None:
    # bass (ch 0), alto (ch 1), soprano (ch 1) avec stagger 8ms entre chaque
    clock.on(); clock.sleep(0.008)
    clock.on(); clock.sleep(0.008)
    clock.on()
    clock.sleep(dur * 0.92 + dur * 0.08)  # hold + gap


def chord4_go(clock: Clock, dur: float) -> None:
    # 4 notes, stagger 10ms entre chaque
    for _ in range(4):
        clock.on()
        clock.sleep(0.01)
    clock.sleep(dur * 0.92 + dur * 0.08)


def play_orn(clock: Clock, notes_with_dur: list[tuple[int, float]]) -> None:
    for _n, d in notes_with_dur:
        j = random.uniform(0, 0.004)
        clock.sleep(j)
        clock.on()
        clock.sleep(d * 0.9 + max(0.0, d * 0.1 - j))


def simulate_example1() -> list[float]:
    c = Clock()
    c.sleep(LEAD_IN)
    chord4_go(c, 3)
    chord4_go(c, 3)
    chord4_go(c, 3)
    chord4_go(c, 4)
    return c.events


def simulate_example2() -> list[float]:
    c = Clock()
    c.sleep(LEAD_IN)
    chord3_sap(c, 3)
    chord3_sap(c, 3)
    chord3_sap(c, 3)
    chord3_sap(c, 4)
    return c.events


def simulate_example3() -> list[float]:
    random.seed(42)
    c = Clock()
    c.sleep(LEAD_IN)
    # Chord 1 : bass + alto + 8 notes soprano ornees
    c.on()  # bass 53
    c.on()  # alto 69
    play_orn(c, [(72, 0.4), (74, 0.35), (72, 0.35), (70, 0.35),
                 (69, 0.35), (70, 0.35), (72, 0.35), (72, 0.4)])
    # Chord 2
    c.on(); c.on()
    play_orn(c, [(74, 0.4), (75, 0.35), (74, 0.35), (72, 0.35),
                 (70, 0.35), (72, 0.35), (74, 0.35), (74, 0.4)])
    # Chord 3
    c.on(); c.on()
    play_orn(c, [(76, 0.4), (77, 0.35), (76, 0.35), (74, 0.35),
                 (72, 0.35), (74, 0.35), (76, 0.35), (76, 0.4)])
    # Chord 4 (finale, 7 notes)
    c.on(); c.on()
    play_orn(c, [(77, 0.4), (79, 0.3), (81, 0.3), (79, 0.3),
                 (77, 0.3), (76, 0.3), (77, 1.2)])
    return c.events


def merge_onsets(events: list[float], tolerance: float = CHORD_MERGE_TOL) -> list[float]:
    """Regroupe les onsets tres proches (dans la meme fenetre) en un seul
    point : on garde le premier de chaque cluster. Representation OSMD :
    un accord = une seule position de curseur."""
    merged: list[float] = []
    for e in sorted(events):
        if not merged or e - merged[-1] > tolerance:
            merged.append(e)
    return merged


def write_timemap(key: str, onsets: list[float]) -> None:
    path = SCORES_DIR / f"{key}.timemap.json"
    onsets_rounded = [round(o, 3) for o in onsets]
    path.write_text(json.dumps({"onsets": onsets_rounded}, separators=(",", ":")))
    dur = onsets_rounded[-1] if onsets_rounded else 0.0
    print(f"  {key:12s}  {len(onsets_rounded):3d} onsets  last={dur:6.2f}s")


def build_example3_midi() -> Path:
    """Genere exemple3.mid avec le timing reel de play_example3 (31 onsets).
    Evite la desynchro avec OSMD : le MusicXML regenere aura aussi 31
    positions au lieu de 32 avec l'ancien MIDI."""
    random.seed(42)
    events: list[tuple[float, str, int, int]] = []

    def on(t: float, ch: int, note: int) -> None:
        events.append((t, "note_on", ch, note))

    def off(t: float, ch: int, note: int) -> None:
        events.append((t, "note_off", ch, note))

    def orn_block(t0: float, bass: int, alto: int, notes: list[tuple[int, float]]) -> float:
        on(t0, 0, bass)
        on(t0, 1, alto)
        t = t0
        for sop, d in notes:
            j = random.uniform(0, 0.004)
            t += j
            on(t, 1, sop)
            t += d * 0.9
            off(t, 1, sop)
            t += max(0.0, d * 0.1 - j)
        off(t, 0, bass)
        off(t, 1, alto)
        return t

    # IMPORTANT : le MIDI demarre a t=0 (pas de lead-in). MuseScore
    # generait une mesure de silence initiale quand on mettait LEAD_IN
    # comme delai avant la 1ere note, ajoutant une position "rest" au
    # curseur OSMD et cassant la sync (MIDI=31 / OSMD=32). Le lead-in
    # est ajoute seulement au timemap.
    t = 0.0
    t = orn_block(t, 53, 69, [(72, 0.4), (74, 0.35), (72, 0.35), (70, 0.35),
                              (69, 0.35), (70, 0.35), (72, 0.35), (72, 0.4)])
    t = orn_block(t, 46, 70, [(74, 0.4), (75, 0.35), (74, 0.35), (72, 0.35),
                              (70, 0.35), (72, 0.35), (74, 0.35), (74, 0.4)])
    t = orn_block(t, 48, 67, [(76, 0.4), (77, 0.35), (76, 0.35), (74, 0.35),
                              (72, 0.35), (74, 0.35), (76, 0.35), (76, 0.4)])
    t = orn_block(t, 53, 69, [(77, 0.4), (79, 0.3), (81, 0.3), (79, 0.3),
                              (77, 0.3), (76, 0.3), (77, 1.2)])

    events.sort(key=lambda e: e[0])
    mid = mido.MidiFile(ticks_per_beat=TICKS_PER_SEC)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage("set_tempo", tempo=1_000_000, time=0))
    tr.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))

    last_t = 0.0
    for (t_abs, mtype, chan, note) in events:
        delta = max(0, int(round((t_abs - last_t) * TICKS_PER_SEC)))
        vel = 80 if mtype == "note_on" else 0
        tr.append(mido.Message(mtype, channel=chan, note=note, velocity=vel, time=delta))
        last_t = t_abs
    tr.append(mido.MetaMessage("end_of_track", time=0))

    path = MIDI_DIR / "exemple3.mid"
    mid.save(path)
    print(f"  Wrote {path}")
    return path


def main() -> int:
    print(f"Re-generating timemaps to match actual video timings (lead-in {LEAD_IN}s).")
    print(f"Output dir: {SCORES_DIR}")

    ex1 = merge_onsets(simulate_example1())
    ex2 = merge_onsets(simulate_example2())
    ex3 = merge_onsets(simulate_example3())

    print("\nRegenerating exemple3.mid (31 onsets, matching simulation):")
    build_example3_midi()

    # Regenere le MusicXML d'exemple3 depuis le nouveau MIDI. build_scores.py
    # va aussi ecrire sa propre version du timemap ; on ecrase ensuite avec
    # notre version a 31 onsets (la sienne, plus fine au rounding, en donne
    # ~34 ce qui remet du resampling).
    print("\nRegenerating exemple3 MusicXML via build_scores.py:")
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_scores.py"), "exemple3"],
        check=True,
    )

    print("\nWriting final timemaps (overwriting any intermediate versions):")
    write_timemap("exemple1", ex1)
    write_timemap("exemple2", ex2)
    write_timemap("exemple3", ex3)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
