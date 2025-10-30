from sqlalchemy.orm import Session
from app.models import models
import json

class DashboardService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_dashboard_data(self):
        """Get dashboard data including pipeline status and build history"""
        # Get latest pipeline run
        latest_run = self.db.query(models.PipelineRun).order_by(
            models.PipelineRun.start_time.desc()
        ).first()
        
        # Get build history (last 10 runs)
        build_history = self.db.query(models.PipelineRun).order_by(
            models.PipelineRun.start_time.desc()
        ).limit(10).all()
        
        # Get active template
        active_template = self.db.query(models.BrandingTemplate).first()
        
        return {
            "status": "active" if latest_run and latest_run.status == "running" else "idle",
            "latest_build": latest_run,
            "build_history": build_history,
            "active_template": active_template
        }
    
    def get_performance_metrics(self):
        """Get performance metrics for builds"""
        # Get all pipeline runs
        all_runs = self.db.query(models.PipelineRun).all()
        
        if not all_runs:
            return {
                "average_build_time": 0,
                "success_rate": 0,
                "total_builds": 0
            }
        
        total_builds = len(all_runs)
        
        # Calculate success rate
        successful_runs = [run for run in all_runs if run.status == "completed"]
        success_rate = len(successful_runs) / total_builds * 100
        
        # Calculate average build time
        total_time = 0
        completed_runs_with_time = 0
        
        for run in successful_runs:
            if run.start_time and run.end_time:
                build_time = (run.end_time - run.start_time).total_seconds()
                total_time += build_time
                completed_runs_with_time += 1
        
        average_build_time = total_time / completed_runs_with_time if completed_runs_with_time > 0 else 0
        
        return {
            "average_build_time": average_build_time,
            "success_rate": success_rate,
            "total_builds": total_builds
        }