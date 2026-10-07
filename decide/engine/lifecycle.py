"""Engine state registry, warmup routines, and FastAPI lifespan management."""

import time
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI
import torch
from decide.config import get_settings
from decide.engine.classifier import MultiTaskClassifier
from decide.engine.loader import resolve_device, load_gliner_model


class EngineState:
    """Singleton tracking runtime model readiness and active compute target."""

    def __init__(self):
        self.is_loaded: bool = False
        self.device_name: str = "unknown"
        self.classifier: Optional[MultiTaskClassifier] = None
        self.load_time_seconds: float = 0.0

    def set_ready(
        self,
        classifier: MultiTaskClassifier,
        device_name: str,
        load_time_seconds: float = 0.0,
    ) -> None:
        self.classifier = classifier
        self.device_name = device_name
        self.load_time_seconds = load_time_seconds
        self.is_loaded = True

    def reset(self) -> None:
        self.is_loaded = False
        self.device_name = "unknown"
        self.classifier = None
        self.load_time_seconds = 0.0


# Global engine state singleton
engine_state = EngineState()


def get_engine_state() -> EngineState:
    """Returns global engine state instance."""
    return engine_state


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler:
    1. Loads GLiNER2.5 model weights into memory.
    2. Runs warmup inference.
    3. Sets engine readiness flag.
    4. Cleans up GPU memory on shutdown.
    """
    settings = get_settings()
    device = resolve_device(settings.device)
    device_name = str(device)
    start_time = time.perf_counter()

    try:
        extractor = load_gliner_model(device=device, local_files_only=False)
        classifier = MultiTaskClassifier(extractor=extractor, device=device)

        # Warmup forward pass
        classifier.predict("warmup test sentence", {"intent": ["support", "general"]})
        load_time = time.perf_counter() - start_time
        engine_state.set_ready(classifier, device_name, load_time_seconds=round(load_time, 3))
    except Exception as e:
        import logging
        logging.getLogger("decide.engine.lifecycle").error("Failed to load model on startup: %s", e, exc_info=True)


    yield

    # Teardown
    engine_state.reset()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
