"""Recalcule les timemap des videos exemple1, exemple2, exemple3.

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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCORES_DIR = ROOT / "assets" / "scores"
LEAD_IN = 0.3           # cf. record_all_videos.py ligne ~95
CHORD_MERGE_TOL = 0.05  # onsets dans la meme fenetre = meme accord


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


def main() -> int:
    print(f"Re-generating timemaps to match actual video timings (lead-in {LEAD_IN}s).")
    print(f"Output dir: {SCORES_DIR}")

    ex1 = merge_onsets(simulate_example1())
    ex2 = merge_onsets(simulate_example2())
    ex3 = merge_onsets(simulate_example3())

    write_timemap("exemple1", ex1)
    write_timemap("exemple2", ex2)
    write_timemap("exemple3", ex3)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
