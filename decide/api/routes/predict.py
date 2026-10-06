"""Secured multi-task intent classification endpoint."""

from typing import Dict
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from pydantic import BaseModel
from decide.auth.api_key import verify_api_key
from decide.auth.guardrails import PredictInputSchema
from decide.db.models import APIKey
from decide.engine.lifecycle import get_engine_state

router = APIRouter()


class PredictResponse(BaseModel):
    result: Dict[str, str]


@router.post("/predict", response_model=PredictResponse)
def predict_intent(
    payload: PredictInputSchema,
    background_tasks: BackgroundTasks,
    current_key: APIKey = Depends(verify_api_key),
) -> PredictResponse:
    """
    Executes single-pass multi-task classification.
    Protected by X-API-Key header.
    """
    state = get_engine_state()
    if not state.is_loaded or state.classifier is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Model is not loaded or engine is uninitialized",
        )

    try:
        prediction_output = state.classifier.predict(payload.text, payload.tasks)
        return PredictResponse(result=prediction_output["result"])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model inference failed: {str(e)}",
        )
