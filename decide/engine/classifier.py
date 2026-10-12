"""Single-pass multi-task classification pipeline and latency profiling."""

import time
from contextlib import nullcontext
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

try:
    import torch
except ImportError:  # pragma: no cover
    torch = None  # type: ignore


class InferenceException(Exception):
    """Raised when an error occurs during model forward pass."""
    pass


@dataclass
class ClassificationResult:
    """Dataclass holding structured classification results and inference latency."""
    result: Dict[str, str]
    latency_ms: float
    confidence: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def __getitem__(self, item: str) -> Any:
        if item == "result":
            return self.result
        elif item == "latency_ms":
            return self.latency_ms
        elif item == "confidence":
            return self.confidence
        raise KeyError(item)

    def __contains__(self, item: str) -> bool:
        return item in ("result", "latency_ms", "confidence")

    def get(self, item: str, default: Any = None) -> Any:
        if item == "result":
            return self.result
        elif item == "latency_ms":
            return self.latency_ms
        elif item == "confidence":
            return self.confidence
        return default


class MultiTaskClassifier:
    """Wrapper around GLiNER2.5 extractor for multi-task intent and category routing."""

    def __init__(self, extractor: Any, device: Any = "cpu"):
        self.extractor = extractor
        self.device = device
        self._patch_extractor_if_needed()

    def _patch_extractor_if_needed(self) -> None:
        """Patches GLiNER2 extractor internal extraction to retain full label confidence distributions."""
        if self.extractor is None or not hasattr(self.extractor, "_extract_classification_result"):
            return
        orig_fn = self.extractor._extract_classification_result
        if getattr(orig_fn, "_is_confidence_patched", False):
            return

        extractor_ref = self.extractor

        def patched_extract_classification_result(results, schema_name, schema, embs, schema_tokens, temperature=1.0):
            prompt_str = schema_tokens[2]
            cls_config = extractor_ref._resolve_classification_config(prompt_str, schema.get("classifications", []))
            if cls_config is not None:
                task = cls_config["task"]
                cls_embeds = embs[1:]
                logits = extractor_ref.classifier(cls_embeds).squeeze(-1) / temperature
                probs = torch.softmax(logits, dim=-1) if torch is not None else None
                labels = cls_config["labels"]
                if not hasattr(extractor_ref, "_last_confidences"):
                    extractor_ref._last_confidences = {}
                if probs is not None:
                    extractor_ref._last_confidences[task] = {
                        labels[j]: float(probs[j].item()) for j in range(len(labels))
                    }
            return orig_fn(results, schema_name, schema, embs, schema_tokens, temperature)

        patched_extract_classification_result._is_confidence_patched = True
        self.extractor._extract_classification_result = patched_extract_classification_result

    def predict(self, text: str, tasks: Dict[str, List[str]]) -> ClassificationResult:
        """
        Executes single-pass multi-task classification under torch.inference_mode().
        Returns normalized predictions dictionary, confidence scores for all candidate values, and measured latency in ms.
        """
        if not text or not tasks:
            return ClassificationResult(result={}, latency_ms=0.0, confidence={})

        start_time = time.perf_counter()

        try:
            if hasattr(self.extractor, "_last_confidences"):
                self.extractor._last_confidences = {}

            inference_context = (
                torch.inference_mode()
                if torch is not None and hasattr(torch, "inference_mode")
                else nullcontext()
            )
            with inference_context:
                # Call gliner2 extractor if available
                if hasattr(self.extractor, "classify_text"):
                    raw_output = self.extractor.classify_text(text, tasks)
                elif hasattr(self.extractor, "extract"):
                    raw_output = self.extractor.extract(text, tasks)
                elif callable(self.extractor):
                    raw_output = self.extractor(text, tasks)
                else:
                    raw_output = {}

            # Map raw output to normalized output schema and confidence scores
            normalized_result: Dict[str, str] = {}
            normalized_confidence: Dict[str, Dict[str, float]] = {}

            extracted_confidences = getattr(self.extractor, "_last_confidences", {}) or {}

            for task_name, candidates in tasks.items():
                pred_label: Optional[str] = None
                task_confidence_map: Dict[str, float] = {}

                # Check if extractor captured full candidate confidences
                if task_name in extracted_confidences:
                    task_confidence_map = {
                        c: float(extracted_confidences[task_name].get(c, 0.0))
                        for c in candidates
                    }

                if isinstance(raw_output, dict) and task_name in raw_output:
                    val = raw_output[task_name]
                    # If returned as a dict with 'label'
                    if isinstance(val, dict) and "label" in val:
                        pred_label = str(val["label"])
                        if not task_confidence_map:
                            if "confidence" in val and isinstance(val["confidence"], dict):
                                task_confidence_map = {c: float(val["confidence"].get(c, 0.0)) for c in candidates}
                            elif "confidence" in val and isinstance(val["confidence"], (int, float)):
                                conf = float(val["confidence"])
                                rem = max(0.0, 1.0 - conf) / max(1, len(candidates) - 1)
                                task_confidence_map = {c: (conf if c == pred_label else rem) for c in candidates}
                            elif "score" in val and isinstance(val["score"], (int, float)):
                                conf = float(val["score"])
                                rem = max(0.0, 1.0 - conf) / max(1, len(candidates) - 1)
                                task_confidence_map = {c: (conf if c == pred_label else rem) for c in candidates}
                    # If returned as a list of extracted entities/labels or string
                    elif isinstance(val, list) and len(val) > 0:
                        first_item = val[0]
                        if isinstance(first_item, dict) and "label" in first_item:
                            pred_label = str(first_item["label"])
                            if not task_confidence_map:
                                if "score" in first_item and isinstance(first_item["score"], (int, float)):
                                    conf = float(first_item["score"])
                                    rem = max(0.0, 1.0 - conf) / max(1, len(candidates) - 1)
                                    task_confidence_map = {c: (conf if c == pred_label else rem) for c in candidates}
                                elif "confidence" in first_item and isinstance(first_item["confidence"], (int, float)):
                                    conf = float(first_item["confidence"])
                                    rem = max(0.0, 1.0 - conf) / max(1, len(candidates) - 1)
                                    task_confidence_map = {c: (conf if c == pred_label else rem) for c in candidates}
                        else:
                            pred_label = str(first_item)
                    else:
                        pred_label = str(val)
                else:
                    # Fallback to first candidate if model returns no match
                    pred_label = candidates[0] if candidates else "unknown"

                normalized_result[task_name] = pred_label

                # Populate fallback confidence map if still empty
                if not task_confidence_map:
                    if pred_label in candidates:
                        task_confidence_map = {c: (1.0 if c == pred_label else 0.0) for c in candidates}
                    else:
                        task_confidence_map = {c: 0.0 for c in candidates}

                normalized_confidence[task_name] = task_confidence_map

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            return ClassificationResult(
                result=normalized_result,
                latency_ms=round(elapsed_ms, 2),
                confidence=normalized_confidence,
            )
        except Exception as e:
            raise InferenceException(f"Model inference failed: {e}") from e

