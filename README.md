# Chorals d'orgue

Site wiki dédié au répertoire d'orgue, avec un focus sur les chorals de Bach et les explorations pédagogiques autour de l'écriture à plusieurs voix.

**URL publique** : https://ffdumont.github.io/chorals-orgue/

## Structure

- `_config.yml` — configuration Jekyll
- `index.md` — page d'accueil
- `pieces/` — fiches des pièces et pages pédagogiques
- `assets/` — partitions (PDF, images), audio (MP3), illustrations
- `_layouts/default.html` — layout custom (ajoute Giscus)
- `_includes/giscus.html` — widget de commentaires

## Déploiement

Hébergé sur **GitHub Pages**. Tout push sur `main` déclenche un rebuild automatique.

## Commentaires

Alimentés par **Giscus** (système basé sur GitHub Discussions). Il faut :

1. Activer les **Discussions** dans les settings du repo
2. Installer l'app [Giscus](https://github.com/apps/giscus) sur le repo
3. Récupérer les IDs sur [giscus.app](https://giscus.app/fr) et les reporter dans `_config.yml`

## Développement local

```bash
bundle install
bundle exec jekyll serve
```

Ouvre alors http://localhost:4000/chorals-orgue/
