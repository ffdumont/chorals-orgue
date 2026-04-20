---
layout: default
title: Le projet
nav_order: 2
permalink: /projet/
---

# Orgue virtuel + IA

Ce wiki accompagne un projet personnel d'apprentissage de l'orgue en autodidacte, avec deux particularités : **l'instrument est virtuel** (GrandOrgue + banque Saint-Jean-de-Luz) et **l'étude s'appuie sur des outils d'analyse MIDI et d'IA** pour objectiver la progression.

## Contexte

- **Profil** : piano pendant l'enfance (~10 ans), reprise à 50 ans après une longue interruption. Culture musicale latente (lecture, tonalité, oreille), motricité à reconstruire.
- **Instrument** : clavier Native Instruments lesté, **pas de pédalier** pour l'instant, GrandOrgue configuré avec la banque Saint-Jean-de-Luz (Choeur) de Piotr Grabowski.
- **Objectif de fond** : jouer les chorals de Bach.
- **Modalité** : auto-apprentissage, sans professeur régulier.

## Cadrage réaliste

Reprise adulte après 40 ans d'interruption ≈ redémarrage technique depuis zéro, mais avec des acquis préservés (lecture deux clés, structure tonale, coordination bimanuelle de base). La plasticité motrice existe à 50 ans mais demande **régularité plutôt qu'intensité** : 20 min/jour > 2h le dimanche. C'est précisément là qu'un outil bien conçu peut avoir un impact élevé.

Sans pédalier, les chorals de Bach ne sont jouables que partiellement. Un pédalier MIDI (400–1500 €, ou DIY) devient pertinent à échéance de 8–12 mois, une fois la technique manuelle suffisamment développée pour en tirer parti. Le clavier lesté construit par ailleurs des réflexes de frappe qu'il faudra désapprendre sur un orgue réel à traction mécanique — à garder en tête sans en faire un blocage.

## Les cinq axes de développement

### 1. Capture et analyse MIDI — le socle

Tapper le flux MIDI entre clavier et GrandOrgue (loopMIDI, `mido`), aligner la performance sur la partition de référence par *Dynamic Time Warping*, en extraire des métriques objectives :

- taux de notes justes,
- dérive rythmique et régularité du débit (écart-type d'intervalle entre notes),
- recouvrement note-off / note-on (qualité du legato),
- longueur réelle des notes (articulation),
- synchronisation main/pied (à terme).

Sans cette couche de mesure, tout le reste reste qualitatif. Pour une reprise adulte, c'est aussi le **levier motivationnel principal** : voir les métriques progresser semaine après semaine entretient une pratique quotidienne sur deux ans.

### 2. Travail de l'indépendance des voix

Séparer les voix SATB d'un MIDI source, faire jouer par GrandOrgue trois voix, muter la quatrième et la jouer soi-même. Rotation des rôles (S muette, puis A, puis T, puis B) et ralentissement progressif vers le tempo cible. Sans pédalier, cet axe se décale d'autant — on reste sur du 2 à 3 voix *manualiter* dans un premier temps.

### 3. Registration assistée

Agent LLM qui, étant donné une pièce (époque, caractère, sample set chargé), propose une registration stylistiquement cohérente — Couperin ≠ Buxtehude ≠ Franck. Automatisation via *Program Change* et messages de tirage de jeux. N'améliore pas la technique, mais construit la culture musicale organistique (traditions française classique, nord-allemande, romantique).

### 4. Doigté et pédalier assistés

Génération de doigtés organistiques (substitutions, glissements, doigts muets) et de pédalier chiffré (talon/pointe, jambe gauche/droite). Problème d'optimisation sous contraintes : distance entre notes, confort de la main, continuité legato. Attaquable par règles + A\* ou par modèle. Axe le plus ambitieux et différenciant, mais aussi le plus coûteux à développer.

### 5. Session tutorée par IA

Couche englobante reliant tout le reste : déclaration d'un objectif → captation → analyse déterministe (JSON) → diagnostic pédagogique et exercice suivant proposés par Claude via API ou CLI. Outils déterministes pour la mesure, LLM pour l'interprétation et la décision pédagogique.

## Trajectoire proposée sur 6 mois

| Période | Briques techniques | Répertoire |
|---|---|---|
| Mois 1–2 | Capture MIDI + dashboard minimal (notes justes, régularité rythmique, progression hebdomadaire) | Exercices à 1 puis 2 voix, très courts. Gammes, petits préludes |
| Mois 3–4 | Analyse d'articulation (longueur réelle des notes, overlap) | Peeters *Ars Organi*, petits chorals à 2 voix, Kaller *Orgelschule* vol. 1 |
| Mois 5–6 | Couche coach via Claude : lecture des métriques, proposition de l'exercice suivant | Premier choral simple à 3 voix (2 mains + 1 voix pré-enregistrée) |
| Mois 8–12 | Intégration pédalier (si acquis) | Élargissement progressif au répertoire avec pédale |

**Ne pas viser les chorals de Bach tout de suite.** Ils restent l'objectif de fond, mais techniquement ils demandent une indépendance des mains de niveau intermédiaire-avancé. Répertoire de démarrage adapté à une reprise adulte : Peeters *Ars Organi* (explicitement conçu pour adultes), Dupré *79 Chorals*, les *Acht kleine Präludien und Fugen* BWV 553–560 (longtemps attribués à Bach), Pachelbel, versets de Couperin, chorals simples à 2 voix de l'*Orgelbüchlein*.

## Priorisation des briques techniques

1. **Axe 1 (capture/analyse)** en premier : socle indispensable et levier motivationnel principal.
2. **Axe 2 (indépendance des voix)** ensuite : rendement pédagogique élevé par heure de développement, même sans pédalier.
3. **Axe 3 (registration)** en parallèle : indépendant des autres, utile immédiatement, plus facile à développer.
4. **Axe 5 (session tutorée)** une fois que 1 et 2 produisent assez de données exploitables.
5. **Axe 4 (doigté/pédalier assistés)** en dernier : le plus ambitieux, à réserver quand le reste tourne.

## Un angle mort assumé

L'outil IA compense mal ce qui ne se mesure pas en MIDI : position du corps, frappe, mouvements de main, posture assise. Une ou deux **leçons ponctuelles de diagnostic** avec un organiste (pas un cours régulier — juste 1 à 2 séances, ou un œil extérieur sur des vidéos) corrigeraient en présentiel des défauts qu'on entretient mal seul pendant des mois. À envisager à un moment.

## En pratique sur ce site

Les pages [Pièces](/chorals-orgue/pieces/bwv639/) documentent les explorations concrètes — une partition, un enregistrement, une démarche pédagogique. La page [Setup technique](/chorals-orgue/setup/) détaille l'architecture logicielle (loopMIDI, scripts Python, captation WASAPI) qui rend tout ça possible.
