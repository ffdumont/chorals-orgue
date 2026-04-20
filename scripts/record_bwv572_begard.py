"""
Enregistre BWV 572 Gravement sur l'orgue Begard (demo) en MP4
(video ecran 2 + audio loopback).

Prerequis :
- GrandOrgue ouvert avec l'orgue *Begard demo* charge
- Tous les jeux Begard *eteints* au depart (pas de A.G. sur Begard demo)
- loopMIDI Port 1 visible
- Ecran 2 non recouvert
- Aucun son parasite
"""
import os
import time
import mido

from record_video import VideoRecorder
from stops_control_begard import Stops, PRESETS, PRESET_COUPLERS

OUT_DIR = r'D:/Projects/chorals-orgue/assets/video'
MIDI_PATH = r'D:/Projects/chorals-orgue/assets/midi/bwv572_gravement.mid'
OUT_NAME = 'bwv572_gravement_begard'
TAIL_SECONDS = 5.0  # laisser mourir la reverbe sur l'accord final

# Mise en scene avant la musique
LEAD_IN_SECONDS = 2.5      # silence apres start record, console encore vide
STOP_PULL_INTERVAL = 1.0   # delai entre chaque tirage de jeu (visible)
COUPLER_PULL_INTERVAL = 1.0
CONTEMPLATIVE_PAUSE = 3.0  # pause apres registration complete, avant la musique


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    out = mido.open_output('loopMIDI Port 1')
    time.sleep(0.3)
    stops = Stops(out)

    print('IMPORTANT : Begard demo charge, ecran 2 degage, silence total.')
    print('Demarrage dans 3 s...')
    time.sleep(3)

    # === PHASE OFF-RECORD : preparation propre + warmup ===
    # 1) A.G. pour partir d'un etat connu (tous jeux et accouplements OFF)
    print('A.G. pre-record (etat propre)...')
    stops.general_cancel()
    time.sleep(0.5)

    # 2) Pre-tirage des jeux (la console montrera la registration au start record)
    print('Pre-tirage off-record : plein_jeu + I/P...')
    stops.toggle_many(PRESETS['plein_jeu'])
    for c in PRESET_COUPLERS['plein_jeu']:
        stops.toggle_coupler(c)
        time.sleep(0.05)
    time.sleep(0.5)

    # 3) Warmup audio engine (note breve sur la registration, sans capture)
    print('Warmup audio engine...')
    out.send(mido.Message('note_on', channel=1, note=60, velocity=70))
    time.sleep(0.5)
    out.send(mido.Message('note_off', channel=1, note=60, velocity=0))
    time.sleep(0.6)

    # === PHASE ON-RECORD ===
    print('Start record...')
    rec = VideoRecorder()
    rec.start()

    # 4) Lead-in : la console est pleine, on contemple la registration
    print(f'Lead-in {LEAD_IN_SECONDS:.1f} s (registration visible)...')
    time.sleep(LEAD_IN_SECONDS)

    # 5) A.G. AUDIBLE : petit clic mecanique de l'annulateur, jeux qui rentrent
    print('A.G. (audible)...')
    stops.general_cancel()
    time.sleep(1.5)  # silence apres A.G., console vide

    # 6) Re-tirage lent des jeux, un par un (clics visibles + audibles)
    print('Re-tirage des jeux (1/s)...')
    for s in PRESETS['plein_jeu']:
        print(f'  -> {s}')
        stops.toggle(s)
        time.sleep(STOP_PULL_INTERVAL)

    # 7) Re-tirage des accouplements
    print('Re-tirage des accouplements...')
    for c in PRESET_COUPLERS['plein_jeu']:
        print(f'  -> {c}')
        stops.toggle_coupler(c)
        time.sleep(COUPLER_PULL_INTERVAL)

    # 8) Pause contemplative avant la musique
    print(f'Pause contemplative {CONTEMPLATIVE_PAUSE:.1f} s...')
    time.sleep(CONTEMPLATIVE_PAUSE)

    # 9) Play full MIDI
    print(f'Playing {MIDI_PATH}...')
    notes_on = set()
    try:
        mid = mido.MidiFile(MIDI_PATH)
        for msg in mid.play():
            if msg.is_meta:
                continue
            out.send(msg)
            if msg.type == 'note_on' and msg.velocity > 0:
                notes_on.add((msg.channel, msg.note))
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                notes_on.discard((msg.channel, msg.note))
        # Laisser mourir la reverbe
        print(f'Tail {TAIL_SECONDS:.1f} s...')
        time.sleep(TAIL_SECONDS)
    finally:
        # Stop capture
        mp4 = os.path.join(OUT_DIR, f'{OUT_NAME}.mp4')
        print(f'Stop record -> {mp4}')
        rec.stop_and_save_mp4(mp4)

        # Coupe notes residuelles + A.G. pour tout retirer proprement
        for ch, n in notes_on:
            out.send(mido.Message('note_off', channel=ch, note=n, velocity=0))
        time.sleep(0.2)
        stops.general_cancel()
        time.sleep(0.3)
        out.close()
        print('Termine.')


if __name__ == '__main__':
    main()
