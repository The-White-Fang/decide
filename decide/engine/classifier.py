"""Single-pass multi-task classification pipeline and latency profiling."""

import time
from dataclasses import dataclass
from typing import Dict, List, Any
import torch


class InferenceException(Exception):
    """Raised when an error occurs during model forward pass."""
    pass


@dataclass
class ClassificationResult:
    """Dataclass holding structured classification results and inference latency."""
    result: Dict[str, str]
    latency_ms: float

    def __getitem__(self, item: str) -> Any:
        if item == "result":
            return self.result
        elif item == "latency_ms":
            return self.latency_ms
        raise KeyError(item)

    def __contains__(self, item: str) -> bool:
        return item in ("result", "latency_ms")

    def get(self, item: str, default: Any = None) -> Any:
        if item == "result":
            return self.result
        elif item == "latency_ms":
            return self.latency_ms
        return default


class MultiTaskClassifier:
    """Wrapper around GLiNER2.5 extractor for multi-task intent and category routing."""

    def __init__(self, extractor: Any, device: torch.device):
        self.extractor = extractor
        self.device = device

    def predict(self, text: str, tasks: Dict[str, List[str]]) -> ClassificationResult:
        """
        Executes single-pass multi-task classification under torch.inference_mode().
        Returns normalized predictions dictionary and measured latency in ms.
        """
        if not text or not tasks:
            return ClassificationResult(result={}, latency_ms=0.0)

        start_time = time.perf_counter()

        try:
            with torch.inference_mode():
                # Call gliner2 extractor if available
                if hasattr(self.extractor, "extract"):
                    raw_output = self.extractor.extract(text, tasks)
                elif callable(self.extractor):
                    raw_output = self.extractor(text, tasks)
                else:
                    raw_output = {}

            # Map raw output to normalized output schema
            normalized_result: Dict[str, str] = {}
            for task_name, candidates in tasks.items():
                if isinstance(raw_output, dict) and task_name in raw_output:
                    val = raw_output[task_name]
                    # If returned as a dict with 'label'
                    if isinstance(val, dict) and "label" in val:
                        normalized_result[task_name] = str(val["label"])
                    # If returned as a list of extracted entities/labels or string
                    elif isinstance(val, list) and len(val) > 0:
                        first_item = val[0]
                        if isinstance(first_item, dict) and "label" in first_item:
                            normalized_result[task_name] = str(first_item["label"])
                        else:
                            normalized_result[task_name] = str(first_item)
                    else:
                        normalized_result[task_name] = str(val)
                else:
                    # Fallback to first candidate if model returns no match
                    normalized_result[task_name] = candidates[0] if candidates else "unknown"

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            return ClassificationResult(
                result=normalized_result,
                latency_ms=round(elapsed_ms, 2),
            )
        except Exception as e:
            raise InferenceException(f"Model inference failed: {e}") from e

