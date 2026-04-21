# Quantnuis — Frontend

Interface web Angular pour le système de détection de véhicules bruyants.

**Stack :** Angular 21, TypeScript 5.9, Vitest, Vite, standalone components

---

## Démarrage

```bash
npm install
npm start        # http://localhost:4200
```

Build production :

```bash
npm run build -- --configuration=production
# Artefacts dans dist/
```

Tests :

```bash
npm test
```

---

## Architecture cloud

| Service | Rôle | URL |
|---------|------|-----|
| S3 + CloudFront | Frontend statique | https://d3g1by0ab5tbz.cloudfront.net |
| EC2 (eu-west-3) | Auth, données, annotations | http://15.236.239.107:8000 |
| Lambda (eu-west-3) | Analyse IA `/predict` | https://fpzs67o2m7jc4bhljfi64xoxby0ygfwe.lambda-url.eu-west-3.on.aws |

Environnements : `src/environments/environment.ts` (dev) et `environment.prod.ts` (prod).

---

## Structure

```
src/app/
├── pages/          # Vues principales (home, dashboard, annotation, admin, legal...)
├── components/     # Composants réutilisables (footer, toast, spectrogram...)
├── services/       # Logique métier et couche API
│   ├── api/        # 1 fichier = 1 endpoint (auth, user, audio-analysis...)
│   └── ec2/        # Services métier (auth, dashboard, admin...)
├── shared/         # Pipes partagés
└── app.routes.ts   # Routing avec authGuard et adminGuard
```

**Règle architecture :** les pages n'importent jamais depuis `services/api/` directement — elles passent toujours par un service métier.

---

## CI/CD

`.github/workflows/deploy-frontend.yml` — build Angular puis sync S3 au push sur `main`.
