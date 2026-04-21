#!/usr/bin/env python3
"""
================================================================================
                    YOUTUBE AUDIO SCRAPER
================================================================================

Télécharge l'audio de vidéos YouTube (dashcam, trafic, voitures bruyantes),
découpe en segments de 4s/22050Hz/mono et intègre au dataset noisy_car_detector.

Usage:
    # Dry-run (par défaut) - voir les vidéos trouvées
    python -m scripts.scrape_youtube --search "loud exhaust sound" --max-videos 5

    # Télécharger et intégrer
    python -m scripts.scrape_youtube --search --execute

    # URL unique avec label forcé
    python -m scripts.scrape_youtube --url "https://youtube.com/watch?v=..." --label 1 --execute

    # Playlist
    python -m scripts.scrape_youtube --playlist "URL" --label 0 --execute

================================================================================
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from config import get_settings
from data_management.slice_manager import SliceManager
from shared import (
    print_header, print_success, print_info, print_warning, print_error, print_progress
)

settings = get_settings()

SEGMENT_DURATION = 4  # secondes
SEGMENT_SAMPLES = SEGMENT_DURATION * settings.SAMPLE_RATE
VIDEO_TIMEOUT = 120  # secondes par vidéo

DEFAULT_QUERIES = [
    'dashcam loud car compilation',
    'noisy car street recording',
    'traffic city ambiance recording',
    'motorcycle exhaust loud',
    'street traffic noise recording binaural',
]

NOISY_KEYWORDS = ['loud', 'noisy', 'fast', 'exhaust', 'revving', 'sport',
                  'modified', 'tuning', 'compilation', 'race', 'turbo']
NORMAL_KEYWORDS = ['traffic', 'ambient', 'city', 'calm', 'normal', 'ambiance',
                   'binaural', 'asmr', 'quiet']


def label_from_query(query: str) -> int:
    """Détermine le label à partir des mots-clés de la query."""
    q = query.lower()
    if any(kw in q for kw in NOISY_KEYWORDS):
        return 1
    if any(kw in q for kw in NORMAL_KEYWORDS):
        return 0
    return None


def load_history(path: Path) -> dict:
    """Charge l'historique partagé (compatible Freesound)."""
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_history(path: Path, history: dict):
    """Sauvegarde l'historique."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(history, f, indent=2)


def get_video_ids_from_search(query: str, max_results: int) -> list:
    """Recherche YouTube et retourne les IDs."""
    cmd = ["yt-dlp", "--get-id", f"ytsearch{max_results}:{query}"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                check=True, timeout=30)
        return [vid.strip() for vid in result.stdout.strip().split('\n') if vid.strip()]
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print_warning(f"Erreur recherche '{query}': {e}")
        return []


def get_video_ids_from_playlist(url: str) -> list:
    """Récupère les IDs d'une playlist."""
    cmd = ["yt-dlp", "--flat-playlist", "--get-id", url]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                check=True, timeout=60)
        return [vid.strip() for vid in result.stdout.strip().split('\n') if vid.strip()]
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print_warning(f"Erreur playlist : {e}")
        return []


def get_video_id_from_url(url: str) -> str:
    """Extrait l'ID d'une URL YouTube."""
    try:
        result = subprocess.run(["yt-dlp", "--get-id", url],
                                capture_output=True, text=True, check=True, timeout=15)
        return result.stdout.strip()
    except Exception:
        return None


def download_audio(video_id: str, output_path: Path, max_duration: int) -> bool:
    """Télécharge l'audio d'une vidéo en WAV 22050Hz mono."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [
        "yt-dlp", "-x",
        "--audio-format", "wav",
        "--postprocessor-args", f"-ar {settings.SAMPLE_RATE} -ac 1",
        "--max-duration", str(max_duration),
        "-o", str(output_path),
        "--no-playlist",
        url,
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True,
                        timeout=VIDEO_TIMEOUT)
        return output_path.exists()
    except subprocess.TimeoutExpired:
        print_warning(f"  Timeout pour {video_id}")
        return False
    except subprocess.CalledProcessError as e:
        err = e.stderr.lower() if e.stderr else ""
        if any(w in err for w in ['unavailable', 'private', 'deleted', 'geo']):
            print_warning(f"  Vidéo {video_id} non disponible")
        else:
            print_warning(f"  Erreur yt-dlp pour {video_id}")
        return False


def segment_and_filter(audio_path: Path, rms_threshold: float) -> list:
    """Charge, découpe en 4s et filtre par RMS. Retourne les segments valides."""
    try:
        y, _ = librosa.load(audio_path, sr=settings.SAMPLE_RATE, mono=True)
    except Exception as e:
        print_warning(f"  Erreur chargement audio: {e}")
        return []

    segments = []
    n_segments = len(y) // SEGMENT_SAMPLES

    for i in range(n_segments):
        seg = y[i * SEGMENT_SAMPLES:(i + 1) * SEGMENT_SAMPLES]
        rms = np.sqrt(np.mean(seg ** 2))
        if rms >= rms_threshold:
            segments.append(seg)

    return segments


def main():
    parser = argparse.ArgumentParser(
        description="Scraper YouTube audio pour Quantnuis",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="URL d'une seule vidéo")
    source.add_argument("--playlist", help="URL d'une playlist")
    source.add_argument("--search", nargs='?', const="default",
                        help="Recherche YouTube (sans argument = queries par défaut)")
    source.add_argument("--queries-file", type=Path,
                        help="Fichier texte (une query par ligne)")

    parser.add_argument("--max-videos", type=int, default=10, help="Max vidéos (défaut: 10)")
    parser.add_argument("--max-duration", type=int, default=300, help="Max durée/vidéo en sec (défaut: 300)")
    parser.add_argument("--rms-threshold", type=float, default=0.01, help="Seuil RMS (défaut: 0.01)")
    parser.add_argument("--label", type=int, choices=[0, 1], help="Forcer un label")
    parser.add_argument("--execute", action="store_true", help="Lancer (dry-run par défaut)")

    args = parser.parse_args()

    # Vérifier yt-dlp
    if not shutil.which("yt-dlp"):
        print_error("yt-dlp n'est pas installé.")
        print_info("Installez-le : sudo pacman -S yt-dlp")
        sys.exit(1)

    print_header("Scraper YouTube Audio")

    # Collecter les vidéos avec leur query source
    videos = []  # list of (query, video_id)

    if args.url:
        vid = get_video_id_from_url(args.url)
        if vid:
            videos.append(("manual_url", vid))
    elif args.playlist:
        ids = get_video_ids_from_playlist(args.playlist)
        videos = [("manual_playlist", vid) for vid in ids]
    elif args.queries_file:
        with open(args.queries_file) as f:
            queries = [l.strip() for l in f if l.strip()]
        for q in queries:
            if len(videos) >= args.max_videos:
                break
            remaining = args.max_videos - len(videos)
            ids = get_video_ids_from_search(q, remaining)
            videos.extend([(q, vid) for vid in ids])
    else:  # --search
        queries = [args.search] if args.search != "default" else DEFAULT_QUERIES
        for q in queries:
            if len(videos) >= args.max_videos:
                break
            remaining = args.max_videos - len(videos)
            ids = get_video_ids_from_search(q, remaining)
            videos.extend([(q, vid) for vid in ids])

    videos = videos[:args.max_videos]

    # Charger historique
    model_dir = settings.DATA_DIR / "noisy_car_detector"
    history_file = model_dir / "scraping_history.json"
    history = load_history(history_file)
    yt_history = set(history.get("youtube", []))

    # Filtrer déjà traités
    new_videos = [(q, vid) for q, vid in videos if vid not in yt_history]
    skipped = len(videos) - len(new_videos)

    print_info(f"Vidéos trouvées : {len(videos)}")
    if skipped:
        print_info(f"Déjà traitées : {skipped}")
    print_info(f"À traiter : {len(new_videos)}")

    if not new_videos:
        print_warning("Aucune nouvelle vidéo à traiter.")
        return

    # Dry-run
    if not args.execute:
        print_header("DRY-RUN")
        print_warning("Utilisez --execute pour lancer le téléchargement.")
        for query, vid in new_videos:
            label = args.label if args.label is not None else label_from_query(query)
            print_info(f"  {vid} | query='{query}' | label={label}")
        return

    # Téléchargement et traitement
    print_header("Téléchargement et traitement")

    tmp_dir = model_dir / "scraping_tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    (tmp_dir / "0").mkdir(parents=True, exist_ok=True)
    (tmp_dir / "1").mkdir(parents=True, exist_ok=True)

    stats = {"processed": 0, "segments": {0: 0, 1: 0}, "rejected": 0}

    for i, (query, vid) in enumerate(new_videos):
        print_progress(i + 1, len(new_videos), prefix="Vidéos: ")

        label = args.label if args.label is not None else label_from_query(query)
        if label is None:
            print_warning(f"  Pas de label pour query '{query}', skip")
            continue

        # Télécharger
        audio_path = tmp_dir / f"{vid}.wav"
        if not download_audio(vid, audio_path, args.max_duration):
            continue

        # Découper et filtrer
        segments = segment_and_filter(audio_path, args.rms_threshold)
        audio_path.unlink(missing_ok=True)

        if not segments:
            print_info(f"  {vid}: aucun segment valide")
            continue

        # Sauvegarder
        rejected = (len(segments))  # will update below
        for idx, seg in enumerate(segments):
            name = f"yt_{vid}_{idx:03d}.wav"
            sf.write(tmp_dir / str(label) / name, seg, settings.SAMPLE_RATE)

        n_total_possible = int(librosa.get_duration(filename=str(tmp_dir / str(label) / f"yt_{vid}_000.wav"),
                                                     sr=settings.SAMPLE_RATE)) if segments else 0
        stats["segments"][label] += len(segments)
        stats["processed"] += 1
        yt_history.add(vid)

        print_info(f"  {vid}: {len(segments)} segments (label={label})")

    print("")  # newline after progress bar

    # Intégration
    print_header("Intégration au dataset")
    manager = SliceManager("noisy_car_detector")

    for label in [0, 1]:
        label_dir = tmp_dir / str(label)
        if any(label_dir.glob("*.wav")):
            print_info(f"Ajout label {label}...")
            manager.add_slices(str(label_dir), default_label=label)

    # Sauvegarder historique
    history["youtube"] = list(yt_history)
    save_history(history_file, history)

    # Résumé
    print_header("Résumé")
    print_info(f"Vidéos traitées : {stats['processed']}")
    print_info(f"Segments label 0 (normal)  : {stats['segments'][0]}")
    print_info(f"Segments label 1 (bruyant) : {stats['segments'][1]}")
    total = stats['segments'][0] + stats['segments'][1]
    print_success(f"Total : {total} segments ajoutés")

    # Nettoyage
    shutil.rmtree(tmp_dir)
    print_success("Scraping YouTube terminé")


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
