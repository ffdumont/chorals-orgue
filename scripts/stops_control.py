"""
Module pour piloter les jeux (tirants) de l'orgue virtuel de Saint-Jean-de-Luz
dans GrandOrgue via MIDI CC.

Prerequis :
- loopMIDI avec un port virtuel "loopMIDI Port 1"
- GrandOrgue avec l'orgue Saint-Jean-de-Luz charge
- MIDI-learn des jeux effectue avec les CC ci-dessous (canal 16)

Le MIDI-learn a ete fait avec la valeur 127 a chaque apprentissage.
En consequence, chaque envoi de CC 127 sur ce CC *toggle* l'etat du jeu
(ON si etait OFF, OFF si etait ON).
"""
import mido

# Mapping des jeux aux Control Change (canal MIDI 16 = index 15)
CC_STOPS = {
    # Grand Orgue
    'GO_bourdon16':        20,
    'GO_flute_harmonique8': 21,
    'GO_bourdon8':         22,
    'GO_prestant4':        23,
    'GO_quinte':           24,  # Quinte 2 2/3
    'GO_doublette':        25,  # Doublette 2
    'GO_tierce':           26,  # Tierce 1 3/5
    # Récit expressif
    'REC_flute8':          27,
    'REC_flute4':          28,
    'REC_plein_jeu':       29,
    'REC_trompette':       30,
    'tremblant':           31,
    # Pédale
    'PED_soubasse16':      40,
    'PED_flute8':          41,
    'PED_bourdon8':        42,
    'PED_flute4':          43,
    'PED_flute2':          44,
}

STOPS_CHANNEL = 15  # canal MIDI 16 (index 15)


class Stops:
    """Gestionnaire de tirants (jeux) pour l'orgue virtuel."""

    def __init__(self, midi_out, port_name='loopMIDI Port 1'):
        """
        midi_out : soit un objet mido.ports.Output deja ouvert,
                   soit None (le module ouvre une connexion).
        """
        self._external_port = midi_out is not None
        self._out = midi_out or mido.open_output(port_name)

    def toggle(self, stop_name):
        """Bascule un jeu (ON <-> OFF)."""
        if stop_name not in CC_STOPS:
            raise ValueError(f'Jeu inconnu : {stop_name}. '
                             f'Disponibles : {list(CC_STOPS)}')
        cc = CC_STOPS[stop_name]
        self._out.send(mido.Message('control_change',
                                     channel=STOPS_CHANNEL,
                                     control=cc, value=127))

    def toggle_many(self, stop_names):
        """Bascule plusieurs jeux d'un coup."""
        import time
        for s in stop_names:
            self.toggle(s)
            time.sleep(0.05)  # petit delai pour GrandOrgue

    def close(self):
        if not self._external_port:
            self._out.close()


# Presets de registration
PRESETS = {
    'doux': ['GO_flute_harmonique8', 'GO_bourdon8', 'PED_soubasse16'],
    'fonde': ['GO_flute_harmonique8', 'GO_bourdon8', 'GO_prestant4',
              'PED_soubasse16', 'PED_bourdon8'],
    'plein_jeu': ['GO_bourdon8', 'GO_prestant4', 'GO_doublette',
                  'GO_quinte', 'GO_tierce',
                  'PED_soubasse16', 'PED_bourdon8', 'PED_flute4'],
}
