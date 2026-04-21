# pipeline/

Orchestrateur du pipeline d'analyse audio a deux modeles en cascade.

## Structure

```
pipeline/
└── orchestrator.py    # Pipeline + PipelineResult
```

## Flux du pipeline

```
Audio -> CarDetector (voiture ?)
            |
         NON -> STOP ("Pas de voiture")
            |
         OUI -> NoisyCarDetector (bruyante ?)
                    |
                 NON -> "Voiture normale (~65 dB)"
                    |
                 OUI -> "Voiture bruyante (~95 dB)"
```

## PipelineResult (dataclass)

| Attribut | Type | Description |
|---|---|---|
| `car_detected` | bool | Voiture detectee ? |
| `car_confidence` | float | Confiance detection (0-100) |
| `car_probability` | float | Probabilite sigmoid (0-1) |
| `is_noisy` | bool (None) | Bruyante ? (None si pas de voiture) |
| `noisy_confidence` | float (None) | Confiance analyse bruit |
| `noisy_probability` | float (None) | Probabilite brute |
| `message` | str | Message recapitulatif |

### Methodes

| Methode | Retour | Description |
|---|---|---|
| `to_dict()` | dict | Format complet (7 champs) |
| `to_simplified()` | dict | Format frontend : `{hasNoisyVehicle, carDetected, confidence, message}` |

## Pipeline (classe)

| Methode | Parametres | Description |
|---|---|---|
| `__init__()` | - | Instancie CarDetector + NoisyCarDetector |
| `load_models()` | - | Charge les 2 modeles. CarDetector obligatoire, NoisyCarDetector optionnel. Retourne bool. |
| `analyze(audio_path, verbose=False)` | audio_path: str | Execute le pipeline cascade. Retourne PipelineResult. |

## Usage

```python
from pipeline import Pipeline

pipeline = Pipeline()
pipeline.load_models()

result = pipeline.analyze("audio.wav")
print(result.to_simplified())
```

## CLI

```bash
python -m pipeline.orchestrator audio.wav
```
