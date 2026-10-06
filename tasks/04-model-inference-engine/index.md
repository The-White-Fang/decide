# TASK-04: Model Execution Engine

## Overview
This task encompasses the integration, device orchestration, execution pipeline, and lifecycle management for Fastino’s `GLiNER2.5-Decide` model using PyTorch 2.x and `gliner2` (`AutoExtractor`).

## Module Architecture & Subtasks

| Subtask ID | Title | Target File | Description |
| :--- | :--- | :--- | :--- |
| **SUBTASK-4.1** | [Model Loader & Device Detection](file:///home/abhishek/decide/tasks/04-model-inference-engine/01-model-loader-and-device-detection.md) | `decide/engine/loader.py` | Load `fastino/GLiNER2.5-Decide` via `gliner2` `AutoExtractor`, offline weights caching, and GPU/CPU target resolution. |
| **SUBTASK-4.2** | [Multi-Task Inference Pipeline](file:///home/abhishek/decide/tasks/04-model-inference-engine/02-multi-task-inference-pipeline.md) | `decide/engine/classifier.py` | Single-pass classification under `torch.inference_mode()`, JSON schema conversion, latency measurement, error wrapping. |
| **SUBTASK-4.3** | [Engine Lifecycle & Warmup](file:///home/abhishek/decide/tasks/04-model-inference-engine/03-engine-lifecycle-and-warmup.md) | `decide/engine/lifecycle.py` | FastAPI lifespan startup handler, dummy inference warmup, readiness status reporting for `/health`. |

## Key Dependencies
- `torch>=2.0.0`
- `gliner2` (`AutoExtractor`)
- `transformers` / Hugging Face local cache

## Acceptance Criteria
- [x] Auto device detection properly picks `cuda:0` when CUDA is available and falls back to `cpu`.
- [x] Loads solely from local cache when `local_files_only=True` is configured for container offline execution.
- [x] Classification correctly maps multi-task labels in a single pass.
- [x] Engine readiness state is tracked and accessible to the health check endpoint.

