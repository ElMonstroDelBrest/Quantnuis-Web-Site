#!/usr/bin/env python3
"""
================================================================================
                    GESTIONNAIRE S3 POUR LES FICHIERS AUDIO
================================================================================

Gestion des fichiers audio stockes sur AWS S3 pour l'interface d'annotation.
Permet de lister, verifier et generer des URLs presignees pour les fichiers.

================================================================================
"""

from typing import List, Optional
import boto3
from botocore.exceptions import ClientError

from config import get_settings

settings = get_settings()


class S3AudioFile:
    """Represente un fichier audio stocke sur S3."""

    def __init__(self, key: str, size: int, last_modified, etag: str = None):
        self.key = key
        self.size = size
        self.last_modified = last_modified
        self.etag = etag

    @property
    def filename(self) -> str:
        """Retourne le nom du fichier sans le chemin."""
        return self.key.split('/')[-1]

    @property
    def size_formatted(self) -> str:
        """Retourne la taille formatee (Ko, Mo)."""
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        else:
            return f"{self.size / (1024 * 1024):.1f} MB"

    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour la serialisation JSON."""
        return {
            "key": self.key,
            "filename": self.filename,
            "size": self.size,
            "size_formatted": self.size_formatted,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None
        }


class S3AudioManager:
    """
    Gestionnaire pour les fichiers audio sur S3.

    Permet de:
    1. Lister les fichiers audio disponibles
    2. Generer des URLs presignees pour telecharger les fichiers
    3. Verifier l'existence d'un fichier

    Usage:
        manager = S3AudioManager()
        files = manager.list_audio_files()
        url = manager.get_presigned_url("audio/recording.wav")
    """

    AUDIO_EXTENSIONS = {'.wav', '.mp3', '.ogg', '.flac', '.m4a', '.mp4'}

    def __init__(self, bucket_name: str = None):
        """
        Initialise le gestionnaire S3 audio.

        Parametres:
            bucket_name: Nom du bucket S3 (defaut: settings.S3_AUDIO_BUCKET_NAME)
        """
        self.bucket_name = bucket_name or settings.S3_AUDIO_BUCKET_NAME
        self._client = None

    @property
    def client(self):
        """Client S3 (lazy loading)."""
        if self._client is None:
            from botocore.config import Config
            # Use eu-west-3 region with signature v4 for presigned URLs
            config = Config(
                region_name='eu-west-3',
                signature_version='s3v4',
                s3={'addressing_style': 'virtual'}
            )
            self._client = boto3.client(
                's3',
                region_name='eu-west-3',
                config=config
            )
        return self._client

    def _is_audio_file(self, key: str) -> bool:
        """Verifie si le fichier est un fichier audio."""
        return any(key.lower().endswith(ext) for ext in self.AUDIO_EXTENSIONS)

    def list_audio_files(
        self,
        prefix: str = "",
        max_files: int = 100
    ) -> List[S3AudioFile]:
        """
        Liste les fichiers audio dans le bucket S3.

        Parametres:
            prefix: Prefixe (dossier) pour filtrer les fichiers
            max_files: Nombre maximum de fichiers a retourner

        Retourne:
            Liste d'objets S3AudioFile
        """
        try:
            paginator = self.client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix,
                PaginationConfig={'MaxItems': max_files * 2}  # Extra pour filtrer
            )

            audio_files = []
            for page in page_iterator:
                if 'Contents' not in page:
                    continue

                for obj in page['Contents']:
                    key = obj['Key']

                    # Ignorer les dossiers et fichiers non-audio
                    if key.endswith('/') or not self._is_audio_file(key):
                        continue

                    audio_file = S3AudioFile(
                        key=key,
                        size=obj['Size'],
                        last_modified=obj['LastModified'],
                        etag=obj.get('ETag', '').strip('"')
                    )
                    audio_files.append(audio_file)

                    if len(audio_files) >= max_files:
                        break

                if len(audio_files) >= max_files:
                    break

            # Trier par date de modification (plus recent en premier)
            audio_files.sort(key=lambda x: x.last_modified or '', reverse=True)

            return audio_files

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                raise ValueError(f"Le bucket '{self.bucket_name}' n'existe pas")
            elif error_code == 'AccessDenied':
                raise PermissionError(f"Acces refuse au bucket '{self.bucket_name}'")
            else:
                raise RuntimeError(f"Erreur S3: {e}")

    def get_presigned_url(
        self,
        key: str,
        expiration: int = None
    ) -> str:
        """
        Genere une URL presignee pour telecharger un fichier.

        Parametres:
            key: Cle (chemin) du fichier dans S3
            expiration: Duree de validite en secondes (defaut: settings.S3_PRESIGNED_URL_EXPIRATION)

        Retourne:
            URL presignee
        """
        if expiration is None:
            expiration = settings.S3_PRESIGNED_URL_EXPIRATION

        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key
                },
                ExpiresIn=expiration
            )
            return url

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                raise FileNotFoundError(f"Le fichier '{key}' n'existe pas")
            else:
                raise RuntimeError(f"Erreur S3: {e}")

    def file_exists(self, key: str) -> bool:
        """
        Verifie si un fichier existe dans le bucket.

        Parametres:
            key: Cle (chemin) du fichier dans S3

        Retourne:
            True si le fichier existe, False sinon
        """
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise RuntimeError(f"Erreur S3: {e}")

    def get_file_metadata(self, key: str) -> Optional[S3AudioFile]:
        """
        Recupere les metadonnees d'un fichier.

        Parametres:
            key: Cle (chemin) du fichier dans S3

        Retourne:
            S3AudioFile ou None si le fichier n'existe pas
        """
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=key)
            return S3AudioFile(
                key=key,
                size=response['ContentLength'],
                last_modified=response['LastModified'],
                etag=response.get('ETag', '').strip('"')
            )
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            raise RuntimeError(f"Erreur S3: {e}")


# ==============================================================================
# INSTANCE GLOBALE
# ==============================================================================

s3_audio_manager = S3AudioManager()
