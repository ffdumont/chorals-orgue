"""Regenere MIDI + MusicXML + timemap pour exemple1/2/3 en preservant la
notation originale (rondes/croches propres) mais au tempo reel des videos.

Les videos YouTube ont ete capturees en envoyant des note_on/note_off
inline (pas depuis un fichier MIDI), a un tempo plus rapide que les
fichiers MIDI originaux stockes dans assets/midi/. D'ou decalage entre
la position du curseur et ce qu'on entend.

Solution propre : on reprend les MIDI originaux depuis git (tempo 40 BPM,
notation propre) et on CHANGE LE TEMPO (pas les ticks !) pour qu'ils
jouent 2x plus vite. MuseScore regenere alors le MusicXML avec la meme
notation qu'avant, mais le timemap extrait du MIDI scale correspond au
vrai tempo des videos.

Facteurs de scale (chord_dur_current / chord_dur_old):
  exemple1 : 3.04 / 6 = 0.507 (chord4_go, stagger 40ms, dur=3)
  exemple2 : 3.016 / 6 = 0.503 (chord3_sap, stagger 16ms, dur=3)
  exemple3 : 2.9 / 6 = 0.483 (ornementation complexe, dur total 2.9s)

Lead-in 0.3s est ajoute au timemap mais PAS au MIDI : on ne veut pas
que MuseScore insere un silence initial qui gonflerait le compte des
positions du curseur OSMD.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import mido

ROOT = Path(__file__).resolve().parent.parent
SCORES_DIR = ROOT / "assets" / "scores"
MIDI_DIR = ROOT / "assets" / "midi"
LEAD_IN = 0.3          # cf. record_all_videos.py ligne ~95
OLD_COMMIT = "0f1862f"  # commit avant regeneration des exemples

# (key, scale_factor) : ratio duree_accord_reelle / duree_accord_ancien_midi
EXEMPLES = [
    ("exemple1", 3.04 / 6.0),    # chord4_go stagger 40ms + dur=3
    ("exemple2", 3.016 / 6.0),   # chord3_sap stagger 16ms + dur=3
    ("exemple3", 2.9 / 6.0),     # ornementations cumul 2.9s
]


def fetch_old_midi(key: str) -> Path:
    """Recupere depuis git l'ancien MIDI d'un exemple."""
    tmp_path = Path("C:/Users/franc/AppData/Local/Temp") / f"old_{key}.mid"
    r = subprocess.run(
        ["git", "show", f"{OLD_COMMIT}:assets/midi/{key}.mid"],
        cwd=str(ROOT), capture_output=True, check=True,
    )
    tmp_path.write_bytes(r.stdout)
    return tmp_path


def scale_midi_tempo(old_path: Path, scale: float) -> mido.MidiFile:
    """Scale les event set_tempo d'un MIDI (et seulement eux) pour le
    faire jouer plus vite/lent sans changer la notation."""
    old = mido.MidiFile(str(old_path))
    new = mido.MidiFile(ticks_per_beat=old.ticks_per_beat)
    for track in old.tracks:
        nt = mido.MidiTrack()
        for msg in track:
            if msg.type == "set_tempo":
                nt.append(msg.copy(tempo=round(msg.tempo * scale)))
            else:
                nt.append(msg.copy())
        new.tracks.append(nt)
    return new


def extract_onsets(midi: mido.MidiFile, lead_in: float = 0.0) -> list[float]:
    """Extrait les onsets uniques (secondes) du MIDI, + lead_in."""
    t = 0.0
    onsets: set[float] = set()
    for msg in midi:
        t += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            onsets.add(round(t + lead_in, 3))
    return sorted(onsets)


def process_exemple(key: str, scale: float) -> None:
    print(f"\n=== {key} (scale={scale:.3f}) ===")
    old_path = fetch_old_midi(key)

    new_midi = scale_midi_tempo(old_path, scale)
    new_midi_path = MIDI_DIR / f"{key}.mid"
    new_midi.save(str(new_midi_path))

    old_tempo_us = 1_500_000  # 40 BPM pour tous les exemples
    new_tempo_us = round(old_tempo_us * scale)
    print(f"  tempo: 40 BPM -> {60_000_000 / new_tempo_us:.0f} BPM")
    print(f"  wrote {new_midi_path}")

    # Regenere le MusicXML via build_scores.py
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_scores.py"), key],
        check=True,
    )

    # Ecrase le timemap produit par build_scores.py (qui utilise une
    # tolerance de rounding trop fine) avec notre extraction + lead-in
    onsets = extract_onsets(new_midi, lead_in=LEAD_IN)
    path = SCORES_DIR / f"{key}.timemap.json"
    path.write_text(json.dumps({"onsets": onsets}, separators=(",", ":")))
    print(f"  {len(onsets)} onsets, last at {onsets[-1]:.2f}s  ->  {path.name}")


def main() -> int:
    print(f"Regenerating exemples with tempo-scaled MIDIs from git {OLD_COMMIT}")
    for key, scale in EXEMPLES:
        process_exemple(key, scale)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
