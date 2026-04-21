#!/usr/bin/env python3
"""
================================================================================
                    QUANTNUIS CLI
================================================================================

Interface en ligne de commande interactive pour gérer tout le projet Quantnuis.

Usage:
    python quantnuis_cli.py

================================================================================
"""

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared.colors import Colors
from shared.logger import print_header, print_success, print_info, print_warning, print_error


# =============================================================================
# HELPERS
# =============================================================================

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def pause():
    print(f"\n{Colors.DIM}Appuyez sur Entrée pour continuer...{Colors.END}")
    input()


def ask(prompt, default=None):
    """Prompt coloré avec valeur par défaut optionnelle."""
    suffix = f" [{default}]" if default else ""
    try:
        response = input(f"{Colors.CYAN}{prompt}{suffix}{Colors.END}: ").strip()
        return response if response else default
    except (KeyboardInterrupt, EOFError):
        print()
        return None


def ask_model():
    """Demande le modèle cible. Retourne 'car' ou 'noisy_car'."""
    print(f"  {Colors.CYAN}[1]{Colors.END} noisy_car_detector")
    print(f"  {Colors.CYAN}[2]{Colors.END} car_detector")
    choice = ask("Modèle", "1")
    if choice == '1':
        return 'noisy_car'
    elif choice == '2':
        return 'car'
    return None


def model_full_name(short):
    """Convertit 'car' → 'car_detector', 'noisy_car' → 'noisy_car_detector'."""
    return {'car': 'car_detector', 'noisy_car': 'noisy_car_detector'}.get(short, short)


def run_cmd(cmd_list):
    """Exécute une commande subprocess."""
    cmd_str = ' '.join(cmd_list)
    print(f"\n{Colors.DIM}$ {cmd_str}{Colors.END}\n")
    try:
        subprocess.run(cmd_list, check=False)
    except FileNotFoundError:
        print_error(f"Commande non trouvée: '{cmd_list[0]}'")
    except KeyboardInterrupt:
        print_warning("\nInterrompu.")
    except Exception as e:
        print_error(str(e))


def get_dataset_stats():
    """Compte les slices par modèle."""
    base = Path(__file__).resolve().parent / 'data'
    stats = {}
    for model in ['car_detector', 'noisy_car_detector']:
        d = base / model / 'slices'
        stats[model] = len(list(d.glob('*.wav'))) if d.exists() else 0
    return stats


def print_menu_item(num, label, destructive=False):
    """Affiche un item de menu."""
    if destructive:
        print(f"  {Colors.CYAN}[{num}]{Colors.END} {Colors.RED}{label}{Colors.END}")
    else:
        print(f"  {Colors.CYAN}[{num}]{Colors.END} {label}")


def show_banner():
    """Affiche le banner Quantnuis style Gemini CLI (half-block pixel art + gradient)."""
    FONT = {
        'Q': ['01110','10001','10001','10001','10101','10010','01110','00010'],
        'U': ['10001','10001','10001','10001','10001','10001','01110','00000'],
        'A': ['00100','01010','10001','10001','11111','10001','10001','00000'],
        'N': ['10001','11001','11001','10101','10011','10011','10001','00000'],
        'T': ['11111','00100','00100','00100','00100','00100','00100','00000'],
        'I': ['11111','00100','00100','00100','00100','00100','11111','00000'],
        'S': ['01110','10001','10000','01110','00001','10001','01110','00000'],
    }
    word = 'QUANTNUIS'
    rows = 8
    combined = ['' for _ in range(rows)]
    for ch in word:
        for r in range(rows):
            combined[r] += FONT[ch][r] + '0'

    # Gradient: blue → purple → magenta → pink
    grad = [
        '\033[38;5;33m', '\033[38;5;39m', '\033[38;5;63m',
        '\033[38;5;99m', '\033[38;5;135m', '\033[38;5;141m',
        '\033[38;5;169m', '\033[38;5;205m', '\033[38;5;210m',
    ]

    width = len(combined[0])
    print()
    for r in range(0, rows, 2):
        line = '  '
        for c in range(width):
            top = combined[r][c] == '1'
            bot = combined[r + 1][c] == '1' if r + 1 < rows else False
            color = grad[min(c // 6, len(grad) - 1)]
            if top and bot:
                line += color + '█'
            elif top:
                line += color + '▀'
            elif bot:
                line += color + '▄'
            else:
                line += ' '
        print(line + '\033[0m')

    print(f"\n{Colors.DIM}          Noisy Vehicle Detection System{Colors.END}")


# =============================================================================
# SOUS-MENUS
# =============================================================================

def menu_dataset():
    while True:
        try:
            clear_screen()
            print_header("Menu > Dataset")
            print_menu_item(1, "Status noisy_car_detector")
            print_menu_item(2, "Status car_detector")
            print_menu_item(3, "Ajouter des slices")
            print_menu_item(4, "Nettoyer les orphelins")
            print_menu_item(5, "Découper un audio long (CSV)")
            print(f"  {Colors.YELLOW}─────────────────────────────{Colors.END}")
            print_menu_item(0, "Retour")

            choice = ask("\nChoix")
            if choice == '1':
                run_cmd(['python', '-m', 'data_management.slice_manager', '-m', 'noisy_car', '-a', 'status'])
                pause()
            elif choice == '2':
                run_cmd(['python', '-m', 'data_management.slice_manager', '-m', 'car', '-a', 'status'])
                pause()
            elif choice == '3':
                model = ask_model()
                if not model: continue
                source = ask("Dossier source (.wav)")
                if not source: continue
                label = ask("Label (0=négatif, 1=positif)")
                if label not in ('0', '1'):
                    print_warning("Label invalide"); pause(); continue
                run_cmd(['python', '-m', 'data_management.slice_manager', '-m', model, '-a', 'add', '-s', source, '-l', label])
                pause()
            elif choice == '4':
                model = ask_model()
                if not model: continue
                run_cmd(['python', '-m', 'data_management.slice_manager', '-m', model, '-a', 'clean'])
                pause()
            elif choice == '5':
                model = ask_model()
                if not model: continue
                audio = ask("Fichier audio")
                if not audio: continue
                csv = ask("Fichier CSV d'annotations")
                if not csv: continue
                run_cmd(['python', '-m', 'data_management.slicing', '-m', model, audio, csv])
                pause()
            elif choice == '0' or choice is None:
                break
        except KeyboardInterrupt:
            break


def menu_pipeline():
    while True:
        try:
            clear_screen()
            print_header("Menu > Pipeline ML")
            print_menu_item(1, "Extraire les features")
            print_menu_item(2, "Sélection de features (top 40)")
            print_menu_item(3, "Benchmark des modèles")
            print_menu_item(4, "Entraîner un modèle")
            print(f"  {Colors.YELLOW}─────────────────────────────{Colors.END}")
            print_menu_item(0, "Retour")

            choice = ask("\nChoix")
            if choice == '1':
                model = ask_model()
                if not model: continue
                run_cmd(['python', '-m', 'scripts.extract_features_parallel', '--model', model_full_name(model)])
                pause()
            elif choice == '2':
                model = ask_model()
                if not model: continue
                run_cmd(['python', '-m', 'shared.feature_selection', '--model', model_full_name(model), '--top', '40'])
                pause()
            elif choice == '3':
                model = ask_model()
                if not model: continue
                opt = ask("Features optimisées ? (o/n)", "n")
                cmd = ['python', '-m', 'scripts.benchmark', '--model', model_full_name(model)]
                if opt and opt.lower() == 'o':
                    cmd.append('--optimized')
                run_cmd(cmd)
                pause()
            elif choice == '4':
                model = ask_model()
                if not model: continue
                run_cmd(['python', '-m', f'models.{model_full_name(model)}.train'])
                pause()
            elif choice == '0' or choice is None:
                break
        except KeyboardInterrupt:
            break


def menu_scraping():
    while True:
        try:
            clear_screen()
            print_header("Menu > Scraping")
            print_menu_item(1, "Freesound - preview (dry-run)")
            print_menu_item(2, "Freesound - télécharger", destructive=True)
            print(f"  {Colors.YELLOW}─────────────────────────────{Colors.END}")
            print_menu_item(3, "YouTube - preview (dry-run)")
            print_menu_item(4, "YouTube - télécharger", destructive=True)
            print(f"  {Colors.YELLOW}─────────────────────────────{Colors.END}")
            print_menu_item(0, "Retour")

            choice = ask("\nChoix")
            if choice in ('1', '2'):
                api_key = ask("Clé API Freesound (vide = env FREESOUND_API_KEY)")
                max_n = ask("Max sons à télécharger", "100")
                cmd = ['python', 'scripts/scrape_freesound.py', '--max', max_n]
                if api_key:
                    cmd.extend(['--api-key', api_key])
                if choice == '1':
                    cmd.append('--dry-run')
                run_cmd(cmd)
                pause()
            elif choice in ('3', '4'):
                max_v = ask("Max vidéos", "10")
                cmd = ['python', 'scripts/scrape_youtube.py', '--search', '--max-videos', max_v]
                if choice == '4':
                    cmd.append('--execute')
                run_cmd(cmd)
                pause()
            elif choice == '0' or choice is None:
                break
        except KeyboardInterrupt:
            break


def menu_drive():
    while True:
        try:
            clear_screen()
            print_header("Menu > Google Drive Sync")
            print_info("Dataset : noisy_car_detector")
            print()
            print_menu_item(1, "Status (diff local vs remote)")
            print_menu_item(2, "Upload local → Drive", destructive=True)
            print_menu_item(3, "Download Drive → local", destructive=True)
            print_menu_item(4, "Bisync (bidirectionnel)", destructive=True)
            print(f"  {Colors.YELLOW}─────────────────────────────{Colors.END}")
            print_menu_item(0, "Retour")

            choice = ask("\nChoix")
            if choice == '1':
                run_cmd(['python', 'scripts/gdrive_sync.py', '-m', 'noisy_car', '--status'])
                pause()
            elif choice == '2':
                run_cmd(['python', 'scripts/gdrive_sync.py', '-m', 'noisy_car', '--upload', '--execute'])
                pause()
            elif choice == '3':
                run_cmd(['python', 'scripts/gdrive_sync.py', '-m', 'noisy_car', '--download', '--execute'])
                pause()
            elif choice == '4':
                run_cmd(['python', 'scripts/gdrive_sync.py', '-m', 'noisy_car', '--sync', '--execute'])
                pause()
            elif choice == '0' or choice is None:
                break
        except KeyboardInterrupt:
            break


def menu_api():
    while True:
        try:
            clear_screen()
            print_header("Menu > Serveur API")
            print_menu_item(1, "Mode développement (--reload)")
            print_menu_item(2, "Mode production (4 workers)")
            print(f"  {Colors.YELLOW}─────────────────────────────{Colors.END}")
            print_menu_item(0, "Retour")

            choice = ask("\nChoix")
            if choice == '1':
                print_warning("Ctrl+C pour arrêter le serveur")
                run_cmd(['uvicorn', 'api.main:app', '--reload', '--host', '0.0.0.0', '--port', '8000'])
                pause()
            elif choice == '2':
                print_warning("Ctrl+C pour arrêter le serveur")
                run_cmd(['uvicorn', 'api.main:app', '--host', '0.0.0.0', '--port', '8000', '--workers', '4'])
                pause()
            elif choice == '0' or choice is None:
                break
        except KeyboardInterrupt:
            break


def menu_admin():
    while True:
        try:
            clear_screen()
            print_header("Menu > Administration")
            print_menu_item(1, "Créer un administrateur")
            print_menu_item(2, "Migrer SQLite → PostgreSQL", destructive=True)
            print(f"  {Colors.YELLOW}─────────────────────────────{Colors.END}")
            print_menu_item(0, "Retour")

            choice = ask("\nChoix")
            if choice == '1':
                email = ask("Email de l'administrateur")
                if email:
                    run_cmd(['python', 'scripts/make_admin.py', email])
                pause()
            elif choice == '2':
                confirm = ask("ATTENTION: opération destructive. Continuer ? (o/n)", "n")
                if confirm and confirm.lower() == 'o':
                    run_cmd(['python', 'scripts/migrate_sqlite_to_postgres.py'])
                else:
                    print_info("Migration annulée.")
                pause()
            elif choice == '0' or choice is None:
                break
        except KeyboardInterrupt:
            break


# =============================================================================
# MENU PRINCIPAL
# =============================================================================

def main():
    while True:
        try:
            clear_screen()
            show_banner()
            print()

            # Stats rapides
            stats = get_dataset_stats()
            nc = stats.get('noisy_car_detector', 0)
            cd = stats.get('car_detector', 0)
            print(f"  {Colors.DIM}Dataset: {Colors.END}{Colors.GREEN}{nc:,}{Colors.END}{Colors.DIM} slices noisy_car | {Colors.END}{Colors.GREEN}{cd:,}{Colors.END}{Colors.DIM} slices car{Colors.END}")
            print()

            print_menu_item(1, "Dataset           Gérer les données d'entraînement")
            print_menu_item(2, "Pipeline ML       Features, benchmark, entraînement")
            print_menu_item(3, "Scraping          Collecter des audios (Freesound, YouTube)")
            print_menu_item(4, "Google Drive      Synchroniser avec Drive")
            print_menu_item(5, "Inférence         Analyser un fichier audio")
            print_menu_item(6, "Serveur API       Lancer le serveur dev/prod")
            print_menu_item(7, "Administration    Outils admin")
            print(f"  {Colors.YELLOW}─────────────────────────────────────────────────{Colors.END}")
            print_menu_item(0, "Quitter")

            choice = ask("\nChoix")

            if choice == '1':
                menu_dataset()
            elif choice == '2':
                menu_pipeline()
            elif choice == '3':
                menu_scraping()
            elif choice == '4':
                menu_drive()
            elif choice == '5':
                audio = ask("Chemin du fichier audio")
                if audio:
                    run_cmd(['python', '-m', 'pipeline.orchestrator', audio])
                    pause()
            elif choice == '6':
                menu_api()
            elif choice == '7':
                menu_admin()
            elif choice == '0':
                clear_screen()
                print_success("Au revoir !")
                sys.exit(0)
        except KeyboardInterrupt:
            print()
            continue


if __name__ == "__main__":
    main()
