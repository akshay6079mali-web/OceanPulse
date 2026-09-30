from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional
from oceanpulse.oceanpulse.pipeline import run_pipeline
from ..auth import get_current_user

router = APIRouter()

class AnalyzeRequest(BaseModel):
    sar_path: str
    ais_path: str
    wind_speed: float

@router.post("/api/v1/analyze", status_code=202)
async def analyze_endpoint(request: AnalyzeRequest, background_tasks: BackgroundTasks, current_user: str = Depends(get_current_user)):
    background_tasks.add_task(run_pipeline, request.sar_path, request.ais_path, request.wind_speed)
    return {"status": "Accepted", "message": "Analyzing SAR & backtracking..."}
