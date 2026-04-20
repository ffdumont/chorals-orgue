"""
Joueur MIDI simple : envoie un fichier .mid au port loopMIDI Port 1.

Usage :
    python play_midi.py chemin/vers/fichier.mid
    python play_midi.py chemin/vers/fichier.mid --stops doux

L'option --stops tire une registration predefinie avant la lecture :
    doux, fonde, plein_jeu (voir stops_control.py)
"""
import argparse
import mido
import time

from stops_control import Stops, PRESETS


def play(path, port_name='loopMIDI Port 1', preset=None):
    out = mido.open_output(port_name)

    if preset:
        if preset not in PRESETS:
            raise ValueError(f'Preset inconnu : {preset}. Disponibles : {list(PRESETS)}')
        stops = Stops(out)
        print(f'Registration "{preset}" : {PRESETS[preset]}')
        stops.toggle_many(PRESETS[preset])
        time.sleep(0.5)

    mid = mido.MidiFile(path)
    print(f'Lecture de {path} ({mid.length:.1f}s)')
    for msg in mid.play():
        if not msg.is_meta:
            out.send(msg)
    print('Termine.')

    if preset:
        time.sleep(0.5)
        stops.toggle_many(PRESETS[preset])  # retirer les jeux

    out.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('midi', help='chemin vers le fichier MIDI')
    p.add_argument('--port', default='loopMIDI Port 1')
    p.add_argument('--stops', default=None,
                   help='preset de registration (doux, fonde, plein_jeu)')
    args = p.parse_args()
    play(args.midi, port_name=args.port, preset=args.stops)
