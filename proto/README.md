# Prototype — Partition synchronisee (BWV 572)

Preuve de concept pour afficher la partition (rendue par OpenSheetMusicDisplay
a partir du MusicXML genere depuis le MIDI) et faire avancer un curseur en
synchronisation avec la video YouTube.

## Comment tester

```bash
cd proto
python -m http.server 8000
```

Puis ouvrir <http://localhost:8000/bwv572_sync.html>.

Pourquoi passer par `http.server` ? Les embeds YouTube et les requetes `fetch()`
pour le MusicXML echouent si la page est ouverte en `file://`.

## Regenerer les assets

```bash
# 1. MusicXML depuis le MIDI
"C:/Program Files/MuseScore 4/bin/MuseScore4.exe" \
  ../assets/midi/bwv572_gravement.mid \
  -o bwv572_gravement.musicxml

# 2. timemap (onsets en secondes)
python build_timemap.py
```

## Calibration

Le `<input id="offset">` en haut de page applique un decalage constant entre
le temps YouTube et le temps MIDI. Le warmup GrandOrgue et le silence en debut
de capture introduisent un delai : commencer a 0, puis ajuster par paliers de
0.5s jusqu'a ce que le curseur tombe sur la note entendue.

## Limites connues

- Si le nombre d'"onset steps" du MusicXML (cursor.next) ne correspond pas au
  nombre d'onsets MIDI (725), la synchro derive au fil de la piece. MuseScore
  peut quantifier differemment des notes tres proches dans le MIDI original
  (620 evenements de tempo -> rubato important).
- Le curseur OSMD n'a pas d'API "reculer d'un pas" par timestamp : un
  scrub-back dans la video declenche un `cursor.reset()` + rebobinage complet.
- L'iframe YouTube doit etre servi sur une origine HTTP(S), pas file://.

## Si la synchro derive

Deux pistes :
1. Calibrer un offset variable : decouper la piece en segments et calibrer
   chacun (mesure 1-32, 33-64, etc.).
2. Indexer par mesure plutot que par note : extraire les temps de debut de
   mesure du MIDI, et avancer le curseur d'une mesure a la fois en utilisant
   `osmd.cursor.iterator.currentMeasure`.
