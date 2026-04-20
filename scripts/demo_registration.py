"""
Demo musicale qui illustre le pilotage des jeux en temps reel.
Joue une courte improvisation en 5 phases avec registration dynamique :
intime -> enrichissement -> brillance -> grand plein-jeu -> retour au calme.

Requiert l'orgue Saint-Jean-de-Luz charge dans GrandOrgue,
avec le mapping MIDI decrit dans stops_control.py.
"""
import mido
import time
import random

from stops_control import Stops

GO = 1   # canal MIDI 2 (= manuel Grand Orgue)
PED = 0  # canal MIDI 1 (= pedalier)


def play(out, ch, note, dur, jitter=0.008, art=0.92):
    j = random.uniform(0, jitter)
    time.sleep(j)
    out.send(mido.Message('note_on', channel=ch, note=note, velocity=80))
    time.sleep(dur * art)
    out.send(mido.Message('note_off', channel=ch, note=note, velocity=0))
    time.sleep(max(0, dur * (1 - art) - j))


def chord(out, ch, notes, dur, art=0.92):
    for n in notes:
        out.send(mido.Message('note_on', channel=ch, note=n, velocity=80))
        time.sleep(random.uniform(0.003, 0.012))
    time.sleep(dur * art)
    for n in notes:
        out.send(mido.Message('note_off', channel=ch, note=n, velocity=0))
    time.sleep(dur * (1 - art))


def run():
    random.seed(11)
    out = mido.open_output('loopMIDI Port 1')
    stops = Stops(out)

    time.sleep(2)

    # --- Phase 1 : ouverture intime ---
    print('Phase 1 : ouverture')
    stops.toggle('GO_bourdon8')
    stops.toggle('PED_soubasse16')
    time.sleep(0.5)

    out.send(mido.Message('note_on', channel=PED, note=33, velocity=80))
    time.sleep(0.3)
    for n, d in [(69, 1.0), (72, 0.8), (71, 0.8), (69, 1.4)]:
        play(out, GO, n, d)
    time.sleep(0.5)
    out.send(mido.Message('note_off', channel=PED, note=33, velocity=0))

    # --- Phase 2 : enrichissement ---
    print('Phase 2 : + Flute harmonique')
    stops.toggle('GO_flute_harmonique8')
    time.sleep(0.3)

    out.send(mido.Message('note_on', channel=PED, note=31, velocity=80))
    for n, d in [(67, 0.6), (70, 0.6), (72, 0.6), (74, 1.2)]:
        play(out, GO, n, d)
    time.sleep(0.3)
    out.send(mido.Message('note_off', channel=PED, note=31, velocity=0))

    # --- Phase 3 : + Prestant 4 + PED Bourdon 8 ---
    print('Phase 3 : brillance')
    stops.toggle('GO_prestant4')
    stops.toggle('PED_bourdon8')
    time.sleep(0.3)

    bass = [36, 38, 40, 41, 43]
    mel = [(72, 72, 76), (74, 74, 77), (76, 76, 79), (77, 77, 81), (79, 79, 83)]
    for b, (m1, m2, m3) in zip(bass, mel):
        out.send(mido.Message('note_on', channel=PED, note=b, velocity=80))
        play(out, GO, m1, 0.3)
        play(out, GO, m2, 0.3)
        play(out, GO, m3, 0.4)
        time.sleep(0.1)
        out.send(mido.Message('note_off', channel=PED, note=b, velocity=0))

    # --- Phase 4 : plein-jeu ---
    print('Phase 4 : plein-jeu')
    stops.toggle_many(['GO_doublette', 'GO_quinte', 'GO_tierce',
                       'PED_flute4', 'PED_flute2'])
    time.sleep(0.3)

    out.send(mido.Message('note_on', channel=PED, note=36, velocity=80))
    chord(out, GO, [60, 64, 67, 72], 1.5)
    chord(out, GO, [62, 65, 69, 74], 1.2)
    chord(out, GO, [65, 69, 72, 77], 1.2)
    chord(out, GO, [67, 71, 74, 79], 2.0)
    out.send(mido.Message('note_off', channel=PED, note=36, velocity=0))

    out.send(mido.Message('note_on', channel=PED, note=36, velocity=80))
    chord(out, GO, [60, 64, 67, 72], 2.5)
    out.send(mido.Message('note_off', channel=PED, note=36, velocity=0))

    # --- Phase 5 : retour au calme ---
    print('Phase 5 : retour au calme')
    stops.toggle_many(['GO_doublette', 'GO_quinte', 'GO_tierce',
                       'GO_prestant4', 'PED_flute4', 'PED_flute2'])
    time.sleep(0.3)

    out.send(mido.Message('note_on', channel=PED, note=33, velocity=80))
    for n, d in [(69, 1.5), (67, 1.2), (65, 1.2), (64, 1.5)]:
        play(out, GO, n, d, art=0.95)
    chord(out, GO, [57, 60, 64, 69], 3.5)
    out.send(mido.Message('note_off', channel=PED, note=33, velocity=0))
    time.sleep(0.5)

    # Fin : tout retirer
    stops.toggle_many(['GO_bourdon8', 'GO_flute_harmonique8',
                       'PED_soubasse16', 'PED_bourdon8'])
    out.close()
    print('Fin.')


if __name__ == '__main__':
    run()
