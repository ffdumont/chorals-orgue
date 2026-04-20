"""
Test auditif de chaque jeu et accouplement de Begard (demo).

Pour chaque jeu :
- active le jeu (toggle ON)
- joue une courte sequence sur le clavier concerne
- desactive le jeu (toggle OFF)
- pause 1s

Pour les accouplements : toggle, jeu test sur GO ou Pedale, toggle OFF.

Usage :
    python test_begard.py                    # teste tout
    python test_begard.py --only GO          # seulement GO
    python test_begard.py --only REC         # seulement Recit
    python test_begard.py --only PED         # seulement Pedale
    python test_begard.py --only couplers    # seulement accouplements
    python test_begard.py --only enclosure   # seulement pedale d'expression
"""
import argparse
import mido
import time

from stops_control_begard import Stops, CC_STOPS

# Canaux MIDI des claviers (mido 0-indexe)
CHAN_GO = 1      # canal MIDI 2
CHAN_REC = 2    # canal MIDI 3
CHAN_PED = 0    # canal MIDI 1


def play_note(out, channel, note, duration=0.8, velocity=80):
    out.send(mido.Message('note_on', channel=channel, note=note, velocity=velocity))
    time.sleep(duration)
    out.send(mido.Message('note_off', channel=channel, note=note, velocity=0))


def play_arpeggio(out, channel, base=60, duration=0.4):
    """Do majeur arpege : C E G C."""
    for n in [base, base + 4, base + 7, base + 12]:
        play_note(out, channel, n, duration=duration)


def test_stop(stops_ctrl, out, stop_name, channel, base_note=60):
    print(f'  -> {stop_name}')
    stops_ctrl.toggle(stop_name)
    time.sleep(0.3)
    play_arpeggio(out, channel, base=base_note, duration=0.35)
    time.sleep(0.3)
    stops_ctrl.toggle(stop_name)
    time.sleep(0.8)


def test_go(stops_ctrl, out):
    print('\n=== GRAND-ORGUE (canal 2, C4 arpege) ===')
    for stop in ['GO_bourdon16', 'GO_montre8', 'GO_bourdon8',
                 'GO_prestant4', 'GO_doublette']:
        test_stop(stops_ctrl, out, stop, CHAN_GO, base_note=60)


def test_rec(stops_ctrl, out):
    print('\n=== RECIT (canal 3, C4 arpege) ===')
    for stop in ['REC_flute_cheminee8', 'REC_viole8', 'REC_flute_creuse4']:
        test_stop(stops_ctrl, out, stop, CHAN_REC, base_note=60)
    # Tremblant : active + tenue longue avec fonds 8
    print('  -> tremblant (sur REC_flute_cheminee8 + REC_viole8)')
    stops_ctrl.toggle('REC_flute_cheminee8')
    stops_ctrl.toggle('REC_viole8')
    stops_ctrl.toggle('tremblant')
    time.sleep(0.3)
    play_note(out, CHAN_REC, 62, duration=3.0)
    stops_ctrl.toggle('tremblant')
    stops_ctrl.toggle('REC_viole8')
    stops_ctrl.toggle('REC_flute_cheminee8')
    time.sleep(0.8)


def test_ped(stops_ctrl, out):
    print('\n=== PEDALE (canal 1, C2) ===')
    for stop in ['PED_soubasse16', 'PED_basse8']:
        test_stop(stops_ctrl, out, stop, CHAN_PED, base_note=36)


def test_couplers(stops_ctrl, out):
    print('\n=== ACCOUPLEMENTS ===')
    # I/P : jeu au GO, note jouee a la pedale, doit sonner via tirasse
    print('  -> I/P (Tirasse GO) : jeu Montre 8 au GO, note jouee a la pedale')
    stops_ctrl.toggle('GO_montre8')
    stops_ctrl.toggle_coupler('I/P')
    time.sleep(0.3)
    play_note(out, CHAN_PED, 48, duration=1.0)  # C3 a la pedale
    stops_ctrl.toggle_coupler('I/P')
    stops_ctrl.toggle('GO_montre8')
    time.sleep(0.8)

    # II/P : jeu au Recit, note pedale
    print('  -> II/P (Tirasse Recit) : jeu Flute 8 Recit, note jouee a la pedale')
    stops_ctrl.toggle('REC_flute_cheminee8')
    stops_ctrl.toggle_coupler('II/P')
    time.sleep(0.3)
    play_note(out, CHAN_PED, 48, duration=1.0)
    stops_ctrl.toggle_coupler('II/P')
    stops_ctrl.toggle('REC_flute_cheminee8')
    time.sleep(0.8)

    # II/I : jeu au Recit, note jouee au GO, doit sonner via accouplement
    print('  -> II/I (Copula Recit sur GO) : jeu Flute 8 Recit, note au GO')
    stops_ctrl.toggle('REC_flute_cheminee8')
    stops_ctrl.toggle_coupler('II/I')
    time.sleep(0.3)
    play_arpeggio(out, CHAN_GO, base=60, duration=0.4)
    stops_ctrl.toggle_coupler('II/I')
    stops_ctrl.toggle('REC_flute_cheminee8')
    time.sleep(0.8)


def test_enclosure(stops_ctrl, out):
    print('\n=== PEDALE D\'EXPRESSION (Recit) ===')
    # Jeux fonds Recit + tremblant pour bien entendre l'effet d'ouverture
    stops_ctrl.toggle('REC_flute_cheminee8')
    stops_ctrl.toggle('REC_viole8')
    time.sleep(0.3)
    # Ouverture progressive boite fermee -> ouverte en tenue
    stops_ctrl.set_enclosure('recit', 0)
    time.sleep(0.3)
    print('  -> tenue C4 avec boite fermee -> ouverte progressivement')
    out.send(mido.Message('note_on', channel=CHAN_REC, note=62, velocity=80))
    for v in range(0, 128, 4):
        stops_ctrl.set_enclosure('recit', v)
        time.sleep(0.08)
    time.sleep(0.5)
    out.send(mido.Message('note_off', channel=CHAN_REC, note=62, velocity=0))
    time.sleep(0.5)
    # Rouvre completement et eteint les jeux
    stops_ctrl.set_enclosure('recit', 127)
    stops_ctrl.toggle('REC_viole8')
    stops_ctrl.toggle('REC_flute_cheminee8')
    time.sleep(0.8)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only',
                        choices=['GO', 'REC', 'PED', 'couplers', 'enclosure'],
                        help='Tester uniquement un groupe')
    args = parser.parse_args()

    out = mido.open_output('loopMIDI Port 1')
    time.sleep(0.3)
    stops_ctrl = Stops(out)

    try:
        if args.only == 'GO':
            test_go(stops_ctrl, out)
        elif args.only == 'REC':
            test_rec(stops_ctrl, out)
        elif args.only == 'PED':
            test_ped(stops_ctrl, out)
        elif args.only == 'couplers':
            test_couplers(stops_ctrl, out)
        elif args.only == 'enclosure':
            test_enclosure(stops_ctrl, out)
        else:
            test_go(stops_ctrl, out)
            test_rec(stops_ctrl, out)
            test_ped(stops_ctrl, out)
            test_couplers(stops_ctrl, out)
            test_enclosure(stops_ctrl, out)
        print('\nTermine.')
    finally:
        out.close()


if __name__ == '__main__':
    main()
