# api/

Point d'entree de l'API REST FastAPI. Trois modules :

## Structure

```
api/
├── main.py              # Wrapper combinant EC2 + Lambda (dev local)
├── ec2_api/             # API stateful (auth, users, admin) -> deploye sur EC2
└── lambda_api/          # API stateless (predict IA) -> deploye sur Lambda
```

## Quel fichier utiliser ?

| Contexte | Entry point | Commande |
|---|---|---|
| **Dev local** | `api.main:app` | `uvicorn api.main:app --reload --port 8000` |
| **Prod EC2** | `api.ec2_api.main:app` | `uvicorn api.ec2_api.main:app --port 8000` |
| **Prod Lambda** | `api.lambda_api.main.handler` | Deploy via Docker/ECR |

## `main.py` - Wrapper dev local (137 lignes)

Monte tous les routers des deux APIs sur une seule app FastAPI.
Permet de tester auth + predict en local sans deployer deux services.

Exporte :
- `app` : instance FastAPI
- `handler` : handler Mangum (compatibilite Lambda)

## Endpoints combines (dev local)

Voir `ec2_api/README.md` et `lambda_api/README.md` pour le detail.
