---
layout: default
title: Calibration sync partition/audio
permalink: /calibration/
nav_order: 7
---

{% include sync_head.html %}

# Calibration — sync partition/audio

Page de diagnostic de la synchronisation entre l'audio et le curseur de la partition. On s'en sert pour isoler les sources de dérive observées sur les pièces réelles (BWV 572, BWV 639).

## Pièce de référence

Une gamme de Do majeur la plus simple possible :
- **8 notes** — do, ré, mi, fa, sol, la, si, do
- **1 seconde par note** — tempo métronomique 60 BPM, pas de rubato
- **Une seule voix**, un seul staff, pas d'accord, pas d'ornement
- **Audio** = synthèse sinusoïdale générée directement depuis le MIDI par `scripts/build_calibration.py` — aucune dérive possible entre la source audio et la source MIDI

## Test

<div class="sync-block"
     data-midi-key="calibration_scale"
     data-scores-base="{{ '/assets/scores/' | relative_url }}">
  <audio controls class="sync-player" preload="metadata" src="{{ '/assets/audio/calibration_scale.mp3' | relative_url }}"></audio>
  <div class="score-wrap" style="margin-top:1em;">
    <div class="osmd-host"></div>
  </div>
  <div class="sync-controls">
    <label>Offset (s): <input type="number" class="offset-input" value="0" step="0.1" /></label>
    <label><input type="checkbox" class="cursor-checkbox" checked /> Curseur visible</label>
    <span class="status">Chargement...</span>
  </div>
  <div class="sync-debug">(attendre le chargement puis lancer la lecture)</div>
</div>

## Résultat attendu

- Le curseur démarre sur la première note au moment où l'audio démarre
- Chaque nouvelle note fait avancer le curseur d'un pas, exactement en synchro
- Aucune dérive audible sur les 8 secondes
- Onsets MIDI **=** steps OSMD (les deux doivent être à 8)

## Si ça dérive

Deux causes possibles :

1. **Compteurs différents** (`MIDI=X / OSMD=Y` affiché dans le statut) → MuseScore quantifie différemment les notes proches ; le resampling automatique tente de corriger mais peut introduire du flou
2. **Offset constant** à ajuster dans le champ *Offset (s)* — utile si l'audio a un blanc initial

Sur cette gamme simple, ni l'un ni l'autre ne devrait se déclencher. Si la dérive persiste ici, c'est que le problème est dans la boucle de sync elle-même (latence `requestAnimationFrame`, précision `currentTime`…).

## Infos de debug

Sous les contrôles, la ligne debug affiche en temps réel :

| Champ | Signification |
|---|---|
| `t` | temps courant de l'audio, après soustraction de l'offset |
| `step X/Y` | index du curseur (X sur Y positions totales dans le score rendu) |
| `prev_onset` | temps de l'onset que le curseur vient de franchir |
| `next_onset` | temps de l'onset suivant |
| `drift` | `t - prev_onset` — mesure la distance entre le temps audio et le temps de l'onset courant. Idéalement proche de 0 juste après chaque avancement du curseur |
| `offset` | décalage actuellement appliqué |

## Régénération des assets

```bash
# Gamme MIDI + MP3 (sinusoïdes)
python scripts/build_calibration.py

# MusicXML + timemap
python scripts/build_scores.py calibration_scale
```
