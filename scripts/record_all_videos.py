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

OUT_DIR = r'D:/Projects/chorals-orgue/assets/video'
os.makedirs(OUT_DIR, exist_ok=True)

CC = {
    'GO_bourdon8': 22, 'GO_flute8': 21, 'GO_prestant4': 23,
    'PED_soubasse': 40, 'PED_bourdon8': 42,
}

# ============ MIDI playback ============

out = mido.open_output('loopMIDI Port 1')

def cc(name):
    out.send(mido.Message('control_change', channel=15, control=CC[name], value=127))
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

def record_example(name, play_fn, stops_on, stops_off_after=None):
    if stops_off_after is None:
        stops_off_after = stops_on

    print(f'\n=== {name} ===')
    rec = VideoRecorder()

    # Pull stops AVANT le start du record pour ne pas filmer le clic
    for s in stops_on:
        cc(s)
    time.sleep(0.5)

    rec.start()
    time.sleep(0.3)  # silence/video lead-in

    play_fn()

    time.sleep(1.0)  # tail
    mp4 = os.path.join(OUT_DIR, f'{name}.mp4')
    rec.stop_and_save_mp4(mp4)

    # Retirer les jeux
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

# ============ Run ============

if __name__ == '__main__':
    import sys
    only = set(sys.argv[1:]) if len(sys.argv) > 1 else None

    print('IMPORTANT : GrandOrgue doit etre sur l\'ecran 2, non recouvert.')
    print('Aucun son parasite pendant l\'enregistrement.')
    time.sleep(2)

    SAP = ['GO_flute8', 'GO_bourdon8', 'PED_soubasse']

    examples = [
        ('exemple1', play_example1, SAP),
        ('exemple2', play_example2, SAP),
        ('exemple3', play_example3, SAP),
        ('exemple4', play_example4, SAP),
        ('bwv639',   play_bwv639,   SAP + ['PED_bourdon8']),
    ]

    if only:
        examples = [e for e in examples if e[0] in only]
        if not examples:
            print(f'Aucune piste ne correspond : {only}')
            sys.exit(1)

    for name, fn, stops in examples:
        record_example(name, fn, stops)

    out.close()
    print(f'\n=== TERMINE === Fichiers dans : {OUT_DIR}')
