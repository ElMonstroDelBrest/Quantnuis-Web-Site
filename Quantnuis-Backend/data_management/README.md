# data_management/

Gestion des donnees d'entrainement : ajout de slices, decoupage audio.

## Structure

```
data_management/
├── slice_manager.py    # Gestion des slices (ajout, statut, nettoyage)
└── slicing.py          # Decoupage audio selon annotations CSV
```

## slice_manager.py - SliceManager

Gere le dataset audio d'un modele specifique.

### Constructeur

```python
manager = SliceManager("car_detector")      # ou "noisy_car_detector"
```

### Methodes

| Methode | Parametres | Description |
|---|---|---|
| `show_status()` | - | Affiche : nb slices, distribution labels, coherence fichiers/annotations |
| `add_slices(source_dir, default_label)` | source_dir: str, label: int (0/1) | Copie des .wav, renomme en slice_XXX.wav, met a jour annotation.csv |
| `remove_orphans()` | - | Supprime fichiers sans annotation et annotations sans fichier |

### CLI

```bash
python -m data_management.slice_manager -m car -a status
python -m data_management.slice_manager -m car -a add -s /path/to/wavs -l 1
python -m data_management.slice_manager -m noisy_car -a clean
```

Options :
- `-m` / `--model` : `car` ou `noisy_car` (obligatoire)
- `-a` / `--action` : `status`, `add`, `clean` (defaut: status)
- `-s` / `--source` : dossier source pour `add`
- `-l` / `--label` : label par defaut (0 ou 1)

## slicing.py - Decoupage audio

Decoupe un fichier audio long en slices selon un CSV d'annotations.

### Fonction principale

```python
slice_audio(audio_path, annotations_path, model_name="car_detector")
```

| Parametre | Type | Description |
|---|---|---|
| `audio_path` | str | Fichier audio source (.wav, .mp3, etc.) |
| `annotations_path` | str | CSV d'annotations |
| `model_name` | str | `car_detector` ou `noisy_car_detector` |

### Format CSV d'annotations

```csv
Start,End,Label,Reliability,Note
00:09:34,00:10:12,car,3,"commentaire"
00:11:30,00:11:43,noisy_car,3,""
```

### Mapping des labels

| Label CSV | car_detector | noisy_car_detector |
|---|---|---|
| `car` | 1 (voiture) | 0 (normal) |
| `noisy_car` | 1 (voiture) | 1 (bruyant) |
| `noise` / `other` | 0 (pas voiture) | ignore |
| `0` / `1` | tel quel | tel quel |

### CLI

```bash
python -m data_management.slicing -m car audio_long.wav annotations.csv
python -m data_management.slicing -m noisy_car audio_long.wav annotations.csv
```

### Fonctions utilitaires

| Fonction | Description |
|---|---|
| `time_to_seconds(time_str)` | Convertit "HH:MM:SS" ou "MM:SS" en secondes |
| `get_next_slice_num(slices_dir)` | Trouve le prochain numero disponible |
| `get_label_value(raw_label, model_name)` | Mappe label texte -> 0/1 selon le modele |
