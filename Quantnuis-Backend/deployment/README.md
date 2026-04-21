# deployment/

Fichiers de deploiement pour l'instance EC2.

## Structure

```
deployment/
└── ec2/
    ├── setup.sh                # Installation initiale de l'instance EC2
    ├── deploy.sh               # Script de deploiement (mise a jour)
    ├── .env.template           # Template des variables d'environnement
    ├── nginx.conf              # Configuration Nginx (reverse proxy)
    └── quantnuis-api.service   # Service systemd pour l'API
```

## Deploiement EC2

L'API EC2 tourne sur une instance t3.micro (eu-west-3) avec :
- Nginx en reverse proxy
- systemd pour gerer le service
- PostgreSQL pour la BDD

### Installation initiale

```bash
# Sur l'instance EC2
bash deployment/ec2/setup.sh
```

### Mise a jour

```bash
bash deployment/ec2/deploy.sh
```

### Configuration

Copier `.env.template` vers `.env` et remplir les variables :
- `SECRET_KEY` : cle JWT (generer avec `openssl rand -hex 32`)
- `DATABASE_URL` : URL PostgreSQL
- `GITHUB_TOKEN` : token pour push annotations
- `CORS_ORIGINS` : origines autorisees

## Deploiement Lambda

Le deploiement Lambda utilise les Dockerfiles a la racine :
- `Dockerfile.lambda` : Image Lambda avec TensorFlow (predict uniquement)
- `Dockerfile` : Image Lambda legacy (monolithe, a migrer)

Push vers ECR puis deploy Lambda via console AWS ou CLI.
