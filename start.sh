#!/bin/bash

# Fonction pour tout arrêter proprement quand on fait CTRL+C
cleanup() {
  echo ""
  echo "🛑 Arrêt des services..."
  
  # Arrêt du Frontend
  if [ -n "$FRONTEND_PID" ]; then 
    kill $FRONTEND_PID
    echo "   - Frontend arrêté"
  fi
  
  # Arrêt du Backend (Docker)
  echo "   - Arrêt des conteneurs Docker..."
  (cd Quantnuis-Backend && docker-compose down)
  
  exit
}

# Intercepter la commande d'arrêt (CTRL+C)
trap cleanup SIGINT

echo "🚀 Lancement de Quantnuis (Hybride : Docker + Local)..."

# --- 1. Lancement du Backend (Docker) ---
echo "🐳 Démarrage du Backend via Docker..."
cd Quantnuis-Backend

# Vérifier si Docker est lancé
if ! docker info > /dev/null 2>&1; then
  echo "❌ Erreur : Docker n'est pas lancé ou accessible."
  exit 1
fi

# Lancement des conteneurs
docker-compose up -d --build

if [ $? -eq 0 ]; then
    echo "✅ Backend conteneurisé lancé sur le port 8000"
else
    echo "❌ Échec du lancement Docker"
    exit 1
fi

cd ..

# Petite pause pour laisser le temps au conteneur de s'initialiser
echo "⏳ Attente de l'initialisation de l'API..."
sleep 5

# --- 2. Lancement du Frontend (Local) ---
echo "🎨 Démarrage du Frontend (Local)..."
cd Quantnuis-Frontend

# Installation des dépendances si nécessaire (rapide si déjà fait)
if [ ! -d "node_modules" ]; then
    echo "📦 Installation des dépendances NPM..."
    npm install
fi

# Lancement de NPM en arrière-plan
npm start &
FRONTEND_PID=$!

cd ..
echo "✅ Frontend lancé (PID: $FRONTEND_PID)"

# --- 3. Informations ---
echo "------------------------------------------------"
echo "Architecture :"
echo "   🐳 Backend : http://localhost:8000 (Docker)"
echo "   💻 Frontend : http://localhost:4200 (Local)"
echo ""
echo "Documentation API : http://localhost:8000/docs"
echo "------------------------------------------------"
echo "Appuyez sur CTRL+C pour arrêter les services."

# Garder le script actif
wait
