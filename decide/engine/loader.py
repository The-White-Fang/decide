"""Device resolution and model checkpoint loader."""

from pathlib import Path
from typing import Literal, Optional, Any
import torch
from decide.config import get_settings


def resolve_device(configured_device: Literal["auto", "cpu", "cuda"] | str) -> torch.device:
    """
    Resolves compute target device based on configuration and runtime hardware availability.
    """
    target = configured_device.lower()
    if target == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda:0")
        return torch.device("cpu")
    elif target == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA compute target requested via DEVICE=cuda, but no CUDA GPU is available.")
        return torch.device("cuda:0")
    elif target == "cpu":
        return torch.device("cpu")
    else:
        raise ValueError(f"Unsupported device target '{configured_device}'. Must be 'auto', 'cpu', or 'cuda'.")


def load_gliner_model(
    checkpoint: Optional[str] = None,
    device: Optional[torch.device] = None,
    cache_dir: Optional[Path | str] = None,
    local_files_only: bool = False,
) -> Any:
    """
    Loads GLiNER2.5 extractor and sets model into evaluation mode on target device.
    """
    settings = get_settings()
    ckpt = checkpoint or settings.model_checkpoint
    target_device = device or resolve_device(settings.device)
    target_cache = cache_dir or settings.cache_dir

    try:
        from gliner2 import AutoExtractor  # type: ignore
        cache_str = str(target_cache) if target_cache is not None else None
        extractor = AutoExtractor.from_pretrained(
            ckpt,
            cache_dir=cache_str,
            local_files_only=local_files_only,
        )
        if hasattr(extractor, "model"):
            extractor.model.to(target_device)
            extractor.model.eval()
        elif hasattr(extractor, "to"):
            extractor.to(target_device)
            if hasattr(extractor, "eval"):
                extractor.eval()
        return extractor
    except Exception as e:

        # Re-raise descriptive error
        raise RuntimeError(f"Failed to load model from checkpoint '{ckpt}': {e}") from e
