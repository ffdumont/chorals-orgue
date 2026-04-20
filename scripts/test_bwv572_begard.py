"""
Test auditif rapide : joue les ~2 premieres minutes de BWV 572 Gravement
sur Begard avec le preset 'plein_jeu' (5 jeux GO + 2 jeux Pedale + I/P).

Prerequis :
- GrandOrgue ouvert avec l'orgue *Begard demo* charge (pas Saint-Jean-de-Luz !)
- loopMIDI Port 1 visible
- son systeme audible

Usage :
    python test_bwv572_begard.py              # 120 s
    python test_bwv572_begard.py --duration 60
"""
import argparse
import time
import mido

from stops_control_begard import Stops, PRESETS, PRESET_COUPLERS

MIDI_PATH = r'D:/Projects/chorals-orgue/assets/midi/bwv572_gravement.mid'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', type=float, default=120.0,
                        help='Duree max en secondes (defaut 120)')
    args = parser.parse_args()

    out = mido.open_output('loopMIDI Port 1')
    time.sleep(0.3)
    stops = Stops(out)

    # Tirer le plein-jeu Begard + accouplement I/P
    print('Pull stops : plein_jeu Begard + I/P...')
    stops.toggle_many(PRESETS['plein_jeu'])
    for c in PRESET_COUPLERS['plein_jeu']:
        stops.toggle_coupler(c)
        time.sleep(0.05)
    time.sleep(0.5)

    # Warmup leger : note breve au GO pour activer le moteur audio
    print('Warmup audio engine...')
    out.send(mido.Message('note_on', channel=1, note=60, velocity=70))
    time.sleep(0.4)
    out.send(mido.Message('note_off', channel=1, note=60, velocity=0))
    time.sleep(0.4)

    print(f'Lecture BWV 572 Gravement ({args.duration:.0f} s max)...')
    mid = mido.MidiFile(MIDI_PATH)
    t0 = time.time()
    notes_on = set()  # set de (channel, note) pour clean up a la fin
    try:
        for msg in mid.play():
            if msg.is_meta:
                continue
            out.send(msg)
            if msg.type == 'note_on' and msg.velocity > 0:
                notes_on.add((msg.channel, msg.note))
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                notes_on.discard((msg.channel, msg.note))
            if time.time() - t0 >= args.duration:
                print(f'-> Stop apres {args.duration:.0f} s')
                break
    finally:
        # Coupe toutes les notes encore tenues
        for ch, n in notes_on:
            out.send(mido.Message('note_off', channel=ch, note=n, velocity=0))
        time.sleep(0.3)
        # Retire les jeux et accouplements
        for c in PRESET_COUPLERS['plein_jeu']:
            stops.toggle_coupler(c)
            time.sleep(0.05)
        for s in PRESETS['plein_jeu']:
            stops.toggle(s)
            time.sleep(0.05)
        time.sleep(0.2)
        out.close()
        print('Termine.')


if __name__ == '__main__':
    main()
