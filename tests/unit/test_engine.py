"""Unit tests for decide.engine subsystem (Task 04 / Module 04)."""

from pathlib import Path
from unittest.mock import MagicMock
import pytest
from fastapi import FastAPI
import torch

from decide.engine.classifier import MultiTaskClassifier, ClassificationResult, InferenceException
from decide.engine.lifecycle import EngineState, get_engine_state, lifespan
from decide.engine.loader import resolve_device, load_gliner_model


def test_device_resolution_auto_and_cpu():
    """Verify resolve_device handles auto and cpu targets cleanly."""
    cpu_device = resolve_device("cpu")
    assert cpu_device.type == "cpu"

    cpu_upper = resolve_device("CPU")
    assert cpu_upper.type == "cpu"

    auto_device = resolve_device("auto")
    assert auto_device.type in ("cuda", "cpu")

    with pytest.raises(ValueError, match="Unsupported device target"):
        resolve_device("unknown_device")


def test_device_resolution_cuda_when_no_gpu(monkeypatch):
    """Verify requesting CUDA when no GPU exists raises a descriptive RuntimeError."""
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(RuntimeError, match="CUDA compute target requested"):
        resolve_device("cuda")


def test_device_resolution_cuda_when_available(monkeypatch):
    """Verify requesting CUDA or auto when GPU exists resolves cuda:0."""
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    cuda_device = resolve_device("cuda")
    assert cuda_device.type == "cuda"
    assert cuda_device.index == 0

    auto_device = resolve_device("auto")
    assert auto_device.type == "cuda"


def test_load_gliner_model_success(monkeypatch):
    """Verify load_gliner_model calls AutoExtractor and moves model to device."""
    import sys
    mock_extractor = MagicMock()
    mock_extractor.model = MagicMock()

    mock_auto_extractor = MagicMock()
    mock_auto_extractor.from_pretrained.return_value = mock_extractor

    fake_gliner = MagicMock()
    fake_gliner.AutoExtractor = mock_auto_extractor
    monkeypatch.setitem(sys.modules, "gliner2", fake_gliner)

    device = torch.device("cpu")
    extractor = load_gliner_model(
        checkpoint="fastino/GLiNER2.5-Decide",
        device=device,
        cache_dir=Path("/tmp/cache"),
        local_files_only=True,
    )

    assert extractor is mock_extractor
    mock_auto_extractor.from_pretrained.assert_called_once_with(
        "fastino/GLiNER2.5-Decide",
        cache_dir="/tmp/cache",
        local_files_only=True,
    )
    mock_extractor.model.to.assert_called_once_with(device)
    mock_extractor.model.eval.assert_called_once()



def test_load_gliner_model_failure(monkeypatch):
    """Verify load_gliner_model raises RuntimeError if loading fails."""
    import sys
    fake_gliner = MagicMock()
    fake_gliner.AutoExtractor.from_pretrained.side_effect = FileNotFoundError("Checkpoint not found")
    monkeypatch.setitem(sys.modules, "gliner2", fake_gliner)

    with pytest.raises(RuntimeError, match="Failed to load model from checkpoint"):
        load_gliner_model(checkpoint="invalid/path", device=torch.device("cpu"))


def test_classification_result_dataclass_and_dict_compatibility():
    """Verify ClassificationResult acts both as a dataclass and dict subscriptable container."""
    cr = ClassificationResult(
        result={"intent": "refund"},
        latency_ms=12.34,
        confidence={"intent": {"refund": 0.95, "other": 0.05}},
    )
    assert cr.result == {"intent": "refund"}
    assert cr.latency_ms == 12.34
    assert cr.confidence == {"intent": {"refund": 0.95, "other": 0.05}}
    assert cr["result"] == {"intent": "refund"}
    assert cr["latency_ms"] == 12.34
    assert cr["confidence"] == {"intent": {"refund": 0.95, "other": 0.05}}
    assert "result" in cr
    assert "latency_ms" in cr
    assert "confidence" in cr
    assert "other" not in cr
    assert cr.get("result") == {"intent": "refund"}
    assert cr.get("latency_ms") == 12.34
    assert cr.get("confidence") == {"intent": {"refund": 0.95, "other": 0.05}}
    assert cr.get("missing", 42) == 42

    with pytest.raises(KeyError):
        _ = cr["invalid"]


def test_multitask_classifier_prediction_mapping():
    """Verify MultiTaskClassifier maps extractor outputs to dictionary and records latency and confidence."""
    class MockExtractor:
        def extract(self, text, tasks):
            return {
                "intent": "replacement",
                "urgency": "critical",
            }

    classifier = MultiTaskClassifier(extractor=MockExtractor(), device=torch.device("cpu"))
    tasks_input = {
        "intent": ["refund", "replacement", "tracking", "general_inquiry"],
        "urgency": ["low", "normal", "critical"],
    }
    res = classifier.predict(
        text="My order arrived broken and I want a replacement immediately.",
        tasks=tasks_input,
    )

    assert isinstance(res, ClassificationResult)
    assert res.result["intent"] == "replacement"
    assert res.result["urgency"] == "critical"
    assert res["result"]["intent"] == "replacement"
    assert res.latency_ms >= 0.0

    # Verify confidence is populated for all candidates
    assert "intent" in res.confidence
    assert "urgency" in res.confidence
    assert set(res.confidence["intent"].keys()) == set(tasks_input["intent"])
    assert set(res.confidence["urgency"].keys()) == set(tasks_input["urgency"])
    assert res.confidence["intent"]["replacement"] == 1.0
    assert res.confidence["intent"]["refund"] == 0.0
    assert res.confidence["urgency"]["critical"] == 1.0


def test_multitask_classifier_complex_outputs():
    """Verify MultiTaskClassifier handles dict with 'label' key and list of dicts."""
    class ComplexExtractor:
        def extract(self, text, tasks):
            return {
                "intent": {"label": "billing", "score": 0.98},
                "priority": [{"label": "high", "score": 0.95}],
            }

    classifier = MultiTaskClassifier(extractor=ComplexExtractor(), device=torch.device("cpu"))
    res = classifier.predict(
        text="Need urgent billing support",
        tasks={
            "intent": ["billing", "general"],
            "priority": ["low", "high"],
        },
    )
    assert res.result["intent"] == "billing"
    assert res.result["priority"] == "high"


def test_multitask_classifier_fallback_to_candidate():
    """Verify fallback to candidate list when extractor returns no match for a task."""
    class EmptyExtractor:
        def extract(self, text, tasks):
            return {}

    classifier = MultiTaskClassifier(extractor=EmptyExtractor(), device=torch.device("cpu"))
    res = classifier.predict(
        text="Sample text",
        tasks={"category": ["billing", "support"], "empty_candidates": []},
    )
    assert res.result["category"] == "billing"
    assert res.result["empty_candidates"] == "unknown"


def test_multitask_classifier_empty_input():
    """Verify empty text or tasks returns early with zero latency."""
    classifier = MultiTaskClassifier(extractor=None, device=torch.device("cpu"))
    res_empty_text = classifier.predict(text="", tasks={"intent": ["test"]})
    assert res_empty_text.result == {}
    assert res_empty_text.latency_ms == 0.0

    res_empty_tasks = classifier.predict(text="some text", tasks={})
    assert res_empty_tasks.result == {}
    assert res_empty_tasks.latency_ms == 0.0


def test_multitask_classifier_error_wrapping():
    """Verify unhandled forward pass exceptions are wrapped in InferenceException."""
    class BrokenExtractor:
        def extract(self, text, tasks):
            raise ValueError("Tensor shape mismatch")

    classifier = MultiTaskClassifier(extractor=BrokenExtractor(), device=torch.device("cpu"))
    with pytest.raises(InferenceException, match="Model inference failed"):
        classifier.predict("sample", {"a": ["b"]})


def test_engine_state_registry():
    """Verify EngineState transitions and tracking of load time."""
    state = EngineState()
    assert state.is_loaded is False
    assert state.load_time_seconds == 0.0

    classifier = MultiTaskClassifier(extractor=None, device=torch.device("cpu"))
    state.set_ready(classifier, "cpu", load_time_seconds=1.234)

    assert state.is_loaded is True
    assert state.device_name == "cpu"
    assert state.classifier is classifier
    assert state.load_time_seconds == 1.234

    state.reset()
    assert state.is_loaded is False
    assert state.device_name == "unknown"
    assert state.classifier is None
    assert state.load_time_seconds == 0.0


@pytest.mark.asyncio
async def test_lifespan_lifecycle_success_and_teardown(monkeypatch):
    """Verify lifespan context manager initializes model, performs warmup, and resets on exit."""
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = {"intent": "support"}
    monkeypatch.setattr("decide.engine.lifecycle.load_gliner_model", lambda **kwargs: mock_extractor)

    app = FastAPI()
    state = get_engine_state()
    state.reset()

    assert state.is_loaded is False

    async with lifespan(app):
        assert state.is_loaded is True
        assert state.device_name in ("cpu", "cuda:0")
        assert state.load_time_seconds >= 0.0
        assert state.classifier is not None

    assert state.is_loaded is False
    assert state.classifier is None


@pytest.mark.asyncio
async def test_lifespan_lifecycle_failure_resilience(monkeypatch):
    """Verify lifespan does not crash app boot if model fails to load, but leaves is_loaded False."""
    def fail_load(**kwargs):
        raise RuntimeError("Weights corrupted")

    monkeypatch.setattr("decide.engine.lifecycle.load_gliner_model", fail_load)

    app = FastAPI()
    state = get_engine_state()
    state.reset()

    async with lifespan(app):
        assert state.is_loaded is False
        assert state.classifier is None

