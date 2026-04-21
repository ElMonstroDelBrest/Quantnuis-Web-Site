#!/usr/bin/env python3
"""
================================================================================
                    SYNCHRONISATION GOOGLE DRIVE
================================================================================

Wrapper rclone pour synchroniser les datasets avec un remote (Google Drive).

Usage:
    # Voir les différences pour le dataset 'noisy_car' (dry-run par défaut)
    python -m scripts.gdrive_sync --model noisy_car --status

    # Télécharger le dataset 'car_detector' depuis le remote
    python -m scripts.gdrive_sync --model car --download --execute

    # Envoyer les changements locaux pour 'noisy_car' vers le remote
    python -m scripts.gdrive_sync --model noisy_car --upload --execute

    # Synchronisation bi-directionnelle
    python -m scripts.gdrive_sync --model noisy_car --sync --execute

================================================================================
"""

import argparse
import subprocess
import sys
import shutil
import time
from pathlib import Path

# Ajouter la racine du projet au path pour les imports absolus
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from config import get_settings
from shared import (
    print_header,
    print_success,
    print_info,
    print_warning,
    print_error,
)


def run_rclone_command(cmd: list):
    """Exécute une commande rclone et affiche sa sortie en temps réel."""
    print_info("Commande rclone :")
    cmd_str = ' '.join(f'"{c}"' if ' ' in c else c for c in cmd)
    print(f"  {cmd_str}\n")

    start_time = time.time()
    rc = 0

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )

        for line in iter(process.stdout.readline, ""):
            print(line, end="")

        process.stdout.close()
        rc = process.wait()

    except FileNotFoundError:
        print_error("La commande 'rclone' n'a pas été trouvée.")
        print_info("Installez-la : sudo pacman -S rclone")
        sys.exit(1)
    except Exception as e:
        print_error(f"Erreur pendant l'exécution de rclone: {e}")
        rc = -1

    duration = time.time() - start_time

    if rc == 0:
        print_success(f"Opération terminée en {duration:.2f}s.")
    else:
        print_warning(f"rclone a terminé avec le code {rc} en {duration:.2f}s.")


def main():
    """Point d'entrée en ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Wrapper rclone pour synchroniser les datasets Quantnuis.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--model", "-m",
        choices=["car", "noisy_car"],
        required=True,
        help="Modèle/dataset cible (car ou noisy_car).",
    )

    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "--status", action="store_true", help="Affiche les différences."
    )
    action_group.add_argument(
        "--upload", action="store_true", help="Copie local vers remote."
    )
    action_group.add_argument(
        "--download", action="store_true", help="Copie remote vers local.",
    )
    action_group.add_argument(
        "--sync", action="store_true", help="Synchronise bi-directionnellement (bisync)."
    )

    parser.add_argument(
        "--execute", action="store_true",
        help="Exécute réellement. Par défaut, dry-run.",
    )
    parser.add_argument(
        "--remote", default="Quantnuis", help="Nom du remote rclone (défaut: 'Quantnuis')."
    )
    parser.add_argument(
        "--remote-path", default="Quantnuis",
        help="Chemin de base sur le remote (défaut: 'Quantnuis').",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Sortie détaillée."
    )

    args = parser.parse_args()

    # Vérifier que rclone est installé
    if not shutil.which("rclone"):
        print_error("rclone n'est pas installé.")
        print_info("Installez-le : sudo pacman -S rclone")
        print_info("Puis configurez : rclone config")
        sys.exit(1)

    # Déterminer l'action
    if args.status:
        action = "status"
    elif args.upload:
        action = "upload"
    elif args.download:
        action = "download"
    elif args.sync:
        action = "sync"

    print_header(f"SYNC {args.model.upper()} - MODE {action.upper()}")

    if not args.execute and action != "status":
        print_warning("DRY-RUN activé. Aucune modification ne sera effectuée.")
        print_info("Utilisez --execute pour appliquer les changements.")

    # Construire les chemins
    settings = get_settings()
    model_map = {"car": "car_detector", "noisy_car": "noisy_car_detector"}
    model_name = model_map[args.model]

    local_path = settings.DATA_DIR / model_name
    if args.remote_path:
        remote_full_path = f"{args.remote}:{args.remote_path}/{model_name}"
    else:
        remote_full_path = f"{args.remote}:{model_name}"

    if not local_path.exists():
        print_warning(f"Le dossier local {local_path} n'existe pas.")
        local_path.mkdir(parents=True, exist_ok=True)

    print_info(f"Local  : {local_path}")
    print_info(f"Remote : {remote_full_path}")

    # Construire la commande rclone
    cmd = ["rclone"]

    if action == "status":
        cmd.extend(["check", str(local_path), remote_full_path])
    elif action == "upload":
        cmd.extend(["copy", str(local_path), remote_full_path])
    elif action == "download":
        cmd.extend(["copy", remote_full_path, str(local_path)])
    elif action == "sync":
        cmd.extend(["bisync", str(local_path), remote_full_path])

    # Filtres : ne sync que slices/ et annotation.csv
    cmd.extend([
        "--filter", "+ annotation.csv",
        "--filter", "+ slices/**",
        "--filter", "- *",
    ])

    if args.verbose:
        cmd.append("-v")

    cmd.append("-P")

    if not args.execute and action != "status":
        cmd.append("--dry-run")
        if action == "sync":
            cmd.append("--resync")

    # Exécuter
    run_rclone_command(cmd)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠ Annulé")
        sys.exit(1)
    except Exception as e:
        print_error(str(e))
        sys.exit(1)
