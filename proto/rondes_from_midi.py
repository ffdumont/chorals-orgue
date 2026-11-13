"""Supprime les silences d'un MIDI et arrondit chaque accord à une ronde.

Usage:
    python rondes_from_midi.py <input.mid> [output.mid]

Chaque "attaque" (notes pressees dans une fenetre courte) devient un accord
d'une ronde. Les accords sont poses bout-a-bout, sans silence.
"""
from __future__ import annotations

import sys
from pathlib import Path

import mido

CHORD_WINDOW_SEC = 0.05  # notes attaquees dans 50 ms = meme accord
TEMPO_BPM = 60           # 60 bpm -> 1 noire = 1 s, 1 ronde = 4 s
PPQ = 480                # ticks/noire dans le fichier de sortie
WHOLE = PPQ * 4          # 1 ronde = 4 noires


def seconds_to_ticks(sec: float) -> int:
    # a tempo donne et PPQ donne, 1 seconde = PPQ * (BPM / 60) ticks
    return int(round(sec * PPQ * TEMPO_BPM / 60))


def extract_note_ons_seconds(mid: mido.MidiFile) -> list[tuple[float, int, int, int]]:
    """Retourne [(temps_sec, note, velocity, channel), ...] pour les note_on."""
    events: list[tuple[float, int, int, int]] = []
    t = 0.0
    for msg in mid:  # iterer sur le fichier -> temps en secondes
        t += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            events.append((t, msg.note, msg.velocity, msg.channel))
    return events


def group_chords(
    note_ons: list[tuple[float, int, int, int]],
    window: float,
) -> list[list[tuple[int, int, int]]]:
    """Regroupe les notes attaquees dans une fenetre <= window en accords.

    Deduplique : si la meme hauteur/canal est retriggee dans la meme fenetre
    (rebond MIDI), on ne garde qu'une seule occurrence.
    """
    chords: list[list[tuple[int, int, int]]] = []
    current_start: float | None = None
    for t, note, vel, ch in note_ons:
        if current_start is None or t - current_start > window:
            chords.append([(note, vel, ch)])
            current_start = t
        else:
            if any(n == note and c == ch for n, _, c in chords[-1]):
                continue
            chords[-1].append((note, vel, ch))
    return chords


def build_output(chords: list[list[tuple[int, int, int]]]) -> mido.MidiFile:
    out = mido.MidiFile(ticks_per_beat=PPQ)
    track = mido.MidiTrack()
    out.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(TEMPO_BPM), time=0))
    track.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))

    for chord in chords:
        # attaques simultanees
        for i, (note, vel, ch) in enumerate(chord):
            track.append(
                mido.Message(
                    "note_on",
                    note=note,
                    velocity=max(vel, 64),
                    channel=ch,
                    time=0,
                )
            )
        # relachees simultanees une ronde plus tard
        for i, (note, _, ch) in enumerate(chord):
            track.append(
                mido.Message(
                    "note_off",
                    note=note,
                    velocity=0,
                    channel=ch,
                    time=WHOLE if i == 0 else 0,
                )
            )
    track.append(mido.MetaMessage("end_of_track", time=0))
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_name(src.stem + "_rondes.mid")

    mid = mido.MidiFile(src)
    note_ons = extract_note_ons_seconds(mid)
    if not note_ons:
        print("Aucune note trouvee dans le fichier.")
        return 1

    chords = group_chords(note_ons, CHORD_WINDOW_SEC)

    out = build_output(chords)
    out.save(dst)

    total_notes = sum(len(c) for c in chords)
    print(f"Entree  : {src}")
    print(f"Sortie  : {dst}")
    print(f"Accords : {len(chords)} (soit {total_notes} notes au total)")
    print(f"Duree   : {len(chords)} rondes @ {TEMPO_BPM} bpm "
          f"= {len(chords) * 4} s")
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    for i, chord in enumerate(chords, 1):
        pretty = " + ".join(f"{names[n % 12]}{n // 12 - 1}" for n, _, _ in chord)
        print(f"  accord {i}: {pretty}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
