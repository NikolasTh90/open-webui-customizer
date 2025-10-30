from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.schemas.branding import PipelineRun, PipelineRunCreate, PipelineRunUpdate
from app.services.pipeline import (
    get_pipeline_run, get_latest_pipeline_run, get_all_pipeline_runs,
    create_pipeline_run, update_pipeline_run, delete_pipeline_run,
    append_pipeline_logs
)
from typing import List, Optional
import os
import subprocess
from datetime import datetime

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])

@router.get("/runs", response_model=List[PipelineRun])
def read_all_pipeline_runs(db: Session = Depends(get_db)):
    return get_all_pipeline_runs(db)

@router.get("/runs/{run_id}", response_model=PipelineRun)
def read_pipeline_run(run_id: int, db: Session = Depends(get_db)):
    db_run = get_pipeline_run(db, run_id)
    if db_run is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return db_run

@router.get("/runs/latest", response_model=Optional[PipelineRun])
def read_latest_pipeline_run(db: Session = Depends(get_db)):
    return get_latest_pipeline_run(db)

@router.post("/runs", response_model=PipelineRun)
def create_new_pipeline_run(run: PipelineRunCreate, db: Session = Depends(get_db)):
    return create_pipeline_run(db, run)

@router.put("/runs/{run_id}", response_model=PipelineRun)
def update_existing_pipeline_run(run_id: int, run: PipelineRunUpdate, db: Session = Depends(get_db)):
    db_run = update_pipeline_run(db, run_id, run)
    if db_run is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return db_run

@router.delete("/runs/{run_id}")
def delete_existing_pipeline_run(run_id: int, db: Session = Depends(get_db)):
    success = delete_pipeline_run(db, run_id)
    if not success:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return {"message": "Pipeline run deleted successfully"}

@router.post("/execute")
def execute_pipeline_steps(
    steps: List[str],
    template_id: int,
    registry_id: int,
    db: Session = Depends(get_db)
):
    # Create a new pipeline run
    run = PipelineRunCreate(
        status="running",
        steps_to_execute=steps,
        logs=f"Pipeline started at {datetime.utcnow()}\n"
    )
    db_run = create_pipeline_run(db, run)
    
    # Execute each step
    for step in steps:
        try:
            if step == "clone":
                # Execute clone step
                result = subprocess.run(["make", "source"], capture_output=True, text=True, cwd=".")
                logs = f"Clone step completed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\n"
            elif step == "build":
                # Execute build step
                result = subprocess.run(["make", "build"], capture_output=True, text=True, cwd=".")
                logs = f"Build step completed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\n"
            elif step == "publish":
                # Execute publish step
                result = subprocess.run(["make", "publish"], capture_output=True, text=True, cwd=".")
                logs = f"Publish step completed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\n"
            elif step == "clean":
                # Execute clean step
                result = subprocess.run(["make", "clean"], capture_output=True, text=True, cwd=".")
                logs = f"Clean step completed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\n"
            else:
                logs = f"Unknown step: {step}\n"
            
            # Append logs to the pipeline run
            append_pipeline_logs(db, db_run.id, logs)
        except Exception as e:
            # Update run status to failed
            update_pipeline_run(db, db_run.id, PipelineRunUpdate(status="failed"))
            raise HTTPException(status_code=500, detail=f"Error executing step {step}: {str(e)}")
    
    # Update run status to completed
    update_pipeline_run(db, db_run.id, PipelineRunUpdate(status="completed"))
    
    return {"message": "Pipeline executed successfully", "run_id": db_run.id}

@router.get("/logs/{run_id}")
def get_pipeline_logs(run_id: int, db: Session = Depends(get_db)):
    db_run = get_pipeline_run(db, run_id)
    if db_run is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return {"logs": db_run.logs}