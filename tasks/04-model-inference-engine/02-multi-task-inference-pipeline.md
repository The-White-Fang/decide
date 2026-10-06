# SUBTASK-4.2: Multi-Task Inference Pipeline

## Parent Task
[TASK-04: Model Execution Engine](file:///home/abhishek/decide/tasks/04-model-inference-engine/index.md)

## Target Code Path
`decide/engine/classifier.py`

## Objective
Implement single-pass multi-task classification using `gliner2` extractor, extracting optimal label predictions for each requested task category, measuring inference latency, and structuring output responses.

## Functional Requirements
1. **Multi-Task Extraction Execution (PRD Section 1 & 7.2):**
   - Execute inference inside `torch.inference_mode()`.
   - Pass input text and task schemas (e.g. `{"intent": ["refund", "replacement"], "urgency": ["low", "critical"]}`).
   - Handle extraction logic of `AutoExtractor` to resolve the highest confidence classification label per task.
2. **Output Formatting:**
   - Format results into dictionary mapping task names to selected labels:
     ```json
     {
       "result": {
         "intent": "replacement",
         "urgency": "critical"
       }
     }
     ```
3. **Latency Benchmarking & Timing:**
   - High-precision timing (`time.perf_counter()`) to track pure model inference time in milliseconds.
   - Attach latency metadata (utilized by playground and performance loggers).
4. **Exception Handling:**
   - Catch PyTorch / tokenization errors; wrap in domain-specific `InferenceException` to allow REST controller to return clean HTTP 500 error messages.

## Interface & Schema
```python
from dataclasses import dataclass
from typing import Any

@dataclass
class ClassificationResult:
    result: dict[str, str]
    latency_ms: float

class MultiTaskClassifier:
    def __init__(self, model: Any, device: torch.device):
        self.model = model
        self.device = device

    def predict(self, text: str, tasks: dict[str, list[str]]) -> ClassificationResult:
        """
        Executes single-pass multi-task classification.
        Returns mapped predictions and measured latency in ms.
        """
        ...
```

## Acceptance Criteria
- [x] Returns exact matching task keys with predicted labels.
- [x] Operates inside `torch.inference_mode()` with no gradient tracking overhead.
- [x] Latency is computed and reported in milliseconds.
- [x] Cleanly raises `InferenceException` on tokenization or shape mismatches without crashing Uvicorn.

