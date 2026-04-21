"""Recalcule les timemap ET le MIDI pour exemple1/2/3.

Les videos YouTube de ces trois exemples ont ete capturees en envoyant
des note_on/note_off inline depuis record_all_videos.py (pas a partir
d'un fichier MIDI). Les fichiers `assets/midi/exemple{1,2,3}.mid` avaient
des timings differents et ne collaient pas a l'audio des videos :
la sync derivait d'une noire sur exemple2 entre autres.

Ici on re-simule play_example1/2/3 en comptabilisant les temps au lieu
d'envoyer les messages MIDI, puis on aggrege les onsets (des notes tres
proches dans le temps = meme accord = 1 seul onset pour le curseur OSMD).

Pour exemple3, on NE simule PAS un nouveau MIDI depuis zero (MuseScore
ajoute alors des silences entre les notes jitterees qui gonflent le
nombre de positions du curseur OSMD). On SCALE l'ancien MIDI (6s/accord
propre) a la vitesse du code actuel (2.9s/accord) : meme structure,
tempo adapte. Le MusicXML conserve ses 32 positions propres.

Lead-in : record_all_videos.py appelle time.sleep(0.3) entre rec.start()
et play_fn(). On inclut 0.3s avant le premier onset dans le timemap.
Dans le MIDI on ne met PAS ce lead-in (MuseScore en ferait un silence
initial, ajoutant une position au curseur OSMD).
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


class Clock:
    def __init__(self) -> None:
        self.t: float = 0.0
        self.events: list[float] = []

    def sleep(self, d: float) -> None:
        self.t += d

    def on(self) -> None:
        self.events.append(self.t)


def chord3_sap(clock: Clock, dur: float) -> None:
    clock.on(); clock.sleep(0.008)
    clock.on(); clock.sleep(0.008)
    clock.on()
    clock.sleep(dur * 0.92 + dur * 0.08)


def chord4_go(clock: Clock, dur: float) -> None:
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


def simulate_example3_chord_starts() -> list[float]:
    """Retourne uniquement les debuts d'accord d'exemple3, pas les
    ornements intermediaires. Utilise pour caler le scaling du MIDI."""
    random.seed(42)
    c = Clock()
    c.sleep(LEAD_IN)
    starts = []
    for notes in [
        [(72, 0.4), (74, 0.35), (72, 0.35), (70, 0.35),
         (69, 0.35), (70, 0.35), (72, 0.35), (72, 0.4)],
        [(74, 0.4), (75, 0.35), (74, 0.35), (72, 0.35),
         (70, 0.35), (72, 0.35), (74, 0.35), (74, 0.4)],
        [(76, 0.4), (77, 0.35), (76, 0.35), (74, 0.35),
         (72, 0.35), (74, 0.35), (76, 0.35), (76, 0.4)],
        [(77, 0.4), (79, 0.3), (81, 0.3), (79, 0.3),
         (77, 0.3), (76, 0.3), (77, 1.2)],
    ]:
        starts.append(c.t)
        c.on(); c.on()
        play_orn(c, notes)
    starts.append(c.t)  # fin apres le 4e accord
    return starts


def merge_onsets(events: list[float], tolerance: float = CHORD_MERGE_TOL) -> list[float]:
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


def scale_old_midi_for_example3() -> tuple[Path, list[float]]:
    """Reprend l'ancien exemple3.mid (6s/accord, 32 onsets, MusicXML
    propre en rondes+croches) et CHANGE LE TEMPO pour que ca joue 2.07x
    plus vite (2.9s/accord). Les durees de notes en ticks restent les
    memes : la notation reste la meme (rondes/croches), seule la vitesse
    change. Retourne le path du nouveau MIDI et les onsets scales."""
    old_path = MIDI_DIR / "_exemple3_orig.mid"
    if not old_path.exists():
        subprocess.run(
            ["git", "show", "0f1862f:assets/midi/exemple3.mid"],
            cwd=str(ROOT), check=True,
            stdout=old_path.open("wb"),
        )

    old = mido.MidiFile(str(old_path))
    scale = 2.9 / 6.0  # nouveau_tempo = ancien * scale (plus petit => plus rapide)

    new = mido.MidiFile(ticks_per_beat=old.ticks_per_beat)
    for track in old.tracks:
        new_track = mido.MidiTrack()
        for msg in track:
            if msg.type == "set_tempo":
                # On scale uniquement le tempo (us/beat). Temps en ticks
                # inchanges -> MuseScore voit les memes durees de notes.
                new_track.append(msg.copy(tempo=round(msg.tempo * scale)))
            else:
                new_track.append(msg.copy())
        new.tracks.append(new_track)

    new_path = MIDI_DIR / "exemple3.mid"
    new.save(str(new_path))
    old_bpm = 60_000_000 / 1_500_000
    new_bpm = old_bpm / scale
    print(f"  Tempo scaled {old_bpm:.0f} -> {new_bpm:.0f} BPM -> {new_path}")

    # Extrait les onsets du nouveau MIDI (avec le tempo modifie), ajoute
    # lead-in, merge accords proches
    t = 0.0
    onsets: set[float] = set()
    for msg in new:
        t += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            onsets.add(round(t + LEAD_IN, 3))
    return new_path, merge_onsets(sorted(onsets))


def main() -> int:
    print(f"Re-generating timemaps to match actual video timings (lead-in {LEAD_IN}s).")
    print(f"Output dir: {SCORES_DIR}")

    ex1 = merge_onsets(simulate_example1())
    ex2 = merge_onsets(simulate_example2())

    print("\nScaling old exemple3.mid to current tempo:")
    _mid3_path, ex3 = scale_old_midi_for_example3()

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
