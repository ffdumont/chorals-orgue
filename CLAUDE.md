# Contexte projet — Chorals d'orgue

Ce fichier est destiné à Claude Code pour reprendre rapidement le contexte du projet. Il résume ce qu'est le projet, sa stack, les conventions, et les dépendances externes non évidentes.

## Vue d'ensemble

Site wiki en Jekyll hébergé sur **GitHub Pages** qui présente des pièces d'orgue avec :
- Partitions affichées inline (PNG générés depuis MIDI via MuseScore CLI)
- Enregistrements MP3 produits automatiquement par des scripts Python
- Commentaires via Giscus (GitHub Discussions)

URL publique : https://ffdumont.github.io/chorals-orgue/
Repo : https://github.com/ffdumont/chorals-orgue

L'utilisateur est **@ffdumont** (François Dumont, francois.dumont1@gmail.com), organiste amateur non-développeur mais à l'aise avec Windows.

## Stack

- **Jekyll 4** avec `remote_theme: just-the-docs/just-the-docs`
- **Giscus** pour les commentaires (nécessite auth GitHub pour poster)
- **Python 3.10+** pour les scripts (pas d'environnement virtuel spécifique)
- Dépendances Python : `mido`, `python-rtmidi`, `soundcard`, `soundfile`
- **ffmpeg** pour l'encodage MP3 (installé à `C:/Program Files/ffmpeg-7.0.2-essentials_build/bin/ffmpeg.exe`)
- **MuseScore 4** pour générer PNG depuis MIDI (`C:/Program Files/MuseScore 4/bin/MuseScore4.exe`)

## Arborescence

```
chorals-orgue/
├── _config.yml             # Jekyll config + Giscus IDs
├── _includes/giscus.html   # Widget commentaires
├── _layouts/default.html   # Ajoute Giscus aux pages de contenu
├── index.md                # Accueil
├── pieces/
│   ├── demarche.md         # Narratif pédagogique
│   ├── exemples-basiques.md # 4 exemples progressifs
│   ├── bwv639.md           # BWV 639
│   └── setup-technique.md  # Doc technique (architecture, mappings MIDI)
├── assets/
│   ├── audio/*.mp3         # Enregistrements
│   ├── images/*.png        # Partitions rendues
│   └── midi/*.mid          # Fichiers MIDI sources
└── scripts/
    ├── stops_control.py    # Module : table CC_STOPS + classe Stops
    ├── play_midi.py        # CLI : joue un .mid sur loopMIDI
    ├── humanize.py         # Applique jitter + articulation à un .mid
    ├── demo_registration.py # Démo avec registration dynamique
    └── record_all.py       # Pipeline d'enregistrement des 5 pistes
```

## Dépendances externes (hors repo)

Ces éléments sont **obligatoires pour faire tourner les scripts** mais ne sont pas dans le repo (trop volumineux ou externes).

### GrandOrgue + orgue Saint-Jean-de-Luz

- **GrandOrgue** installé à `D:/GrandOrgue/` (app + données utilisateur)
- **Orgue Saint-Jean-de-Luz (Choeur)** à `D:/OrganSamples/Saint-Jean-de-Luz (choeur).organ` (~14 GB de samples)
- Banque gratuite de Piotr Grabowski ([piotrgrabowski.pl/saint-jean-de-luz-choeur](https://piotrgrabowski.pl/saint-jean-de-luz-choeur/))
- Backup config MIDI : `D:/GrandOrgue/Data/backup-midi-mapping.cmb`

### loopMIDI

- Pilote de ports MIDI virtuels
- Port configuré : `loopMIDI Port` (apparaît comme `loopMIDI Port 0` en entrée et `loopMIDI Port 1` en sortie)
- **Bug Windows 11** : sur 24H2+, les ports sont invisibles tant que `midisrv` n'a pas été redémarré après création. Commande : `powershell -Command "Restart-Service -Name midisrv -Force"` (non destructif, peut être lancé à tout moment).

## Mappings MIDI (cœur du projet)

**Claviers** (Note On/Off) :
- Grand Orgue = canal MIDI 2 (mido `channel=1`)
- Pédale = canal MIDI 1 (mido `channel=0`)
- Récit = non mappé

**Jeux** : tous sur canal MIDI 16 (mido `channel=15`), Control Change avec valeur 127 (toggle ON/OFF à chaque envoi). Liste complète dans [scripts/stops_control.py](scripts/stops_control.py) et documentée dans [pieces/setup-technique.md](pieces/setup-technique.md).

Extrait rapide :
- CC 20-26 = jeux Grand Orgue (Bourdon 16, Flûte harm. 8, Bourdon 8, Prestant 4, Quinte 2 2/3, Doublette 2, Tierce 1 3/5)
- CC 27-30 = jeux Récit (Flûte 8, Flûte 4, Plein-jeu III, Trompette 8)
- CC 31 = Tremblant
- CC 40-44 = jeux Pédale (Soubasse 16, Flûte 8, Bourdon 8, Flûte 4, Flûte 2)

## Workflows typiques

### Jouer un MIDI via GrandOrgue

```bash
cd scripts
python play_midi.py ../assets/midi/exemple4.mid --stops fonde
```

Prérequis : GrandOrgue ouvert avec l'orgue chargé, loopMIDI tournant, port visible (voir bug Win11 ci-dessus).

### Regénérer tous les enregistrements MP3

```bash
cd scripts
python record_all.py
```

Durée ~5-6 min, aucun son parasite pendant l'exécution. Résultat dans `assets/audio/`.

### Ajouter une nouvelle pièce

1. Placer le fichier MIDI dans `assets/midi/`
2. Générer la partition PNG : `"C:/Program Files/MuseScore 4/bin/MuseScore4.exe" fichier.mid -o fichier.png -T 10` (crée `fichier-1.png` pour la page 1). L'option `-T 10` recadre automatiquement l'image au contenu musical avec une marge de 10px — sans elle, MuseScore exporte la page A4 complète et laisse beaucoup de blanc sous la musique dans le wiki.
3. Ajouter la page Markdown dans `pieces/` avec `<audio controls>` + `![partition]()`
4. Enregistrer le MP3 (adapter `record_all.py` ou créer un nouveau script)
5. Commit + push → GitHub Pages rebuild automatique (~1-2 min)

## Commit / déploiement

Le repo est public, les commits sont en français ou anglais selon le contexte. Git config inline utilisée dans les scripts (pas besoin de config globale) :

```bash
git -c user.email="francois.dumont1@gmail.com" -c user.name="ffdumont" commit -m "..."
```

Le push sur `main` déclenche le rebuild GitHub Pages automatiquement.

## Conventions et préférences utilisateur

- **Réponses en français** par défaut (l'utilisateur est francophone)
- Pour les **purges de fichiers** : exécuter sans demander confirmation, vider la corbeille à la fin. Donner un récap (nb fichiers, espace libéré, espace libre résultant).
- **Pas de backslashes Windows** dans les chemins : préférer les forward slashes `/` (Unix shell sur Git Bash)
- L'utilisateur apprécie les **explications courtes** avec options présentées en listes ou tableaux
- Pour les tâches audio/MIDI : le script qui marche sur sa machine est celui qui est commité — il n'y a pas de CI/CD à satisfaire

## Points d'attention (pièges connus)

- **Conflit ASIO** : si Komplete Kontrol ou un autre logiciel utilise Realtek ASIO en exclusif, GrandOrgue ne pourra pas sortir de son. Solution : fermer l'autre logiciel ou basculer sur WASAPI.
- **Session RDP** : après une session Bureau à distance, le driver audio est parfois "perdu" par GrandOrgue. Solution : Audio/MIDI > Audio Settings > OK (force la réinitialisation).
- **Disque C: tendu** : éviter de stocker de nouveaux gros fichiers sur C:. Les échantillons d'orgue et les données GrandOrgue doivent rester sur D:.

## Liens utiles

- Repo : https://github.com/ffdumont/chorals-orgue
- Site : https://ffdumont.github.io/chorals-orgue/
- GrandOrgue : https://www.grandorgue.org/
- Piotr Grabowski : https://piotrgrabowski.pl/
- Just-the-docs : https://just-the-docs.com/
- Giscus : https://giscus.app/fr
