# Quantnuis

Plateforme de détection de véhicules bruyants par analyse audio, développée dans un cadre universitaire (ENSTA Bretagne · Campus de Brest).

Pipeline IA en cascade : détection de véhicule → analyse du niveau sonore.

---

## Sous-projets

| Dossier | Description |
|---------|-------------|
| [`Quantnuis-Backend/`](Quantnuis-Backend/README.md) | API FastAPI + modèles TensorFlow, déployés sur AWS Lambda et EC2 |
| [`Quantnuis-Frontend/`](Quantnuis-Frontend/README.md) | Interface Angular, déployée sur S3/CloudFront |

---

## Démarrage rapide

```bash
# Backend
cd Quantnuis-Backend
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000

# Frontend (autre terminal)
cd Quantnuis-Frontend
npm install && npm start
```

---

## Contact

george-daniel.gherasim@ensta.fr — [GitHub](https://github.com/ElMonstroDelBrest/Quantnuis-Web-Site)
