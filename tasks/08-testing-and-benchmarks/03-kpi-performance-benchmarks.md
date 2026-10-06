# SUBTASK-8.3: KPI Performance Benchmarks

## Parent Task
[TASK-08: Testing, Quality Assurance & Benchmarks](file:///home/abhishek/decide/tasks/08-testing-and-benchmarks/index.md)

## Target Code Path
`tests/benchmarks/`

## Objective
Implement automated latency and throughput benchmark scripts to systematically verify all Key Performance Indicators (KPIs) set forth in PRD Section 2.2.

## Functional Requirements
1. **P95 Latency Benchmark (`benchmark_latency.py`):**
   - Execute 100 sequential single-pass requests using the PRD standard payload:
     - Text: `"My order arrived broken and I want a replacement immediately."`
     - Tasks: `intent` (4 labels), `urgency` (3 labels)
   - Measure request response latency at client and pure inference inside server.
   - Calculate Mean, P50, P90, P95, and P99 latency.
   - Assert:
     - CPU execution: P95 < 150 ms (on modern 4-core x86_64 CPU).
     - GPU execution: P95 < 35 ms (on NVIDIA T4/L4 GPU).
2. **Auth Lookup Overhead Benchmark (`benchmark_auth.py`):**
   - Execute 1,000 auth check calls with valid API keys.
   - Profile the time spent in `verify_api_key()` (SHA-256 calculation + in-memory cache / SQLite indexed lookup).
   - Assert: Average auth lookup overhead < 1.0 ms (PRD Section 2.2 target).
3. **Container Readiness & Startup Benchmark (`benchmark_readiness.sh`):**
   - Trigger container startup (`docker run` or application boot).
   - Poll `GET /health` every 100ms.
   - Calculate elapsed time until HTTP 200 OK with `model_loaded: true` is received.
   - Assert: Container Readiness < 12 seconds.

## Interface & Schema
```python
import time
import numpy as np
from decide.auth.api_key import APIKeyCache
from decide.crypto import hash_api_key

def test_auth_lookup_overhead_benchmark(client, active_key_secret):
    latencies = []
    headers = {"X-API-Key": active_key_secret}
    # Pre-warm cache
    client.post("/predict", headers=headers, json={"text": "ping", "tasks": {"t": ["a"]}})

    for _ in range(500):
        t0 = time.perf_counter()
        resp = client.post("/predict", headers=headers, json={"text": "ping", "tasks": {"t": ["a"]}})
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000)

    p95 = np.percentile(latencies, 95)
    print(f"P95 Total Response Latency: {p95:.2f} ms")
```

## Acceptance Criteria
- [x] P95 latency is rigorously tracked and reported against PRD thresholds.
- [x] Auth lookup overhead is proven to be strictly under 1 millisecond.
- [x] Benchmark scripts output machine-readable JSON summaries for CI/CD pipelines.

