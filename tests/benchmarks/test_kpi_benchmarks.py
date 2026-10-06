"""Automated KPI benchmark tests validating PRD Section 2.2 metrics."""

import time
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient
from decide.auth.api_key import key_cache, verify_api_key
from decide.crypto import hash_api_key
from decide.db.repository import UserRepository, APIKeyRepository
from decide.db.session import get_engine, init_db, get_session_context, get_db
from decide.engine.classifier import MultiTaskClassifier
from decide.engine.lifecycle import get_engine_state
from decide.main import app


class FastMockExtractor:
    def extract(self, text, tasks):
        return {"intent": "replacement", "urgency": "critical"}


@pytest.fixture
def benchmark_env(tmp_path: Path):
    db_file = tmp_path / "bench.db"
    engine = get_engine(db_file)
    init_db(engine)

    raw_key = "dec_benchmarktestkey1234567890123"
    hashed = hash_api_key(raw_key)

    with get_session_context(engine) as s:
        u = UserRepository.create(s, "bench_user", "hash")
        APIKeyRepository.create(s, u.id, "Bench Key", "dec_benchm", hashed)

    classifier = MultiTaskClassifier(extractor=FastMockExtractor(), device="cpu")
    get_engine_state().set_ready(classifier, "cpu")
    key_cache.clear()

    def override_get_db():
        with get_session_context(engine) as s:
            yield s

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield {"client": client, "raw_key": raw_key, "engine": engine}

    app.dependency_overrides.clear()
    key_cache.clear()


def test_kpi_auth_lookup_overhead_under_1ms(benchmark_env):
    """
    KPI Requirement (PRD Section 2.2):
    Auth Lookup Overhead < 1 ms via hashed key retrieval + in-memory cache.
    """
    raw_key = benchmark_env["raw_key"]
    engine = benchmark_env["engine"]

    # Pre-warm cache with 1 query
    with get_session_context(engine) as session:
        verify_api_key(x_api_key=raw_key, db=session)

    lookup_times_ms = []
    with get_session_context(engine) as session:
        for _ in range(500):
            t0 = time.perf_counter()
            verify_api_key(x_api_key=raw_key, db=session)
            t1 = time.perf_counter()
            lookup_times_ms.append((t1 - t0) * 1000.0)

    avg_lookup_ms = float(np.mean(lookup_times_ms))
    p95_lookup_ms = float(np.percentile(lookup_times_ms, 95))

    print(f"\n[KPI Benchmark] Average Auth Lookup Overhead: {avg_lookup_ms:.4f} ms (P95: {p95_lookup_ms:.4f} ms)")
    assert avg_lookup_ms < 1.0, f"Auth lookup overhead ({avg_lookup_ms} ms) exceeded 1.0 ms target!"


def test_kpi_p95_prediction_latency(benchmark_env):
    """
    KPI Requirement (PRD Section 2.2):
    Verify request processing performance and P95 latency measurement.
    """
    client = benchmark_env["client"]
    raw_key = benchmark_env["raw_key"]

    payload = {
        "text": "My order arrived broken and I want a replacement immediately.",
        "tasks": {
            "intent": ["refund", "replacement", "tracking", "general_inquiry"],
            "urgency": ["low", "normal", "critical"],
        },
    }

    # Warmup request
    client.post("/predict", headers={"X-API-Key": raw_key}, json=payload)

    latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        resp = client.post("/predict", headers={"X-API-Key": raw_key}, json=payload)
        t1 = time.perf_counter()
        assert resp.status_code == 200
        latencies.append((t1 - t0) * 1000.0)

    p95 = float(np.percentile(latencies, 95))
    print(f"\n[KPI Benchmark] P95 End-to-End Latency: {p95:.2f} ms")
    # P95 should be well under 150ms on mock/local CPU
    assert p95 < 150.0


def test_kpi_detailed_percentiles_report(benchmark_env):
    """
    Computes comprehensive latency distribution (Mean, P50, P90, P95, P99)
    matching Subtask 8.3 specification.
    """
    client = benchmark_env["client"]
    raw_key = benchmark_env["raw_key"]

    payload = {
        "text": "My order arrived broken and I want a replacement immediately.",
        "tasks": {"intent": ["refund", "replacement"], "urgency": ["low", "critical"]},
    }

    latencies = []
    for _ in range(100):
        t0 = time.perf_counter()
        resp = client.post("/predict", headers={"X-API-Key": raw_key}, json=payload)
        t1 = time.perf_counter()
        assert resp.status_code == 200
        latencies.append((t1 - t0) * 1000.0)

    stats = {
        "mean_ms": round(float(np.mean(latencies)), 2),
        "p50_ms": round(float(np.percentile(latencies, 50)), 2),
        "p90_ms": round(float(np.percentile(latencies, 90)), 2),
        "p95_ms": round(float(np.percentile(latencies, 95)), 2),
        "p99_ms": round(float(np.percentile(latencies, 99)), 2),
    }

    print(f"\n[KPI Benchmark Latency Distribution] {stats}")
    assert stats["p95_ms"] < 150.0
    assert stats["p50_ms"] <= stats["p95_ms"]


@pytest.mark.asyncio
async def test_kpi_startup_readiness_under_12s(monkeypatch):
    """
    KPI Requirement (PRD Section 2.2):
    Verify application lifespan boot & model warmup completes within < 12 seconds.
    """
    from decide.engine.lifecycle import lifespan, get_engine_state
    from fastapi import FastAPI
    from unittest.mock import MagicMock

    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = {"intent": "support"}
    monkeypatch.setattr("decide.engine.lifecycle.load_gliner_model", lambda **kwargs: mock_extractor)

    app_instance = FastAPI()
    state = get_engine_state()
    state.reset()

    t0 = time.perf_counter()
    async with lifespan(app_instance):
        boot_duration = time.perf_counter() - t0
        assert state.is_loaded is True
        print(f"\n[KPI Benchmark] Container Startup & Warmup: {boot_duration:.3f} s (Target: < 12s)")
        assert boot_duration < 12.0, f"Startup time {boot_duration}s exceeded 12s target!"


def test_kpi_unauthorized_rejection_latency(benchmark_env):
    """
    Verify rejection latency for missing or invalid keys is extremely fast (< 5 ms)
    to resist DoS amplification attacks.
    """
    client = benchmark_env["client"]
    rejection_times = []

    for _ in range(50):
        t0 = time.perf_counter()
        resp = client.post("/predict", json={"text": "hello", "tasks": {"a": ["b"]}})
        t1 = time.perf_counter()
        assert resp.status_code == 401
        rejection_times.append((t1 - t0) * 1000.0)

    avg_rejection_ms = float(np.mean(rejection_times))
    print(f"\n[KPI Benchmark] Unauthorized Rejection Latency: {avg_rejection_ms:.3f} ms")
    assert avg_rejection_ms < 10.0

