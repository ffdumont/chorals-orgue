# Mémoires Claude

Ce fichier est une **copie versionnée** des mémoires persistantes de Claude pour ce projet. Les originales sont dans la mémoire utilisateur locale (hors repo). Les copier ici permet qu'une future session Claude (y compris lancée depuis un autre dossier) retrouve le même contexte.

Chaque section correspond à une mémoire. Les metadonnées (nom, description, type) sont conservées.

---

## Profil utilisateur

*Type : user*

Rôle et centres d'intérêt de l'utilisateur — organiste, manipule des MIDI de répertoire classique/liturgique.

- **Organiste** — joue sur l'orgue de Saint-Jean-de-Luz (cf. mémoire GrandOrgue dédiée)
- Travaille régulièrement avec des fichiers **MIDI de répertoire** (chorals de Bach, pièces liturgiques)
- Usage typique : analyser, écouter, router des MIDI vers GrandOrgue ou un sampler
- Environnement : Windows 11, Native Instruments (Kontakt 8, Komplete Kontrol), loopMIDI pour routing
- Langue de travail : **français** — répondre en français par défaut
- Niveau technique : à l'aise avec des outils musicaux mais pas développeur — privilégier explications claires + commandes prêtes à copier

---

## Native Instruments setup

*Type : reference*

État de l'installation Native Instruments — chemins, apps installées, config audio, bibliothèques disponibles.

### Installation

- Racine : `D:\Native Instruments\`
  - `Application\Kontakt 8\`
  - `Application\Komplete Kontrol\`
  - `Content\` (vide à ce jour)
  - `Download\`

### Bibliothèques

- **Kontakt Factory Selection** installé mais une seule preset visible : **Piano Uno**
- Komplete Kontrol ne voit **aucun instrument** (scan/installation via Native Access nécessaire)
- Aucun fichier `.nki` / `.nkm` trouvé dans `D:\Native Instruments\` — seulement le preset par défaut de Kontakt (`C:\Users\franc\AppData\Local\Native Instruments\Kontakt 8\default\kontakt_def.nki`)

### Config audio Kontakt

- Driver : **ASIO**
- Device : **Realtek ASIO**
- Buffer : 1024 samples
- Latency totale : 21.3 ms

### Pas de DAW installé

- Pas de Maschine (non inclus dans cette install NI)
- Komplete Kontrol sert de mini-hôte mais nécessite bibliothèques scannées
- Pour lire un MIDI facilement → suggérer Reaper (gratuit/illimité) ou Python + synthé Windows pour écoute rapide

Le contexte musical (organiste, répertoire de choral) fait qu'on privilégie orgue > piano > cordes/chœur pour les suggestions de sons.

---

## loopMIDI Windows 11 fix

*Type : reference*

Sur Windows 11 (24H2 / 25H2 / 26H1), le nouveau stack MIDI 2.0 de Microsoft empêche les ports loopMIDI d'apparaître dans les apps (Komplete Kontrol, Kontakt, Python mido/rtmidi, WinMM) — même quand loopMIDI les affiche dans son UI et que le driver `teVirtualMIDI64` tourne.

**Fix** :

1. Lancer loopMIDI et créer le port
2. Redémarrer le service Windows MIDI :

   ```powershell
   Restart-Service -Name midisrv -Force
   ```

   (ou `services.msc` → "Service MIDI de Windows" → Redémarrer)
3. Relancer les apps MIDI (KK, Kontakt, scripts Python)

**Pourquoi** : les ports créés après le démarrage de `midisrv` ne sont pas énumérés correctement. Redémarrer `midisrv` force la ré-énumération.

**Quand l'appliquer** : dès qu'un utilisateur signale que loopMIDI ne marche pas / port invisible sur Windows 11, faire le restart de `midisrv` avant de suggérer des alternatives (Reaper, BOME, etc.).

Setup confirmé fonctionnel : Python mido → loopMIDI Port → Komplete Kontrol ou GrandOrgue.

---

## Cleanup sans confirmation

*Type : feedback*

Pour les opérations de nettoyage/suppression de fichiers (purge Downloads, Videos, cache, etc.), ne pas demander de confirmation et vider la corbeille à la fin.

**Pourquoi** : l'utilisateur est autonome sur ses choix de cleanup et préfère l'efficacité plutôt que des aller-retours de confirmation. La corbeille est vidée aussi pour obtenir l'espace libéré réel immédiatement.

**Comment l'appliquer** : quand l'utilisateur demande "purge X" ou "supprime Y", exécuter directement avec `Remove-Item -Force` puis `Clear-RecycleBin -Force`. Toujours donner un récap après (fichiers supprimés, espace libéré, espace libre résultant).

---

## GrandOrgue Saint-Jean-de-Luz — mapping MIDI

*Type : project*

Mapping MIDI CC pour les jeux et claviers de l'orgue Saint-Jean-de-Luz Choeur dans GrandOrgue. Workflow Python mido via loopMIDI Port 1.

- **Orgue** : Saint-Jean-de-Luz (Choeur) — Piotr Grabowski, format GrandOrgue
- **Emplacement** : `D:/OrganSamples/Saint-Jean-de-Luz (choeur).organ`
- **Data GrandOrgue** : `D:/GrandOrgue/` (Cache, Settings, Combinations, MIDI recordings, etc.)
- **Backup MIDI config** : `D:/GrandOrgue/Data/backup-midi-mapping.cmb`

### Claviers (Note On/Off)

- **Grand Orgue** → canal MIDI 2 (mido `channel=1`)
- **Pédale** → canal MIDI 1 (mido `channel=0`)
- **Récit** → non mappé (à faire si besoin)

### Jeux (Control Change sur canal MIDI 16 = mido `channel=15`, valeur 127 = toggle)

| CC | Jeu |
|---|---|
| 20 | GO Bourdon 16 |
| 21 | GO Flûte harmonique 8 |
| 22 | GO Bourdon 8 |
| 23 | GO Prestant 4 |
| 24 | GO Quinte 2 2/3 |
| 25 | GO Doublette 2 |
| 26 | GO Tierce 1 3/5 |
| 27 | REC Flûte 8 |
| 28 | REC Flûte 4 |
| 29 | REC Plein-jeu III |
| 30 | REC Trompette 8 |
| 31 | Tremblant |
| 40 | PED Soubasse 16 |
| 41 | PED Flûte 8 |
| 42 | PED Bourdon 8 |
| 43 | PED Flûte 4 |
| 44 | PED Flûte 2 |

**Pourquoi** : évite de refaire le MIDI-learn à chaque nouveau morceau. Les jeux se comportent en toggle (envoyer CC avec valeur 127 alterne ON/OFF).

**Comment l'utiliser** : voir [scripts/stops_control.py](../scripts/stops_control.py) pour le module Python, ou la [page Setup technique](../pieces/setup-technique.md) pour la version expliquée.
