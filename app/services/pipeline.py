from sqlalchemy.orm import Session
from app.models.models import PipelineRun
from app.schemas.branding import PipelineRunCreate, PipelineRunUpdate
from typing import List, Optional
from datetime import datetime

def get_pipeline_run(db: Session, run_id: int) -> Optional[PipelineRun]:
    return db.query(PipelineRun).filter(PipelineRun.id == run_id).first()

def get_latest_pipeline_run(db: Session) -> Optional[PipelineRun]:
    return db.query(PipelineRun).order_by(PipelineRun.id.desc()).first()

def get_all_pipeline_runs(db: Session) -> List[PipelineRun]:
    return db.query(PipelineRun).all()

def create_pipeline_run(db: Session, run: PipelineRunCreate) -> PipelineRun:
    db_run = PipelineRun(
        status=run.status,
        steps_to_execute=run.steps_to_execute,
        logs=run.logs,
        started_at=datetime.utcnow()
    )
    db.add(db_run)
    db.commit()
    db.refresh(db_run)
    return db_run

def update_pipeline_run(db: Session, run_id: int, run: PipelineRunUpdate) -> Optional[PipelineRun]:
    db_run = get_pipeline_run(db, run_id)
    if db_run:
        update_data = run.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_run, key, value)
        # Update completed_at if status is completed or failed
        if run.status in ["completed", "failed"] and db_run.completed_at is None:
            db_run.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(db_run)
    return db_run

def delete_pipeline_run(db: Session, run_id: int) -> bool:
    db_run = get_pipeline_run(db, run_id)
    if db_run:
        db.delete(db_run)
        db.commit()
        return True
    return False

def append_pipeline_logs(db: Session, run_id: int, new_logs: str) -> Optional[PipelineRun]:
    db_run = get_pipeline_run(db, run_id)
    if db_run:
        if db_run.logs:
            db_run.logs += new_logs
        else:
            db_run.logs = new_logs
        db.commit()
        db.refresh(db_run)
    return db_run