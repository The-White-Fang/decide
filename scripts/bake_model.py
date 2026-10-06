import os
import sys
from pathlib import Path


def bake() -> bool:
    checkpoint = os.environ.get("MODEL_CHECKPOINT")
    cache_dir = os.environ.get("CACHE_DIR")
    if not checkpoint or not cache_dir:
        try:
            from decide.config import get_settings
            settings = get_settings()
            checkpoint = checkpoint or settings.model_checkpoint
            cache_dir = cache_dir or str(settings.cache_dir)
        except Exception:
            checkpoint = checkpoint or "fastino/GLiNER2.5-Decide"
            cache_dir = cache_dir or "/root/.cache/huggingface"

    print(f"==> Baking model weights for '{checkpoint}' into '{cache_dir}'...")

    try:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        from gliner2 import AutoExtractor
        AutoExtractor.from_pretrained(
            checkpoint,
            cache_dir=cache_dir,
            local_files_only=False,
        )
        print("==> Model weights baked successfully!")
        return True
    except Exception as e:
        print(f"Warning: Model download failed: {e}", file=sys.stderr)
        # In build environments without model access, continue build
        return False


if __name__ == "__main__":
    bake()
    sys.exit(0)



