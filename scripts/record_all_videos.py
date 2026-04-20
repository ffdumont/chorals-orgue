"""
Enregistre automatiquement les 4 exemples + BWV 639 en MP4 (video + audio).
Capture l'ecran 2 (GrandOrgue) via ffmpeg gdigrab et le son systeme via
WASAPI loopback, puis mux en MP4.

Prerequis :
    - GrandOrgue ouvert, orgue Saint-Jean-de-Luz charge, sur l'ecran 2
    - loopMIDI tournant, port "loopMIDI Port 1" visible
    - ecran 2 non recouvert par d'autres fenetres
    - aucun son parasite ne doit jouer pendant l'execution

Duree : ~5-6 min. Resultat dans assets/video/*.mp4.
"""
import mido
import os
import random
import time

from record_video import VideoRecorder
from stops_control import (Stops, CC_STOPS, CC_COUPLERS, STOPS_CHANNEL,
                            PRESETS, PRESET_COUPLERS)

OUT_DIR = r'D:/Projects/chorals-orgue/assets/video'
os.makedirs(OUT_DIR, exist_ok=True)

# Alias pour les noms courts utilises dans ce script (compat historique)
CC = {
    'GO_bourdon8': CC_STOPS['GO_bourdon8'],
    'GO_flute8':   CC_STOPS['GO_flute_harmonique8'],
    'GO_prestant4': CC_STOPS['GO_prestant4'],
    'PED_soubasse': CC_STOPS['PED_soubasse16'],
    'PED_bourdon8': CC_STOPS['PED_bourdon8'],
}

# ============ MIDI playback ============

out = mido.open_output('loopMIDI Port 1')

def cc(name):
    # Accepte soit un alias de CC (ci-dessus), soit un nom direct de CC_STOPS
    num = CC.get(name) or CC_STOPS.get(name)
    if num is None:
        raise ValueError(f'CC inconnu : {name}')
    out.send(mido.Message('control_change', channel=STOPS_CHANNEL, control=num, value=127))
    time.sleep(0.05)

def coupler(name):
    num = CC_COUPLERS[name]
    out.send(mido.Message('control_change', channel=STOPS_CHANNEL, control=num, value=127))
    time.sleep(0.05)

def non(ch, n, v=80):
    out.send(mido.Message('note_on', channel=ch, note=n, velocity=v))

def nof(ch, n):
    out.send(mido.Message('note_off', channel=ch, note=n, velocity=0))

def chord4_go(s, a, t, b, dur):
    for n in [b, t, a, s]:
        non(1, n)
        time.sleep(0.01)
    time.sleep(dur * 0.92)
    for n in [b, t, a, s]:
        nof(1, n)
    time.sleep(dur * 0.08)

def chord3_sap(s, a, bass, dur):
    non(0, bass)
    time.sleep(0.008)
    non(1, a)
    time.sleep(0.008)
    non(1, s)
    time.sleep(dur * 0.92)
    nof(0, bass)
    nof(1, a)
    nof(1, s)
    time.sleep(dur * 0.08)

def record_example(name, play_fn, stops_on, stops_off_after=None, couplers_on=(),
                   tail=1.0):
    if stops_off_after is None:
        stops_off_after = stops_on

    print(f'\n=== {name} ===')
    rec = VideoRecorder()

    # Pull stops + couplers AVANT le start du record pour ne pas filmer le clic
    for s in stops_on:
        cc(s)
    for c in couplers_on:
        coupler(c)
    time.sleep(0.5)

    rec.start()
    time.sleep(0.3)  # silence/video lead-in

    play_fn()

    time.sleep(tail)  # laisser mourir la reverbe avant de couper
    mp4 = os.path.join(OUT_DIR, f'{name}.mp4')
    rec.stop_and_save_mp4(mp4)

    # Retirer les jeux et accouplements
    for c in couplers_on:
        coupler(c)
    for s in stops_off_after:
        cc(s)
    time.sleep(0.3)

# ============ Exemples (copie de record_all.py) ============

def play_example1():
    chord4_go(77, 72, 69, 53, 3)
    chord4_go(77, 74, 70, 46, 3)
    chord4_go(76, 72, 67, 48, 3)
    chord4_go(77, 72, 69, 53, 4)

def play_example2():
    chord3_sap(72, 69, 53, 3)
    chord3_sap(74, 70, 46, 3)
    chord3_sap(76, 67, 48, 3)
    chord3_sap(77, 69, 53, 4)

def play_example3():
    random.seed(42)
    def play_orn(notes_with_dur):
        for n, d in notes_with_dur:
            j = random.uniform(0, 0.004)
            time.sleep(j)
            non(1, n)
            time.sleep(d * 0.9)
            nof(1, n)
            time.sleep(max(0, d * 0.1 - j))

    non(0, 53); non(1, 69)
    play_orn([(72, 0.4), (74, 0.35), (72, 0.35), (70, 0.35),
              (69, 0.35), (70, 0.35), (72, 0.35), (72, 0.4)])
    nof(0, 53); nof(1, 69)

    non(0, 46); non(1, 70)
    play_orn([(74, 0.4), (75, 0.35), (74, 0.35), (72, 0.35),
              (70, 0.35), (72, 0.35), (74, 0.35), (74, 0.4)])
    nof(0, 46); nof(1, 70)

    non(0, 48); non(1, 67)
    play_orn([(76, 0.4), (77, 0.35), (76, 0.35), (74, 0.35),
              (72, 0.35), (74, 0.35), (76, 0.35), (76, 0.4)])
    nof(0, 48); nof(1, 67)

    non(0, 53); non(1, 69)
    play_orn([(77, 0.4), (79, 0.3), (81, 0.3), (79, 0.3),
              (77, 0.3), (76, 0.3), (77, 1.2)])
    nof(0, 53); nof(1, 69)

def play_example4():
    mid = mido.MidiFile(r'D:/Projects/chorals-orgue/assets/midi/exemple4.mid')
    for msg in mid.play():
        if not msg.is_meta:
            out.send(msg)

def play_bwv639():
    mid = mido.MidiFile(r'D:/GrandOrgue/MIDI recordings/ich-ruf-zu-dir-orgue.mid')
    for msg in mid.play():
        if not msg.is_meta:
            out.send(msg)

def play_bwv572_gravement():
    mid = mido.MidiFile(r'D:/Projects/chorals-orgue/assets/midi/bwv572_gravement.mid')
    for msg in mid.play():
        if not msg.is_meta:
            out.send(msg)

# ============ Run ============

if __name__ == '__main__':
    import sys
    only = set(sys.argv[1:]) if len(sys.argv) > 1 else None

    print('IMPORTANT : GrandOrgue doit etre sur l\'ecran 2, non recouvert.')
    print('Aucun son parasite pendant l\'enregistrement.')
    time.sleep(2)

    # Reset deterministe : A.G. coupe tous les jeux + accouplements,
    # puis les pedales d'expression sont ouvertes a 127.
    print('Reset initial (A.G. + enclosures ouvertes)...')
    stops = Stops(out)
    stops.reset()

    # Warmup : sans cela, le tout premier chord de la premiere capture
    # peut tomber avant que le moteur audio de GrandOrgue soit actif
    # (cold start ASIO/WASAPI). On joue une note courte et on la retire.
    print('Warmup GrandOrgue audio engine...')
    cc('GO_flute8')       # pull
    time.sleep(0.3)
    non(1, 60); time.sleep(0.6); nof(1, 60)  # C4 bref
    time.sleep(0.3)
    cc('GO_flute8')       # release
    time.sleep(0.5)

    SAP = ['GO_flute8', 'GO_bourdon8', 'PED_soubasse']

    # (name, play_fn, stops, couplers, tail)
    examples = [
        ('exemple1', play_example1, SAP, (), 1.0),
        ('exemple2', play_example2, SAP, (), 1.0),
        ('exemple3', play_example3, SAP, (), 1.0),
        ('exemple4', play_example4, SAP, (), 1.0),
        ('bwv639',   play_bwv639,   SAP + ['PED_bourdon8'], (), 1.0),
        # BWV 572 se termine sur un accord plein-jeu majestueux : on laisse
        # mourir la reverbe des samples (5s) avant de couper la capture.
        ('bwv572_gravement', play_bwv572_gravement,
         PRESETS['grand_plein_jeu'], PRESET_COUPLERS['grand_plein_jeu'], 5.0),
    ]

    if only:
        examples = [e for e in examples if e[0] in only]
        if not examples:
            print(f'Aucune piste ne correspond : {only}')
            sys.exit(1)

    for name, fn, stops, couplers, tail in examples:
        record_example(name, fn, stops, couplers_on=couplers, tail=tail)

    out.close()
    print(f'\n=== TERMINE === Fichiers dans : {OUT_DIR}')
