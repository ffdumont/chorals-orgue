"""
Module pour piloter les jeux de l'orgue virtuel de Begard (Mutin 1899, demo gratuite)
dans GrandOrgue via MIDI CC.

Prerequis :
- loopMIDI avec un port virtuel "loopMIDI Port 1"
- GrandOrgue avec l'orgue Begard (demo) charge
- MIDI-learn des jeux effectue avec les CC ci-dessous (canal 16)

Le MIDI-learn a ete fait avec la valeur 127. Chaque envoi de CC 127 toggle le jeu.

Mapping claviers :
- Grand-Orgue (I) = canal MIDI 2 (mido channel=1)
- Recit (II) = canal MIDI 3 (mido channel=2)
- Pedale = canal MIDI 1 (mido channel=0)

===========================================================================
VERSION DEMO GRATUITE : 10 jeux sur 21 echantillonnes.
Les jeux ci-dessous sont PRESENTS sur la console virtuelle mais NON
echantillonnes -- les tirer ne produira pas (ou peu) de son :

  Grand-Orgue     : Flute harmonique 8, Flute douce 4, Plein jeu
  Recit expressif : Voix celeste 8, Flageolet 2, Sesquialtera 2 rangs,
                    Basson et Hautbois 8, Trompette 8, Clairon 4
  Pedale          : Contrebasse 16, Basson 16

Pour la version complete : https://piotrgrabowski.pl/begard/ (payante)
===========================================================================
"""
import mido

# Mapping des jeux aux Control Change (canal MIDI 16 = index 15)
# Numeros de CC alignes sur stops_control.py (Saint-Jean-de-Luz) quand possible,
# pour permettre de reutiliser les memes fichiers MIDI entre les deux orgues.
CC_STOPS = {
    # Grand Orgue
    'GO_bourdon16':  20,
    'GO_montre8':    21,
    'GO_bourdon8':   22,
    'GO_prestant4':  23,
    'GO_doublette':  25,   # Doublette 2
    # Recit expressif
    'REC_flute_cheminee8': 27,
    'REC_viole8':          28,
    'REC_flute_creuse4':   29,
    'tremblant':           31,
    # Pedale
    'PED_soubasse16': 40,
    'PED_basse8':     41,
}

STOPS_CHANNEL = 15  # canal MIDI 16 (index 15)

# Accouplements (leviers de pedale sur la console Begard)
CC_COUPLERS = {
    'I/P':  50,   # Tirasse Grand-Orgue
    'II/P': 51,   # Tirasse Recit
    'II/I': 52,   # Copula II/I (Recit sur Grand-Orgue)
}

# Pedale d'expression du Recit (controleur continu, canal 16)
# Value 0 = boite fermee, 127 = boite completement ouverte
CC_ENCLOSURES = {
    'recit': 60,  # grande pedale centrale = swell box Recit
}

# Annulateur General (A.G.) : coupe TOUS les jeux + accouplements en un envoi.
# MIDI-learne sur Begard avec CC 63 canal 16 (meme convention que SJDL).
CC_GENERAL_CANCEL = 63


class Stops:
    """Gestionnaire de tirants pour Begard."""

    def __init__(self, midi_out, port_name='loopMIDI Port 1'):
        self._external_port = midi_out is not None
        self._out = midi_out or mido.open_output(port_name)

    def toggle(self, stop_name):
        if stop_name not in CC_STOPS:
            raise ValueError(f'Jeu inconnu : {stop_name}. '
                             f'Disponibles : {list(CC_STOPS)}')
        cc = CC_STOPS[stop_name]
        self._out.send(mido.Message('control_change',
                                     channel=STOPS_CHANNEL,
                                     control=cc, value=127))

    def toggle_many(self, stop_names):
        import time
        for s in stop_names:
            self.toggle(s)
            time.sleep(0.05)

    def toggle_coupler(self, coupler_name):
        if coupler_name not in CC_COUPLERS:
            raise ValueError(f'Accouplement inconnu : {coupler_name}. '
                             f'Disponibles : {list(CC_COUPLERS)}')
        self._out.send(mido.Message('control_change',
                                     channel=STOPS_CHANNEL,
                                     control=CC_COUPLERS[coupler_name],
                                     value=127))

    def set_enclosure(self, name, value):
        """Positionne la boite expressive. value : 0 (ferme) a 127 (ouvert)."""
        if name not in CC_ENCLOSURES:
            raise ValueError(f'Enclosure inconnue : {name}. '
                             f'Disponibles : {list(CC_ENCLOSURES)}')
        v = max(0, min(127, int(value)))
        self._out.send(mido.Message('control_change',
                                     channel=STOPS_CHANNEL,
                                     control=CC_ENCLOSURES[name], value=v))

    def general_cancel(self):
        """Annulateur General : coupe tous les jeux + accouplements en un envoi.
        Etat absolu, pas un toggle."""
        self._out.send(mido.Message('control_change',
                                     channel=STOPS_CHANNEL,
                                     control=CC_GENERAL_CANCEL, value=127))

    def close(self):
        if not self._external_port:
            self._out.close()


# Presets de registration adaptes aux 10 jeux gratuits de Begard
PRESETS = {
    # Accompagnement doux, solo a une main
    'doux': ['GO_bourdon8', 'PED_soubasse16'],

    # Fonds de 8 au GO avec Prestant, pedale 16+8
    'fonde': ['GO_montre8', 'GO_bourdon8', 'GO_prestant4',
              'PED_soubasse16', 'PED_basse8'],

    # Grand plein-jeu sans mixture (complet sur le gratuit) pour Bach /
    # BWV 572 Gravement : pyramide 16-8-8-4-2 au GO + pedale + tirasse GO.
    # A completer avec le coupler I/P (voir PRESET_COUPLERS).
    'plein_jeu': [
        'GO_bourdon16', 'GO_montre8', 'GO_bourdon8',
        'GO_prestant4', 'GO_doublette',
        'PED_soubasse16', 'PED_basse8',
    ],

    # Recit expressif doux pour dialogues (Tres vitement de BWV 572)
    'recit_fonds': ['REC_flute_cheminee8', 'REC_viole8', 'REC_flute_creuse4'],
}

# Accouplements associes a certains presets
PRESET_COUPLERS = {
    'plein_jeu': ['I/P'],
}
