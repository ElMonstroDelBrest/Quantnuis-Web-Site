# shared/

Utilitaires partages entre les modeles, le pipeline et l'API.

## Structure

```
shared/
├── audio_utils.py       # Chargement audio + extraction de features (runtime)
├── colors.py            # Codes ANSI pour terminal
├── logger.py            # Fonctions d'affichage formatees
└── feature_selection.py # Selection des meilleures features (entrainement)
```

> `benchmark.py` et `benchmark_cnn.py` ont ete deplaces dans `scripts/`.

## audio_utils.py - Fonctions audio (runtime)

Utilise par les deux modeles et le pipeline pour l'inference.

| Fonction | Signature | Description |
|---|---|---|
| `load_audio` | `(file_path, sr=22050) -> (y, sr)` | Charge un fichier audio via librosa. Mono, reechantillonne. |
| `normalize_audio` | `(y) -> y` | Normalise le signal entre -1 et 1. |
| `extract_base_features` | `(y, sr) -> dict` | ~100 features : RMS, ZCR, spectral (centroid, bandwidth, rolloff, flatness, contrast), HPSS, MFCC (40), chroma (12), tempo, energie. |
| `extract_vehicle_features` | `(y, sr) -> dict` | ~60 features : bandes frequence moteur (20-100, 100-300, 300-2000, >2000 Hz), delta MFCC (13), mel bandes, onset, spectral flux, autocorrelation. |
| `extract_noise_features` | `(y, sr) -> dict` | ~65 features : F0/RPM, HNR, PSD bandes moteur/echappement, spectral peaks, dB peaks, crest factor, energie haute frequence. |
| `extract_all_features` | `(y, sr) -> dict` | Combine base + vehicle + noise (~225 features). |
| `select_features` | `(all_features, feature_names) -> dict` | Filtre le sous-ensemble de features demande par un modele. |

### Bandes de frequence vehicule

| Bande | Hz | Signification |
|---|---|---|
| `psd_motor_low` | 50-150 | Fondamentale moteur basse |
| `psd_motor_high` | 150-300 | Fondamentale haute / harmoniques |
| `psd_harmonics` | 300-800 | Harmoniques moteur |
| `psd_exhaust` | 800-2000 | Echappement |
| `psd_turbo` | 2000-4000 | Sifflement turbo / echappement sport |
| `psd_aero` | 4000-8000 | Bruit aerodynamique / pneus |

## colors.py - Codes ANSI

Classe `Colors` avec constantes ANSI :
- Couleurs : `CYAN`, `GREEN`, `YELLOW`, `RED`, `BLUE`, `MAGENTA`, `WHITE`
- Styles : `BOLD`, `DIM`, `ITALIC`, `UNDERLINE`
- Reset : `END` (obligatoire apres chaque style)

## logger.py - Affichage terminal

| Fonction | Prefixe | Couleur | Description |
|---|---|---|---|
| `print_header(title, width=50)` | `---` | Cyan | En-tete de section en majuscules |
| `print_success(msg)` | `[OK]` | Vert | Message de succes |
| `print_info(msg)` | `[i]` | Cyan | Information |
| `print_warning(msg)` | `[!]` | Jaune | Avertissement |
| `print_error(msg)` | `[ERREUR]` | Rouge | Erreur |
| `print_progress(current, total, prefix)` | barre | - | Barre de progression |
| `print_box(content, color, emoji)` | boite | variable | Contenu dans une boite formatee |

## feature_selection.py - Selection de features

Analyse d'importance, suppression de redondance, selection des top features.

```bash
python -m shared.feature_selection --model car_detector --top 40
python -m shared.feature_selection --model car_detector --analyze
```
