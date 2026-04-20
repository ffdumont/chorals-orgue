# Contexte projet — Chorals d'orgue

Ce fichier est destiné à Claude Code pour reprendre rapidement le contexte du projet. Il résume ce qu'est le projet, sa stack, les conventions, et les dépendances externes non évidentes.

## Vue d'ensemble

Site wiki en Jekyll hébergé sur **GitHub Pages** qui présente des pièces d'orgue avec :
- Partitions affichées inline (PNG générés depuis MIDI via MuseScore CLI)
- Vidéos YouTube (non-répertoriées) embarquées en iframe, montrant la console GrandOrgue (jeux tirés, touches qui bougent) + audio
- Pipeline Python qui automatise capture écran + audio, upload YouTube, et mise à jour des pages markdown
- Commentaires via Giscus (GitHub Discussions)

URL publique : https://ffdumont.github.io/chorals-orgue/
Repo : https://github.com/ffdumont/chorals-orgue
Chaîne YouTube dédiée : [Chorals d'orgue](https://www.youtube.com/channel/UCDuYey5ZKESuB-ZyJrJrvUg) (ID `UCDuYey5ZKESuB-ZyJrJrvUg`)

L'utilisateur est **@ffdumont** (François Dumont, francois.dumont1@gmail.com), organiste amateur non-développeur mais à l'aise avec Windows.

## Stack

- **Jekyll 4** avec `remote_theme: just-the-docs/just-the-docs`
- **Giscus** pour les commentaires (nécessite auth GitHub pour poster)
- **Python 3.10+** pour les scripts (pas d'environnement virtuel spécifique)
- Dépendances Python : `mido`, `python-rtmidi`, `soundcard`, `soundfile`, `numpy`, `pyyaml`, `google-api-python-client`, `google-auth-oauthlib`, `google-auth-httplib2`
- **ffmpeg** (`C:/Program Files/ffmpeg-7.0.2-essentials_build/bin/ffmpeg.exe`) : capture écran (gdigrab) + mux audio/vidéo
- **MuseScore 4** (`C:/Program Files/MuseScore 4/bin/MuseScore4.exe`) : génère les PNG de partitions depuis MIDI
- **gcloud** CLI installé pour gérer le projet GCP `chorals-orgue-yt` (auth `francois.dumont1@gmail.com`)

## Arborescence

```
chorals-orgue/
├── _config.yml             # Jekyll config + Giscus IDs
├── _includes/giscus.html   # Widget commentaires
├── _layouts/default.html   # Ajoute Giscus aux pages de contenu
├── index.md                # Accueil
├── journal.md              # Journal des ajouts/modifs
├── pieces/
│   ├── bwv639.md           # BWV 639 + démarche pédagogique + 4 exemples progressifs
│   └── setup-technique.md  # Doc technique (architecture, mappings MIDI)
├── assets/
│   ├── images/*.png        # Partitions rendues
│   ├── midi/*.mid          # Fichiers MIDI sources
│   └── video/              # MP4 de capture locale (GITIGNORÉ — YouTube est la source de vérité)
└── scripts/
    ├── stops_control.py        # Module : table CC_STOPS + classe Stops
    ├── play_midi.py            # CLI : joue un .mid sur loopMIDI
    ├── humanize.py             # Applique jitter + articulation à un .mid
    ├── demo_registration.py    # Démo avec registration dynamique
    ├── record_all.py           # LEGACY : ancien pipeline MP3 (plus utilisé)
    ├── record_video.py         # Module + CLI : capture écran 2 + audio loopback → MP4
    ├── record_all_videos.py    # Pipeline : capture les 5 pistes BWV 639 en MP4
    ├── youtube_auth.py         # OAuth 2.0 pour l'API YouTube Data v3
    ├── upload_youtube.py       # Upload MP4 en non-répertorié, alimente video_ids.yml
    ├── update_embeds.py        # Remplace <audio> par iframes YouTube dans les .md
    ├── video_ids.yml           # Mapping clé → ID YouTube (VERSIONNÉ)
    ├── client_secret.json      # OAuth client (GITIGNORÉ)
    └── token.json              # Refresh token OAuth (GITIGNORÉ)
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

### Google Cloud / YouTube Data API

- Projet GCP : `chorals-orgue-yt` (créé via `gcloud projects create`)
- API activée : `youtube.googleapis.com`
- OAuth consent : app en mode **External + Testing**, user `francois.dumont1@gmail.com` ajouté comme test user
- OAuth client type **Desktop app**, credentials téléchargés dans `scripts/client_secret.json`
- Scope utilisé : `https://www.googleapis.com/auth/youtube` (upload + delete + manage)
- Quota : 10 000 units/jour (un upload = 1600 units, largement suffisant)
- Premier login : `python youtube_auth.py` ouvre le navigateur. Choisir **la chaîne "Chorals d'orgue"** (pas le compte personnel) dans le sélecteur. Warning "app non vérifiée" normal : Advanced → Go to ... (unsafe).

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

## Écrans

- Écran 1 (primary) = 1920×1080 à l'offset (0, 0) — console Claude / navigateur
- **Écran 2** = 1920×1080 à l'offset (1920, 1) — **GrandOrgue doit rester visible et non-recouvert pendant la capture vidéo**

Les coordonnées sont codées en dur dans `record_video.py` (constantes `SCREEN_OFFSET_X`, etc.). Si le setup change, éditer ce fichier.

## Workflows typiques

### Jouer un MIDI via GrandOrgue

```bash
cd scripts
python play_midi.py ../assets/midi/exemple4.mid --stops fonde
```

Prérequis : GrandOrgue ouvert avec l'orgue chargé, loopMIDI tournant, port visible (voir bug Win11 ci-dessus).

### Regénérer toutes les vidéos des exemples BWV 639

```bash
cd scripts
python record_all_videos.py                          # les 5 pistes
python record_all_videos.py exemple4 bwv639          # ou seulement celles-ci
```

Durée ~5-6 min pour les 5. Résultat dans `assets/video/` (gitignoré). Prérequis : GrandOrgue sur écran 2 non-recouvert, loopMIDI ok, silence total. Le script inclut un **warmup GrandOrgue** pour éviter que le premier chord tombe avant que le moteur audio soit actif.

### Uploader une vidéo sur YouTube

```bash
cd scripts
python upload_youtube.py \
  --file ../assets/video/exemple4.mp4 \
  --key exemple4 \
  --title "BWV 639 — Exemple 4 : la basse pizzicato" \
  --description "..." \
  --tags "orgue,Bach,BWV 639"
```

Privacy par défaut = `unlisted`. Le mapping est écrit dans `scripts/video_ids.yml`. Si la clé existe déjà, l'ancien ID est noté dans la sortie (à supprimer manuellement via API ou YouTube Studio).

### Mettre à jour les pages markdown avec les iframes YouTube

```bash
cd scripts
python update_embeds.py --dry-run     # preview
python update_embeds.py               # applique
```

Cherche les `<audio>` référençant `/assets/audio/<key>.mp3` et les remplace par une iframe YouTube (aspect ratio 16:9 responsive) pointant vers l'ID correspondant dans `video_ids.yml`. Idempotent pour les `<audio>` non encore remplacés. Pour remplacer une iframe existante par un nouvel ID (re-capture), éditer la page markdown à la main.

### Ajouter une nouvelle pièce

1. Placer le fichier MIDI dans `assets/midi/`
2. Générer la partition PNG : `"C:/Program Files/MuseScore 4/bin/MuseScore4.exe" fichier.mid -o fichier.png -T 10` (crée `fichier-1.png` pour la page 1). L'option `-T 10` recadre automatiquement l'image au contenu musical avec une marge de 10px — sans elle, MuseScore exporte la page A4 complète et laisse beaucoup de blanc sous la musique dans le wiki.
3. Ajouter la page Markdown dans `pieces/` avec un bloc `<audio controls><source src="/chorals-orgue/assets/audio/<key>.mp3">...</audio>` + `![partition]()`. Le bloc `<audio>` est un placeholder qui sera remplacé par l'iframe à l'étape suivante.
4. Capturer la vidéo : adapter `record_all_videos.py` (ajouter une fonction `play_<key>()` + une ligne dans la liste `examples`) puis `python record_all_videos.py <key>`.
5. Uploader : `python upload_youtube.py --file ../assets/video/<key>.mp4 --key <key> --title "..." --description "..."`.
6. Remplacer les `<audio>` par des iframes : `python update_embeds.py`.
7. Commit + push → GitHub Pages rebuild automatique (~1-2 min).

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
- **Cold start audio GrandOrgue** : le tout premier chord après ouverture peut tomber avant que le moteur audio soit actif. `record_all_videos.py` inclut un warmup (C4 bref sur Flûte 8) pour éviter une capture muette.
- **Iframe YouTube en `file://`** : un embed YouTube ouvert via `file:///...` peut échouer avec "Erreur 153" (Referer manquant). Pour tester en local, servir via `python -m http.server`.
- **OAuth scope** : si un script YouTube échoue avec `insufficient authentication scopes`, c'est que `scripts/token.json` a été obtenu avec un scope trop étroit. Supprimer `token.json` et relancer `python youtube_auth.py` pour reauthoriser avec le scope complet (`youtube`).

## Liens utiles

- Repo : https://github.com/ffdumont/chorals-orgue
- Site : https://ffdumont.github.io/chorals-orgue/
- Chaîne YouTube : https://www.youtube.com/channel/UCDuYey5ZKESuB-ZyJrJrvUg
- Console GCP du projet : https://console.cloud.google.com/home/dashboard?project=chorals-orgue-yt
- GrandOrgue : https://www.grandorgue.org/
- Piotr Grabowski : https://piotrgrabowski.pl/
- Just-the-docs : https://just-the-docs.com/
- Giscus : https://giscus.app/fr
