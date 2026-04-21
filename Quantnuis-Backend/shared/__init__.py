# Shared utilities module
# Colors and logger are always available (no heavy dependencies)
from .colors import Colors
from .logger import (
    print_header,
    print_success,
    print_info,
    print_warning,
    print_error,
    print_progress
)

__all__ = [
    "Colors",
    "print_header",
    "print_success",
    "print_info",
    "print_warning",
    "print_error",
    "print_progress",
]

# audio_utils requires librosa/numpy — lazy import to avoid breaking EC2
# Import directly: from shared.audio_utils import load_audio, ...
try:
    from .audio_utils import (
        load_audio,
        normalize_audio,
        load_melspectrogram,
        extract_base_features,
        extract_vehicle_features,
        extract_noise_features,
        extract_all_features,
        select_features
    )
    __all__ += [
        "load_audio",
        "normalize_audio",
        "load_melspectrogram",
        "extract_base_features",
        "extract_vehicle_features",
        "extract_noise_features",
        "extract_all_features",
        "select_features"
    ]
except ImportError:
    pass
