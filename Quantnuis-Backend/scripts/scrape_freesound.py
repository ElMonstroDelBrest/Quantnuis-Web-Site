#!/usr/bin/env python3
"""
================================================================================
                    FREESOUND.ORG SCRAPER
================================================================================

Télécharge des sons de voitures depuis l'API Freesound.org, les convertit
en segments de 4s/22050Hz/mono et les intègre au dataset noisy_car_detector.

Usage:
    python -m scripts.scrape_freesound --api-key YOUR_KEY --max 100
    python -m scripts.scrape_freesound --api-key YOUR_KEY --query "loud car" --label 1
    python -m scripts.scrape_freesound --api-key YOUR_KEY --dry-run

================================================================================
"""

import os
import sys
import argparse
import time
import json
import shutil
import requests
import librosa
import soundfile as sf
import numpy as np
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import get_settings
from shared import print_header, print_success, print_info, print_warning, print_error, print_progress
from data_management.slice_manager import SliceManager

settings = get_settings()
FREESOUND_API_URL = "https://freesound.org/apiv2"
TARGET_SR = settings.SAMPLE_RATE
SEGMENT_DURATION = 4.0
MIN_DURATION = 3.0
SEGMENT_SAMPLES = int(TARGET_SR * SEGMENT_DURATION)

DEFAULT_QUERIES = [
    'car engine', 'traffic noise', 'vehicle passing', 'road noise',
    'car horn', 'motorcycle engine', 'truck engine', 'loud car',
    'car acceleration', 'engine revving', 'sport car exhaust',
]

NOISY_TAGS = {'loud', 'noisy', 'revving', 'acceleration', 'sport', 'motorcycle',
              'horn', 'exhaust', 'fast', 'modified', 'turbo', 'race'}
NORMAL_TAGS = {'traffic', 'ambient', 'city', 'idle', 'passing', 'road',
               'calm', 'normal', 'street'}


def auto_label(tags: list) -> int:
    """Détermine le label via les tags Freesound. Retourne None si ambigu."""
    tag_set = set(t.lower() for t in tags)
    if tag_set & NOISY_TAGS:
        return 1
    if tag_set & NORMAL_TAGS:
        return 0
    return None


def segment_audio(audio_path: Path) -> list:
    """Charge, convertit et segmente un audio en chunks de 4s."""
    try:
        y, _ = librosa.load(audio_path, sr=TARGET_SR, mono=True)
    except Exception as e:
        print_warning(f"Erreur chargement {audio_path.name}: {e}")
        return []

    duration = len(y) / TARGET_SR
    if duration < MIN_DURATION:
        return []

    segments = []
    if duration >= SEGMENT_DURATION:
        # Découpe sans overlap
        for start in range(0, len(y) - SEGMENT_SAMPLES + 1, SEGMENT_SAMPLES):
            segments.append(y[start:start + SEGMENT_SAMPLES])
    else:
        # Pad si entre 3s et 4s
        padded = librosa.util.fix_length(y, size=SEGMENT_SAMPLES)
        segments.append(padded)

    return segments


def load_history(path: Path) -> set:
    """Charge l'historique des IDs déjà téléchargés."""
    try:
        with open(path) as f:
            data = json.load(f)
            return set(data.get("freesound", []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_history(path: Path, freesound_ids: set):
    """Sauvegarde l'historique (merge avec YouTube si présent)."""
    try:
        with open(path) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    data["freesound"] = list(freesound_ids)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Scraper Freesound.org")
    parser.add_argument("--api-key", help="Clé API Freesound v2")
    parser.add_argument("--max", type=int, default=100, help="Max sons à télécharger (défaut: 100)")
    parser.add_argument("--query", help="Requête de recherche unique")
    parser.add_argument("--queries-file", help="Fichier texte (une requête par ligne)")
    parser.add_argument("--label", type=int, choices=[0, 1], help="Forcer un label")
    parser.add_argument("--dry-run", action="store_true", help="Preview sans télécharger")

    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("FREESOUND_API_KEY")
    if not api_key:
        print_error("Clé API manquante. --api-key ou env FREESOUND_API_KEY")
        sys.exit(1)

    # Chemins
    model_dir = settings.DATA_DIR / "noisy_car_detector"
    tmp_dir = model_dir / "scraping_tmp"
    history_file = model_dir / "scraping_history.json"

    # Queries
    if args.query:
        queries = [args.query]
    elif args.queries_file:
        with open(args.queries_file) as f:
            queries = [l.strip() for l in f if l.strip()]
    else:
        queries = DEFAULT_QUERIES

    print_header("Scraper Freesound.org")
    print_info(f"Queries : {len(queries)}")
    print_info(f"Max downloads : {args.max}")
    print_info(f"Dry-run : {'oui' if args.dry_run else 'non'}")

    if not args.dry_run:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        (tmp_dir / "0").mkdir(parents=True, exist_ok=True)
        (tmp_dir / "1").mkdir(parents=True, exist_ok=True)

    history = load_history(history_file)
    print_info(f"Historique : {len(history)} sons déjà scraped")

    # Recherche et collecte
    sounds = []
    for query in queries:
        if len(sounds) >= args.max:
            break

        print_info(f"Recherche : '{query}'")
        page = 1

        while len(sounds) < args.max:
            params = {
                "query": query,
                "token": api_key,
                "page": page,
                "page_size": 150,
                "fields": "id,name,previews,tags,duration",
                "filter": f"duration:[{MIN_DURATION} TO 300]",
            }

            try:
                resp = requests.get(f"{FREESOUND_API_URL}/search/text/",
                                    params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                print_warning(f"Erreur API : {e}")
                break

            time.sleep(0.5)

            found_new = False
            for sound in data.get('results', []):
                if len(sounds) >= args.max:
                    break
                if sound['id'] in history:
                    continue

                found_new = True
                label = args.label if args.label is not None else auto_label(sound['tags'])
                if label is None:
                    continue

                preview_url = (sound.get('previews', {}).get('preview-hq-mp3')
                               or sound.get('previews', {}).get('preview-hq-ogg'))
                if not preview_url:
                    continue

                sounds.append({
                    "id": sound['id'],
                    "name": sound['name'],
                    "label": label,
                    "url": preview_url,
                })
                history.add(sound['id'])

            if not data.get('next') or not found_new:
                break
            page += 1

    # Téléchargement et traitement
    print_header(f"Traitement de {len(sounds)} sons")

    stats = {0: 0, 1: 0}
    downloaded = 0

    for i, sound in enumerate(sounds):
        print_progress(i + 1, len(sounds), prefix="Traitement: ")

        if args.dry_run:
            print_info(f"  [DRY-RUN] {sound['name']} -> label {sound['label']}")
            stats[sound['label']] += 1
            continue

        try:
            audio_resp = requests.get(sound['url'], timeout=30)
            audio_resp.raise_for_status()

            dl_path = tmp_dir / f"dl_{sound['id']}.tmp"
            with open(dl_path, 'wb') as f:
                f.write(audio_resp.content)

            segments = segment_audio(dl_path)
            dl_path.unlink()

            if not segments:
                continue

            for idx, seg in enumerate(segments):
                name = f"fs_{sound['id']}_{idx}.wav"
                sf.write(tmp_dir / str(sound['label']) / name, seg, TARGET_SR)
                stats[sound['label']] += 1

            downloaded += 1

        except requests.RequestException as e:
            print_warning(f"Erreur download {sound['name']}: {e}")
        except Exception as e:
            print_error(f"Erreur traitement {sound['name']}: {e}")

    # Résumé et intégration
    print_header("Résumé")
    print_info(f"Sons trouvés : {len(sounds)}")
    print_info(f"Sons traités : {downloaded}")
    print_info(f"Segments label 0 (normal)  : {stats[0]}")
    print_info(f"Segments label 1 (bruyant) : {stats[1]}")

    if not args.dry_run:
        save_history(history_file, history)
        print_success(f"Historique sauvegardé ({len(history)} entrées)")

        manager = SliceManager("noisy_car_detector")
        for label in [0, 1]:
            label_dir = tmp_dir / str(label)
            if any(label_dir.glob("*.wav")):
                print_info(f"Intégration label {label}...")
                manager.add_slices(str(label_dir), default_label=label)

        shutil.rmtree(tmp_dir)
        print_success("Nettoyage terminé")

    print_success("Scraping Freesound terminé")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠ Annulé")
        tmp = settings.DATA_DIR / "noisy_car_detector" / "scraping_tmp"
        if tmp.exists():
            shutil.rmtree(tmp)
    except Exception as e:
        print_error(str(e))
        sys.exit(1)
