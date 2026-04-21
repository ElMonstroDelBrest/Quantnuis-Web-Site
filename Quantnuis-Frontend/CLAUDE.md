# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Quantnuis Frontend - Interface web Angular pour le systeme de detection de vehicules bruyants.

Stack: Angular 21, TypeScript 5.9, Vitest, Vite, standalone components, dark theme.

## Architecture Cloud (Production)

```
┌─────────────────────────────────────────────────────────────┐
│  S3: projet-quantnuis-frontend                              │
│  - Frontend Angular (fichiers statiques)                    │
│  URL: http://projet-quantnuis-frontend.s3-website.eu-west-3.amazonaws.com │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  S3: quantnuis-audio-bucket                                 │
│  - Stockage des fichiers audio uploades par les utilisateurs│
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  EC2: quantnuis-api-ec2 (t3.micro, eu-west-3)              │
│  - Auth (login, register, JWT)                              │
│  - Admin (gestion users, annotation requests)               │
│  - Generation de spectrogrammes (annotation)                │
│  - S3 audio (presigned URLs, listing)                       │
│  - PostgreSQL                                               │
│  - Nginx reverse proxy → uvicorn (port 8000)                │
│  IP: 15.236.239.107 (PAS d'Elastic IP - a configurer)      │
│  DNS: ec2-15-236-239-107.eu-west-3.compute.amazonaws.com   │
│  HTTPS: pas encore configure (Certbot pret)                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Lambda: quantnuis-api (eu-west-3, ECR Docker)              │
│  - Modele IA brut uniquement (/predict)                     │
│  - Stateless, pay-per-use                                   │
│  - TensorFlow 2.15, pipeline CarDetector + NoisyCarDetector │
│  URL: https://fpzs67o2m7jc4bhljfi64xoxby0ygfwe.lambda-url.eu-west-3.on.aws │
└─────────────────────────────────────────────────────────────┘
```

### Routage des appels API (frontend)

| Service | Cible | Variable | Endpoints |
|---------|-------|----------|-----------|
| AuthService | EC2 | `apiUrl` | `/token`, `/register`, `/users/me`, `/stats`, `/history`, `/admin/*`, `/annotation-requests/*` |
| S3AudioService | EC2 | `apiUrl` | `/s3-audio/*` |
| AnnotationComponent | EC2 | `apiUrl` | `/annotation-requests`, `/integrate-annotations` |
| AudioAnalysisService | Lambda | `lambdaUrl` | `/predict` |

### S3 Buckets

- `projet-quantnuis-frontend` - Frontend statique (eu-west-3)
- `quantnuis-audio-bucket` - Fichiers audio utilisateurs (eu-west-3)
- `quantnuis-db-bucket` - Backup DB pour Lambda (eu-west-3)

## Common Commands

```bash
# Install dependencies
npm install

# Dev server (http://localhost:4200)
npm start

# Production build
npm run build -- --configuration=production

# Tests
npm test
```

## Environment Configuration

- `src/environments/environment.ts` - Dev (apiUrl + lambdaUrl → localhost:8000)
- `src/environments/environment.prod.ts` - Prod (apiUrl → EC2, lambdaUrl → Lambda)

## Key Files

### Pages (src/app/pages/)
- `home.component.ts` - Landing page + audio upload/analyse (1683 lignes)
- `dashboard.component.ts` - Stats utilisateur, historique
- `annotation.component.ts` - Editeur d'annotations audio avance (3191 lignes)
- `admin.component.ts` - Panel admin (review annotations, gestion users)
- `login.component.ts` / `register.component.ts` - Auth
- `about.component.ts`, `contact.component.ts`, `legal.component.ts`

### Components (src/app/components/)
- `spectrogram/` - Visualisation spectrale canvas
- `db-gauge/` - Jauge de decibels
- `live-audio/` - Waveform temps reel (WebAudio API)
- `toast/` - Notifications
- `confetti/` - Animation celebration
- `footer/`, `empty-state/`, `offline-banner/`

### Shared (src/app/shared/)
- `pipes/safe-html.pipe.ts` - Pipe SafeHtml reutilisable (DomSanitizer)

### Services (src/app/services/) — Architecture MVC

```
Vue (Components/Pages) → Controleur (Services) → Modele (API Layer)
```

**Regle stricte** : Les vues n'importent JAMAIS depuis `services/api/`. Elles passent toujours par un service controleur.

#### Modele — API Layer (services/api/) - 1 methode = 1 endpoint, interfaces typees
- `ec2.api.ts` - Classe abstraite base (apiUrl)
- `lambda.api.ts` - Classe abstraite base (lambdaUrl)
- `auth.api.ts` - POST /token, POST /register (extends Ec2Api) — `LoginResponse`
- `user.api.ts` - GET /users/me, /stats, /history (extends Ec2Api) — `UserProfile`, `UserStats`, `AnalysisHistoryEntry`
- `admin.api.ts` - GET/POST /admin/* (extends Ec2Api) — `AnnotationRequest`, `AdminUser`, `AdminStats`, `ReviewAction`
- `annotation-request.api.ts` - POST /annotation-requests, GET /my (extends Ec2Api) — `AnnotationRequestResponse`
- `s3-audio.api.ts` - GET /s3-audio/* (extends Ec2Api) — `S3AudioFile`, `S3AudioListResponse`, `S3PresignedUrlResponse`
- `audio-analysis.api.ts` - POST /predict (extends LambdaApi) — `AnalysisResult`

#### Controleur — Services metier (services/)
- `ec2/auth.service.ts` - State utilisateur, orchestration login/logout (utilise TokenStorage + AuthApi + UserApi)
- `dashboard.service.ts` - Facade pour dashboard (combine stats + history via UserApi)
- `admin.service.ts` - Facade pour panel admin (wraps AdminApi, re-exporte types)
- `audio-analysis.service.ts` - Facade pour analyse audio (wraps AudioAnalysisApi)
- `s3-audio.service.ts` - Facade pour fichiers S3 (wraps S3AudioApi)

#### Infra (services/)
- `token.storage.ts` - Source unique encode/decode/expire tokens (partage entre auth.service et auth.interceptor)
- `annotation-persistence.service.ts` - IndexedDB pour undo/redo annotations
- `notification.service.ts` - Systeme de toast notifications
- `offline.service.ts` - Detection offline (DestroyRef + takeUntilDestroyed)
- `sound.service.ts` - Sons UI (WebAudio API)
- `textgrid.service.ts` - Import/export Praat TextGrid

### Interceptors & Config
- `auth.interceptor.ts` - Ajoute Bearer token via TokenStorage (plus de duplication)
- `error.interceptor.ts` - Retry exponential backoff + gestion erreurs HTTP
- `global-error.handler.ts` - Capture erreurs globales
- `app.routes.ts` - Routes avec authGuard et adminGuard
- `app.config.ts` - Providers (router, http, animations, interceptors)

### PWA
- `public/sw.js` - Service Worker (network-first cache)
- `public/manifest.json` - PWA manifest (standalone, dark theme)

## CI/CD

- `.github/workflows/deploy-frontend.yml` - Build Angular → sync vers S3
- `.github/workflows/deploy-backend.yml` - Build Docker → ECR → update Lambda
- `.github/workflows/deploy-ec2.yml` - rsync vers EC2 → restart service

## Styling

- Pure CSS avec CSS Variables (pas de framework CSS)
- Dark theme (#0a0a1a), glassmorphism
- Font: Inter (Google Fonts)
- Responsive: breakpoints 1024px, 768px, 480px
- Couleurs: --accent (#6366f1 indigo), --success (#10b981), --danger (#ef4444)

## TODO / A ameliorer

- [ ] Attacher une Elastic IP a l'EC2 (IP change au reboot)
- [ ] Configurer HTTPS sur EC2 (Certbot + Nginx)
- [ ] Configurer CloudFront devant S3 frontend (HTTPS + CDN)
- [ ] Restreindre CORS en production (pas de wildcard *)
- [ ] Reduire le bundle size (809KB, budget 800KB)
