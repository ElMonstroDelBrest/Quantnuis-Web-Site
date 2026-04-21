# Audios de démonstration (salon)

Ce dossier contient les audios que les visiteurs peuvent choisir depuis la page d'accueil pour tester la démo sur place.

## Ajouter / modifier des audios

1. Déposer le fichier (WAV, MP3, M4A, ≤ 10 MB) dans ce dossier.
2. Éditer `manifest.json` : ajouter une entrée dans `audios[]` avec `id`, `file`, `label`, `description`, `icon`.
3. Rebuild et déployer le frontend (`npm run build -- --configuration=production`).

## Champs manifest

| Champ         | Obligatoire | Description                                                                |
|---------------|-------------|----------------------------------------------------------------------------|
| `id`          | oui         | Identifiant stable (utilisé par Angular `trackBy`)                         |
| `file`        | oui         | Nom du fichier dans ce dossier                                             |
| `label`       | oui         | Titre affiché sur la carte                                                 |
| `description` | oui         | Texte secondaire affiché sous le label                                     |
| `icon`        | non         | `car` \| `sport` \| `moto` \| `street` (déterminer l'icône affichée)       |

## Icônes

Les icônes sont des SVG inline dans `home-picker.component.ts` (pas de dépendance externe).

## Notes

- Les fichiers sont servis directement depuis le CDN (S3/CloudFront), pas d'appel à l'API Lambda/EC2 pour les lister.
- Pas besoin d'authentification pour accéder à ces audios — c'est voulu pour le salon.
