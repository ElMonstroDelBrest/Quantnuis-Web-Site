#!/usr/bin/env python3
"""
================================================================================
                    GESTIONNAIRE S3 POUR LA BASE DE DONNÉES
================================================================================

Gestion de la persistance de la base SQLite sur AWS S3.
Utilisé uniquement en environnement Lambda.

================================================================================
"""

import os
import boto3
from botocore.exceptions import ClientError

from config import get_settings
from shared.logger import print_info, print_success, print_warning, print_error

settings = get_settings()


class S3DatabaseManager:
    """
    Gestionnaire pour synchroniser la base SQLite avec S3.
    
    Sur AWS Lambda, le système de fichiers est en lecture seule
    (sauf /tmp). Cette classe permet de :
    1. Télécharger la BDD depuis S3 au démarrage
    2. Uploader la BDD vers S3 après les modifications
    
    Usage:
        manager = S3DatabaseManager()
        manager.download()  # Au démarrage
        # ... opérations sur la BDD ...
        manager.upload()    # Après modifications
    """
    
    def __init__(self, bucket_name: str = None, db_filename: str = "quantnuis.db"):
        """
        Initialise le gestionnaire S3.
        
        Paramètres:
            bucket_name: Nom du bucket S3 (défaut: settings.S3_BUCKET_NAME)
            db_filename: Nom du fichier de base de données
        """
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME
        self.db_filename = db_filename
        self.local_path = f"/tmp/{db_filename}"
        
        self._client = None
    
    @property
    def client(self):
        """Client S3 (lazy loading)."""
        if self._client is None:
            self._client = boto3.client('s3')
        return self._client
    
    @property
    def is_lambda(self) -> bool:
        """Vérifie si on est sur AWS Lambda."""
        return settings.IS_LAMBDA
    
    def download(self) -> bool:
        """
        Télécharge la base de données depuis S3.
        
        Retourne:
            bool: True si le téléchargement a réussi ou si pas nécessaire
        """
        if not self.is_lambda:
            return True  # Pas nécessaire en local
        
        try:
            print_info(f"Téléchargement de {self.db_filename} depuis S3...")
            self.client.download_file(
                self.bucket_name, 
                self.db_filename, 
                self.local_path
            )
            print_success("Base de données téléchargée")
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                print_info("Aucune BDD existante sur S3, création d'une nouvelle")
                return True  # Première exécution, pas d'erreur
            else:
                print_error(f"Erreur de téléchargement S3: {e}")
                return False
                
        except Exception as e:
            print_error(f"Erreur inattendue: {e}")
            return False
    
    def upload(self) -> bool:
        """
        Upload la base de données vers S3.
        
        Retourne:
            bool: True si l'upload a réussi ou si pas nécessaire
        """
        if not self.is_lambda:
            return True  # Pas nécessaire en local
        
        try:
            if not os.path.exists(self.local_path):
                print_warning("Pas de BDD locale à uploader")
                return False
            
            print_info(f"Upload de la BDD vers {self.bucket_name}...")
            self.client.upload_file(
                self.local_path, 
                self.bucket_name, 
                self.db_filename
            )
            print_success("Base de données sauvegardée sur S3")
            return True
            
        except Exception as e:
            print_error(f"Erreur d'upload S3: {e}")
            return False
    
    def sync_after_write(self):
        """
        Synchronise avec S3 après une écriture.
        
        À appeler après chaque modification de la BDD en environnement Lambda.
        """
        if self.is_lambda:
            self.upload()
    
    def ensure_downloaded(self):
        """
        S'assure que la BDD est téléchargée avant utilisation.
        
        À appeler au démarrage de l'application Lambda.
        """
        if self.is_lambda:
            return self.download()
        return True


# ==============================================================================
# INSTANCE GLOBALE
# ==============================================================================

s3_db_manager = S3DatabaseManager()


# ==============================================================================
# FONCTIONS UTILITAIRES (compatibilité avec l'ancien code)
# ==============================================================================

def download_db() -> bool:
    """Télécharge la BDD depuis S3."""
    return s3_db_manager.download()


def upload_db() -> bool:
    """Upload la BDD vers S3."""
    return s3_db_manager.upload()
