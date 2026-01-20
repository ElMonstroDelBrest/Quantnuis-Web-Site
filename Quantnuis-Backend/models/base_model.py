#!/usr/bin/env python3
"""
================================================================================
                    CLASSE DE BASE POUR LES MODÈLES ML
================================================================================

Classe abstraite définissant l'interface commune pour tous les modèles.
Les modèles car_detector et noisy_car_detector héritent de cette classe.

================================================================================
"""

import os
import numpy as np
import joblib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, Optional, List, Dict

import tensorflow as tf

from config import get_settings
from shared import (
    print_header, print_success, print_info, 
    print_warning, print_error
)

settings = get_settings()


class BaseMLModel(ABC):
    """
    Classe de base pour les modèles de machine learning.
    
    Cette classe définit l'interface commune et implémente les fonctionnalités
    partagées entre tous les modèles (chargement, prédiction, etc.)
    
    Attributs:
        model: Le modèle TensorFlow/Keras chargé
        scaler: Le StandardScaler pour normaliser les données
        feature_names: Liste des features attendues par le modèle
        model_name: Nom du modèle (pour les logs)
    """
    
    def __init__(self, model_name: str):
        """
        Initialise le modèle de base.
        
        Paramètres:
            model_name (str): Nom du modèle pour identification
        """
        self.model_name = model_name
        self.model: Optional[tf.keras.Model] = None
        self.scaler = None
        self.feature_names: List[str] = []
        self._is_loaded = False
    
    # ==========================================================================
    # PROPRIÉTÉS ABSTRAITES (à implémenter dans les sous-classes)
    # ==========================================================================
    
    @property
    @abstractmethod
    def model_path(self) -> Path:
        """Chemin vers le fichier modèle (.h5)"""
        pass
    
    @property
    @abstractmethod
    def scaler_path(self) -> Path:
        """Chemin vers le scaler (.pkl)"""
        pass
    
    @property
    @abstractmethod
    def features_path(self) -> Path:
        """Chemin vers la liste des features (.txt)"""
        pass
    
    @property
    @abstractmethod
    def threshold(self) -> float:
        """Seuil de classification"""
        pass
    
    @property
    @abstractmethod
    def positive_label(self) -> str:
        """Label pour la classe positive"""
        pass
    
    @property
    @abstractmethod
    def negative_label(self) -> str:
        """Label pour la classe négative"""
        pass
    
    # ==========================================================================
    # MÉTHODES DE CHARGEMENT
    # ==========================================================================
    
    def load(self) -> bool:
        """
        Charge le modèle, le scaler et la liste des features.
        
        Retourne:
            bool: True si le chargement a réussi
        """
        if self._is_loaded:
            return True
        
        try:
            # Vérifier l'existence des fichiers
            if not self.model_path.exists():
                print_warning(f"[{self.model_name}] Modèle non trouvé: {self.model_path}")
                return False
            
            if not self.scaler_path.exists():
                print_warning(f"[{self.model_name}] Scaler non trouvé: {self.scaler_path}")
                return False
            
            if not self.features_path.exists():
                print_warning(f"[{self.model_name}] Features non trouvées: {self.features_path}")
                return False
            
            # Charger le modèle
            self.model = tf.keras.models.load_model(str(self.model_path))
            
            # Charger le scaler
            self.scaler = joblib.load(str(self.scaler_path))
            
            # Charger la liste des features
            with open(self.features_path, 'r') as f:
                self.feature_names = [line.strip() for line in f.readlines()]
            
            self._is_loaded = True
            print_success(f"[{self.model_name}] Modèle chargé avec succès")
            
            return True
            
        except Exception as e:
            print_error(f"[{self.model_name}] Erreur de chargement: {e}")
            return False
    
    def ensure_loaded(self) -> bool:
        """Assure que le modèle est chargé, le charge si nécessaire."""
        if not self._is_loaded:
            return self.load()
        return True
    
    # ==========================================================================
    # MÉTHODES DE PRÉDICTION
    # ==========================================================================
    
    def predict_features(self, features: Dict[str, float]) -> Tuple[str, float, float]:
        """
        Fait une prédiction à partir de features déjà extraites.
        
        Paramètres:
            features (dict): Dictionnaire {nom_feature: valeur}
        
        Retourne:
            tuple: (label, confiance_pourcentage, probabilité_brute)
        """
        if not self.ensure_loaded():
            raise RuntimeError(f"Impossible de charger le modèle {self.model_name}")
        
        # Construire le vecteur de features dans le bon ordre
        X = np.array([[features.get(name, 0.0) for name in self.feature_names]])
        
        # Standardiser
        X_scaled = self.scaler.transform(X)
        
        # Prédire
        prediction = self.model.predict(X_scaled, verbose=0)
        probability = float(prediction[0][0])
        
        # Interpréter le résultat
        if probability > self.threshold:
            label = self.positive_label
            confidence = probability * 100
        else:
            label = self.negative_label
            confidence = (1 - probability) * 100
        
        return label, confidence, probability
    
    @abstractmethod
    def predict_file(self, audio_path: str) -> Tuple[str, float, float]:
        """
        Fait une prédiction sur un fichier audio.
        
        À implémenter dans les sous-classes car chaque modèle peut avoir
        des features spécifiques à extraire.
        
        Paramètres:
            audio_path (str): Chemin vers le fichier audio
        
        Retourne:
            tuple: (label, confiance_pourcentage, probabilité_brute)
        """
        pass
    
    # ==========================================================================
    # MÉTHODES UTILITAIRES
    # ==========================================================================
    
    @property
    def is_loaded(self) -> bool:
        """Indique si le modèle est chargé."""
        return self._is_loaded
    
    @property
    def n_features(self) -> int:
        """Nombre de features attendues par le modèle."""
        return len(self.feature_names)
    
    def get_model_info(self) -> dict:
        """
        Retourne les informations sur le modèle.
        
        Retourne:
            dict: Informations du modèle
        """
        return {
            "name": self.model_name,
            "is_loaded": self._is_loaded,
            "n_features": self.n_features,
            "threshold": self.threshold,
            "positive_label": self.positive_label,
            "negative_label": self.negative_label,
            "model_path": str(self.model_path),
            "model_exists": self.model_path.exists()
        }
