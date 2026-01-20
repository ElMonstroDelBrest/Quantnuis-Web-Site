#!/usr/bin/env python3
"""
================================================================================
                    GESTIONNAIRE DE SLICES AUDIO
================================================================================

Gestion des slices audio pour les deux modèles.

Structure des données :
    data/
    ├── car_detector/
    │   ├── slices/          # Audio pour détection voiture
    │   └── annotation.csv   # Annotations (nfile, label)
    └── noisy_car_detector/
        ├── slices/          # Audio avec voiture détectée
        └── annotation.csv   # Annotations (nfile, label: 0=normal, 1=bruyant)

Usage:
    python -m data_management.slice_manager --model car          # Modèle 1
    python -m data_management.slice_manager --model noisy_car    # Modèle 2

================================================================================
"""

import os
import sys
import shutil
from pathlib import Path
import pandas as pd

from config import get_settings
from shared import print_header, print_success, print_info, print_warning, print_error

settings = get_settings()


class SliceManager:
    """
    Gestionnaire de slices audio pour un modèle spécifique.
    
    Gère :
    - L'ajout de slices depuis un dossier externe
    - Le statut de la base de données
    - La cohérence entre fichiers et annotations
    
    Usage:
        manager = SliceManager("car_detector")
        manager.show_status()
        manager.add_slices("/path/to/audio/folder")
    """
    
    def __init__(self, model_name: str):
        """
        Initialise le gestionnaire pour un modèle.
        
        Paramètres:
            model_name: "car_detector" ou "noisy_car_detector"
        """
        self.model_name = model_name
        
        if model_name == "car_detector":
            from models.car_detector import config
            self.config = config
        elif model_name == "noisy_car_detector":
            from models.noisy_car_detector import config
            self.config = config
        else:
            raise ValueError(f"Modèle inconnu: {model_name}")
        
        self.slices_dir = self.config.SLICES_DIR
        self.annotation_csv = self.config.ANNOTATION_CSV
    
    def show_status(self):
        """Affiche le statut de la base de données."""
        print_header(f"Statut - {self.model_name}")
        
        # Vérifier les slices
        if self.slices_dir.exists():
            files = list(self.slices_dir.glob("*.wav"))
            print_info(f"📁 Slices: {len(files)} fichiers audio")
        else:
            print_warning(f"📁 Slices: dossier inexistant")
            print_info(f"   Chemin: {self.slices_dir}")
            return
        
        # Vérifier les annotations
        if self.annotation_csv.exists():
            df = pd.read_csv(self.annotation_csv)
            print_info(f"📄 Annotations: {len(df)} entrées")
            
            # Distribution des labels
            if 'label' in df.columns:
                print_header("Distribution")
                for label in sorted(df['label'].unique()):
                    count = (df['label'] == label).sum()
                    pct = count / len(df) * 100
                    print_info(f"Label {label}: {count} ({pct:.1f}%)")
            
            # Cohérence
            annotated = set(df['nfile'].values)
            on_disk = set(f.name for f in files)
            
            missing_files = annotated - on_disk
            missing_annotations = on_disk - annotated
            
            if missing_files:
                print_warning(f"{len(missing_files)} fichiers annotés manquants")
            if missing_annotations:
                print_warning(f"{len(missing_annotations)} fichiers non annotés")
            
            if not missing_files and not missing_annotations:
                print_success("Base de données cohérente")
        else:
            print_warning(f"📄 Annotations: fichier inexistant")
            print_info(f"   Chemin: {self.annotation_csv}")
    
    def add_slices(self, source_dir: str, default_label: int = None):
        """
        Ajoute des slices depuis un dossier externe.
        
        Paramètres:
            source_dir: Chemin vers le dossier contenant les .wav
            default_label: Label par défaut (optionnel, sinon demandé)
        """
        source_path = Path(source_dir)
        
        if not source_path.exists():
            print_error(f"Dossier non trouvé: {source_dir}")
            return
        
        # Créer les dossiers si nécessaire
        self.slices_dir.mkdir(parents=True, exist_ok=True)
        self.config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Trouver le prochain numéro
        existing = list(self.slices_dir.glob("slice_*.wav"))
        if existing:
            nums = [int(f.stem.replace('slice_', '')) for f in existing]
            next_num = max(nums) + 1
        else:
            next_num = 1
        
        # Lister les fichiers à ajouter
        files = list(source_path.glob("*.wav"))
        if not files:
            print_warning("Aucun fichier .wav trouvé")
            return
        
        print_info(f"📥 {len(files)} fichiers à ajouter...")
        
        # Demander le label si non fourni
        if default_label is None:
            print_info("Labels disponibles:")
            if self.model_name == "car_detector":
                print_info("  0 = Pas de voiture")
                print_info("  1 = Voiture")
            else:
                print_info("  0 = Normal")
                print_info("  1 = Bruyant")
            
            label_input = input("Label pour ces fichiers: ").strip()
            default_label = int(label_input)
        
        # Copier les fichiers
        added = 0
        new_rows = []
        
        for f in sorted(files):
            new_name = f"slice_{next_num:03d}.wav"
            dst = self.slices_dir / new_name
            
            shutil.copy2(f, dst)
            
            new_rows.append({
                'nfile': new_name,
                'label': default_label,
                'reliability': 3  # Fiabilité par défaut
            })
            
            print_info(f"  ✓ {f.name} → {new_name}")
            next_num += 1
            added += 1
        
        # Mettre à jour les annotations
        df_new = pd.DataFrame(new_rows)
        
        if self.annotation_csv.exists():
            df_existing = pd.read_csv(self.annotation_csv)
            df_final = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df_final = df_new
        
        df_final = df_final.drop_duplicates(subset=['nfile'])
        df_final.to_csv(self.annotation_csv, index=False)
        
        print_success(f"{added} fichiers ajoutés")
        print_info(f"Annotations mises à jour: {self.annotation_csv}")
    
    def remove_orphans(self):
        """Supprime les fichiers non annotés et les annotations sans fichier."""
        if not self.annotation_csv.exists():
            print_warning("Pas de fichier d'annotations")
            return
        
        df = pd.read_csv(self.annotation_csv)
        files = set(f.name for f in self.slices_dir.glob("*.wav"))
        annotated = set(df['nfile'].values)
        
        # Fichiers sans annotation
        missing_annotations = files - annotated
        for f in missing_annotations:
            path = self.slices_dir / f
            path.unlink()
            print_info(f"Supprimé: {f}")
        
        # Annotations sans fichier
        df_clean = df[df['nfile'].isin(files)]
        df_clean.to_csv(self.annotation_csv, index=False)
        
        removed = len(df) - len(df_clean)
        if removed > 0:
            print_info(f"{removed} annotations orphelines supprimées")
        
        print_success("Nettoyage terminé")


# ==============================================================================
# POINT D'ENTRÉE CLI
# ==============================================================================

def main():
    """Point d'entrée en ligne de commande."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Gestionnaire de slices audio")
    parser.add_argument(
        "--model", "-m",
        choices=["car", "noisy_car"],
        required=True,
        help="Modèle cible (car ou noisy_car)"
    )
    parser.add_argument(
        "--action", "-a",
        choices=["status", "add", "clean"],
        default="status",
        help="Action à effectuer"
    )
    parser.add_argument(
        "--source", "-s",
        help="Dossier source pour l'action 'add'"
    )
    parser.add_argument(
        "--label", "-l",
        type=int,
        help="Label par défaut pour l'action 'add'"
    )
    
    args = parser.parse_args()
    
    # Mapper les noms courts vers les noms complets
    model_map = {
        "car": "car_detector",
        "noisy_car": "noisy_car_detector"
    }
    model_name = model_map[args.model]
    
    manager = SliceManager(model_name)
    
    if args.action == "status":
        manager.show_status()
    elif args.action == "add":
        if not args.source:
            args.source = input("Dossier source: ").strip()
        manager.add_slices(args.source, args.label)
    elif args.action == "clean":
        manager.remove_orphans()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠ Annulé")
    except Exception as e:
        print_error(str(e))
        raise
