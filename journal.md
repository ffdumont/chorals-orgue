---
layout: default
title: Journal
nav_order: 6
permalink: /journal/
---

# Journal du wiki

Cette page recense les ajouts et modifications notables apportés au wiki : nouvelles pièces, refontes de pages, ajustements techniques. Les entrées sont listées de la plus récente à la plus ancienne.

## 2026-04-20

### Page [Le projet](/chorals-orgue/projet/)

- Ajout d'une page d'introduction décrivant la démarche d'ensemble : apprentissage de l'orgue en autodidacte, orgue virtuel et outils d'analyse MIDI assistés par IA.
- Lien mis en avant depuis l'accueil.

### Page [Setup technique](/chorals-orgue/setup/)

- Création de la page documentant l'architecture logicielle : chaîne de production audio (script Python → loopMIDI → GrandOrgue → MP3), mappings MIDI (claviers, jeux en Control Change), et scripts du dossier `scripts/`.
- Remplacement des schémas ASCII initiaux par des **diagrammes Mermaid** pour une meilleure lisibilité.
- Correction d'une erreur de syntaxe dans le second diagramme Mermaid.

### Page [BWV 639 — Ich ruf zu dir](/chorals-orgue/pieces/bwv639/)

- Création de la page autour du choral *Ich ruf zu dir, Herr Jesu Christ* de Bach (*Orgelbüchlein*).
- **Fusion** de trois pages initialement séparées (démarche pédagogique, 4 exemples progressifs, BWV 639 final) en une seule page structurée.
- Ajout des partitions PNG inline et des lecteurs audio MP3 pour chaque étape.
- Ajustement de la génération des partitions : utilisation de l'option `-T 10` de MuseScore pour recadrer automatiquement les PNG au contenu musical (évite les grandes zones blanches sous la musique).

### Infrastructure

- Mise en place de la structure Jekyll initiale avec le thème *Just the Docs*.
- Activation des commentaires **Giscus** (basés sur GitHub Discussions) sur toutes les pages de contenu.
- Ajout des scripts Python de pilotage MIDI (`stops_control.py`, `play_midi.py`, `humanize.py`, `demo_registration.py`, `record_all.py`).
