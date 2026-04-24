---
layout: default
title: Journal
nav_order: 6
permalink: /journal/
---

# Journal du wiki

Cette page recense les ajouts et modifications notables apportés au wiki : nouvelles pièces, refontes de pages, ajustements techniques. Les entrées sont listées de la plus récente à la plus ancienne.

## 2026-04-24

### Page [BWV 939 — Petit Prélude en Do majeur](/chorals-orgue/pieces/bwv939/)

- Ajout d'un court prélude pédagogique issu des *Cinq Petits Préludes* BWV 939-943 : arpèges brisés main droite sur rondes tenues main gauche, 15 mesures en Do majeur, pièce pour clavier (pas de pédalier).
- Version jouée en **tempo d'étude ♩ = 70** (plus lent que l'*Allegretto* ♩ = 100 de l'arrangement Ben Choupak récupéré sur Musescore), pour faire entendre chaque croche et la progression harmonique.
- Registration douce : **Flûte harmonique 8' + Bourdon 8'** au Grand Orgue de Saint-Jean-de-Luz (Chœur).
- Côté pipeline : ajout d'une fonction `play_bwv939()` dans [scripts/record_all_videos.py](https://github.com/ffdumont/chorals-orgue/blob/main/scripts/record_all_videos.py) ; MusicXML source récupéré depuis l'arrangement Choupak (MusicTake) et converti en MIDI via MuseScore 4 CLI ; canaux MIDI remappés sur le Grand Orgue (canal 2) puisque la pièce n'a pas de partie de pédalier.

## 2026-04-20

### Page [BWV 572 — Pièce d'orgue (Gravement)](/chorals-orgue/pieces/bwv572/) — version Bégard

- Ajout d'une **deuxième version** du *Gravement* jouée sur le grand orgue romantique Mutin 1899 de Bégard (banque démo Piotr Grabowski, 10 jeux échantillonnés sur 21). La page est restructurée pour présenter en miroir les deux versions ("orgue de chœur vs grand orgue") et compare ce qu'on entend de différent : Saint-Jean-de-Luz brillante avec ses mutations et sa mixture, Bégard plus ronde et chantante dans la tradition Cavaillé-Coll/Mutin.
- Registration Bégard : tous les fonds disponibles au Grand-Orgue (Bourdon 16, Montre 8, Bourdon 8, Prestant 4, Doublette 2), Soubasse 16 + Basse 8 à la Pédale, accouplement I/P. Récit non utilisé (sans mixture ni anche échantillonnées en démo).
- Mise en scène ajoutée à l'enregistrement : déclenchement de l'**Annulateur Général** au démarrage avec le petit clic mécanique audible, puis tirage des jeux un par un avant la pause contemplative qui précède la musique.
- Côté code : nouveau module [scripts/stops_control_begard.py](https://github.com/ffdumont/chorals-orgue/blob/main/scripts/stops_control_begard.py) (mapping MIDI Bégard, A.G. sur CC 63 comme SJDL), renommage de `stops_control.py` en `stops_control_sjdl.py`, scripts dédiés [test_begard.py](https://github.com/ffdumont/chorals-orgue/blob/main/scripts/test_begard.py) et [record_bwv572_begard.py](https://github.com/ffdumont/chorals-orgue/blob/main/scripts/record_bwv572_begard.py). Le même fichier MIDI `bwv572_gravement.mid` est rejoué tel quel sur les deux orgues — seule la registration change.

### Page [BWV 572 — Pièce d'orgue (Gravement)](/chorals-orgue/pieces/bwv572/)

- Ajout d'une démo "grand plein-jeu" avec 15 des 17 jeux de l'orgue de Saint-Jean-de-Luz (88 %) : tous les jeux du Grand Orgue et du Récit (y compris la Trompette 8 pour plus d'éclat), fonds de Pédale, avec accouplements II/I et I/P.
- Section *Gravement* extraite automatiquement du MIDI complet (séquence Dean Lampe, Kunst der Fuge) par détection de frontière entre les sections (changement de mesure 12/8 → 4/4 et densité de notes).
- Nouveau preset `grand_plein_jeu` dans [scripts/stops_control_sjdl.py](https://github.com/ffdumont/chorals-orgue/blob/main/scripts/stops_control_sjdl.py) avec accouplements associés via `PRESET_COUPLERS`. Extension de [scripts/play_midi.py](https://github.com/ffdumont/chorals-orgue/blob/main/scripts/play_midi.py) et [scripts/record_all_videos.py](https://github.com/ffdumont/chorals-orgue/blob/main/scripts/record_all_videos.py) pour gérer les accouplements dans un preset.

### Bascule MP3 → vidéos YouTube

- Remplacement des lecteurs audio MP3 par des vidéos YouTube (non-répertoriées) embarquées en iframe : on voit désormais la console GrandOrgue avec les jeux tirés et les touches qui bougent pendant l'écoute.
- Chaîne dédiée : [Chorals d'orgue](https://www.youtube.com/channel/UCDuYey5ZKESuB-ZyJrJrvUg).
- Pipeline d'automatisation ajoutée : capture de l'écran GrandOrgue + audio loopback via `ffmpeg`/`soundcard`, upload YouTube via l'API Data v3, puis mise à jour automatique des pages markdown. Nouveaux scripts : `record_video.py`, `record_all_videos.py`, `youtube_auth.py`, `upload_youtube.py`, `update_embeds.py`.

### Page [Le projet](/chorals-orgue/projet/)

- Ajout d'une page d'introduction décrivant la démarche d'ensemble : apprentissage de l'orgue en autodidacte, orgue virtuel et outils d'analyse MIDI assistés par IA.
- Lien mis en avant depuis l'accueil.
- **Révision** : retrait des objectifs chiffrés (durées, prix, calendrier) pour enlever toute pression inutile.
- **Révision** : reformulation moins technique et plus musicale, à destination des mélomanes familiers de l'enseignement classique de l'orgue (vocabulaire organistique, la tradition posée comme boussole, l'outil comme complément du maître).

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
