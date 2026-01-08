"""
Enhanced API routes for Custom Fork Cloning Pipeline operations.

This module provides REST API endpoints for the enhanced pipeline functionality
including custom Git repository support, flexible build steps, and build output management.

Author: Open WebUI Customizer Team
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from pathlib import Path

from app.models.database import get_db
from app.services.enhanced_pipeline_service import EnhancedPipelineService
from app.services.git_repository_service import GitRepositoryService
from app.models.models import PipelineRun, BuildOutput
from app.exceptions import (
    ValidationError, NotFoundError, DatabaseError,
    PipelineError, FileOperationError
)
from app.utils.logging import get_logger, log_function_call, log_api_request

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])

# Pydantic models for request/response
class PipelineRunResponse(BaseModel):
    id: int
    status: str
    steps_to_execute: List[str]
    git_repository_id: Optional[int] = None
    output_type: str
    registry_id: Optional[int] = None
    started_at: str
    completed_at: Optional[str] = None
    logs: str
    repository_info: Optional[Dict[str, Any]] = None
    build_outputs: Optional[List[Dict[str, Any]]] = None

class PipelineRunCreate(BaseModel):
    steps_to_execute: Optional[List[str]] = None
    git_repository_id: Optional[int] = None
    branding_template_id: Optional[int] = None
    configuration_id: Optional[int] = None
    output_type: str = "zip"
    registry_id: Optional[int] = None
    custom_parameters: Optional[Dict[str, Any]] = None

class ExecutionResult(BaseModel):
    success: bool
    message: str

class PipelineRunListResponse(BaseModel):
    success: bool
    runs: List[PipelineRunResponse]
    count: int

class PipelineRunResponseWrapper(BaseModel):
    success: bool
    pipeline_run: PipelineRunResponse

class ExecutionResponse(BaseModel):
    success: bool
    execution_result: ExecutionResult

class BuildOutputsResponse(BaseModel):
    success: bool
    build_outputs: List[Dict[str, Any]]
    count: int

class BuildStepResponse(BaseModel):
    success: bool
    build_steps: Dict[str, Any]
    count: int

class StatisticsResponse(BaseModel):
    success: bool
    statistics: Dict[str, Any]

class CleanupResponse(BaseModel):
    success: bool
    cleanup_result: Dict[str, Any]

class RepositoryUsageResponse(BaseModel):
    success: bool
    repository_usage: Dict[str, Any]

def get_enhanced_pipeline_service(db: Session) -> EnhancedPipelineService:
    """Get enhanced pipeline service instance."""
    return EnhancedPipelineService(db)

def _pipeline_run_to_response(
    run: PipelineRun, 
    db: Session,
    include_outputs: bool = False
) -> PipelineRunResponse:
    """Convert pipeline run model to response model."""
    response_data = PipelineRunResponse(
        id=run.id,  # type: ignore[arg-type]
        status=run.status,  # type: ignore[arg-type]
        steps_to_execute=run.steps_to_execute or [],  # type: ignore[arg-type]
        git_repository_id=run.git_repository_id,  # type: ignore[arg-type]
        output_type=run.output_type,  # type: ignore[arg-type]
        registry_id=run.registry_id,  # type: ignore[arg-type]
        started_at=run.started_at.isoformat(),  # type: ignore[arg-type]
        completed_at=run.completed_at.isoformat() if run.completed_at else None,  # type: ignore[arg-type]
        logs=run.logs or ""  # type: ignore[arg-type]
    )
    
    # Add repository info if available
    if run.git_repository_id:  # type: ignore[arg-type]
        try:
            git_service = GitRepositoryService(db)
            repo_info = git_service.get_repository_info(run.git_repository_id)  # type: ignore[arg-type]
            response_data.repository_info = repo_info
        except Exception as e:
            logger.warning(f"Failed to get repository info for run {run.id}: {str(e)}")
    
    # Add build outputs if requested
    if include_outputs:
        try:
            service = get_enhanced_pipeline_service(db)
            build_outputs = service._get_build_outputs(run)  # type: ignore[arg-type]
            # Convert BuildOutput objects to dictionaries
            outputs = [
                {
                    'id': output.id,  # type: ignore[arg-type]
                    'pipeline_run_id': output.pipeline_run_id,  # type: ignore[arg-type]
                    'output_type': output.output_type,  # type: ignore[arg-type]
                    'file_path': output.file_path,  # type: ignore[arg-type]
                    'image_url': output.image_url,  # type: ignore[arg-type]
                    'file_size_bytes': output.file_size_bytes,  # type: ignore[arg-type]
                    'checksum_sha256': output.checksum_sha256,  # type: ignore[arg-type]
                    'download_count': output.download_count,  # type: ignore[arg-type]
                    'expires_at': output.expires_at.isoformat() if output.expires_at else None,  # type: ignore[arg-type]
                    'created_at': output.created_at.isoformat()  # type: ignore[arg-type]
                }
                for output in build_outputs
            ]
            response_data.build_outputs = outputs
        except Exception as e:
            logger.warning(f"Failed to get build outputs for run {run.id}: {str(e)}")
            response_data.build_outputs = []
    
    return response_data

@router.get("/runs", response_model=PipelineRunListResponse)
@log_api_request
@log_function_call
def get_pipeline_runs(
    status: Optional[str] = Query(None),
    limit: Optional[int] = Query(None),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """
    Get all pipeline runs.
    
    Query Parameters:
        status (str): Filter by status (pending, running, completed, failed)
        limit (int): Maximum number of runs to return
        offset (int): Offset for pagination
    
    Returns:
        JSON array of pipeline run data
    """
    try:
        service = get_enhanced_pipeline_service(db)
        
        # Build query
        query = db.query(PipelineRun)
        
        if status:
            query = query.filter(PipelineRun.status == status)
        
        # Apply pagination
        if limit:
            query = query.offset(offset).limit(limit)
        
        runs = query.order_by(PipelineRun.started_at.desc()).all()
        
        result = [_pipeline_run_to_response(run, db) for run in runs]
        
        return PipelineRunListResponse(
            success=True,
            runs=result,
            count=len(result)
        )
        
    except Exception as e:
        logger.error(f"Error getting pipeline runs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/runs", response_model=PipelineRunResponseWrapper, status_code=201)
@log_api_request
@log_function_call
def create_pipeline_run(
    pipeline_data: PipelineRunCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new pipeline run with custom fork support.
    
    JSON Body:
        steps_to_execute (list): List of build steps to execute
        git_repository_id (int, optional): Custom Git repository ID
        branding_template_id (int, optional): Branding template ID
        configuration_id (int, optional): Configuration ID
        output_type (str): Output type ('zip', 'docker_image', 'both')
        registry_id (int, optional): Container registry ID
        custom_parameters (dict, optional): Additional custom parameters
    
    Returns:
        JSON of created pipeline run data
    """
    try:
        service = get_enhanced_pipeline_service(db)
        pipeline_run = service.create_pipeline_run(
            steps_to_execute=pipeline_data.steps_to_execute,
            git_repository_id=pipeline_data.git_repository_id,
            branding_template_id=pipeline_data.branding_template_id,
            configuration_id=pipeline_data.configuration_id,
            output_type=pipeline_data.output_type,
            registry_id=pipeline_data.registry_id,
            custom_parameters=pipeline_data.custom_parameters
        )
        
        response_data = _pipeline_run_to_response(pipeline_run, db)
        
        logger.info(f"Created enhanced pipeline run via API", extra={
            'pipeline_run_id': pipeline_run.id,
            'output_type': pipeline_data.output_type
        })
        
        return PipelineRunResponseWrapper(
            success=True,
            pipeline_run=response_data
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Database error creating pipeline run: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating pipeline run: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/runs/{run_id}", response_model=PipelineRunResponseWrapper)
@log_api_request
@log_function_call
def get_pipeline_run(
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific pipeline run.
    
    URL Parameters:
        run_id (int): Pipeline run ID
    
    Returns:
        JSON of pipeline run data
    """
    try:
        pipeline_run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        
        if not pipeline_run:
            raise NotFoundError(f"Pipeline run with ID {run_id} not found")
        
        response_data = _pipeline_run_to_response(pipeline_run, db, include_outputs=True)
        
        return PipelineRunResponseWrapper(
            success=True,
            pipeline_run=response_data
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting pipeline run: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/runs/{run_id}/execute", response_model=ExecutionResponse)
@log_api_request
@log_function_call
def execute_pipeline_run(
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Execute a pipeline run.
    
    URL Parameters:
        run_id (int): Pipeline run ID
    
    Returns:
        JSON with execution result
    """
    try:
        service = get_enhanced_pipeline_service(db)
        success, message = service.execute_pipeline_run(run_id)
        
        logger.info(f"Executed pipeline run via API", extra={
            'pipeline_run_id': run_id,
            'success': success
        })
        
        return ExecutionResponse(
            success=True,
            execution_result=ExecutionResult(
                success=success,
                message=message
            )
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationError, PipelineError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing pipeline run: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/runs/{run_id}/logs", response_class=PlainTextResponse)
@log_api_request
@log_function_call
def get_pipeline_logs(
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the logs for a pipeline run.
    
    URL Parameters:
        run_id (int): Pipeline run ID
    
    Returns:
        Plain text logs
    """
    try:
        service = get_enhanced_pipeline_service(db)
        logs = service.get_pipeline_logs(run_id)
        
        return logs
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting pipeline logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/runs/{run_id}/outputs", response_model=BuildOutputsResponse)
@log_api_request
@log_function_call
def get_build_outputs(
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all build outputs for a pipeline run.
    
    URL Parameters:
        run_id (int): Pipeline run ID
    
    Returns:
        JSON array of build output data
    """
    try:
        service = get_enhanced_pipeline_service(db)
        # Use the internal method since get_build_outputs is private
        pipeline_run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
        if not pipeline_run:
            raise NotFoundError(f"Pipeline run with ID {run_id} not found")
        build_outputs = service._get_build_outputs(pipeline_run)
        # Convert BuildOutput objects to dictionaries
        outputs = [
            {
                'id': output.id,  # type: ignore[arg-type]
                'pipeline_run_id': output.pipeline_run_id,  # type: ignore[arg-type]
                'output_type': output.output_type,  # type: ignore[arg-type]
                'file_path': output.file_path,  # type: ignore[arg-type]
                'image_url': output.image_url,  # type: ignore[arg-type]
                'file_size_bytes': output.file_size_bytes,  # type: ignore[arg-type]
                'checksum_sha256': output.checksum_sha256,  # type: ignore[arg-type]
                'download_count': output.download_count,  # type: ignore[arg-type]
                'expires_at': output.expires_at.isoformat() if output.expires_at else None,  # type: ignore[arg-type]
                'created_at': output.created_at.isoformat()  # type: ignore[arg-type]
            }
            for output in build_outputs
        ]
        
        return BuildOutputsResponse(
            success=True,
            build_outputs=outputs,
            count=len(outputs)
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting build outputs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/outputs/{output_id}/download")
@log_api_request
@log_function_call
def download_build_output(
    output_id: int,
    db: Session = Depends(get_db)
):
    """
    Download a build output file.
    
    URL Parameters:
        output_id (int): Build output ID
    
    Returns:
        File download
    """
    try:
        service = get_enhanced_pipeline_service(db)
        file_path = service.download_build_output(output_id)
        
        # Get output info for filename
        output = db.query(BuildOutput).filter(BuildOutput.id == output_id).first()
        if not output:
            raise NotFoundError(f"Build output with ID {output_id} not found")
        
        filename = f"build_output_{output_id}.zip"
        
        return FileResponse(
            path=Path(file_path),
            filename=filename,
            media_type='application/zip'
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationError, FileOperationError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error downloading build output: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/steps", response_model=BuildStepResponse)
@log_api_request
@log_function_call
def get_available_build_steps(
    db: Session = Depends(get_db)
):
    """
    Get information about all available build steps.
    
    Returns:
        JSON array of build step information
    """
    try:
        service = get_enhanced_pipeline_service(db)
        steps = service.AVAILABLE_BUILD_STEPS
        
        return BuildStepResponse(
            success=True,
            build_steps=steps,
            count=len(steps)
        )
        
    except Exception as e:
        logger.error(f"Error getting build steps: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics", response_model=StatisticsResponse)
@log_api_request
@log_function_call
def get_pipeline_statistics(
    days: int = Query(30),
    db: Session = Depends(get_db)
):
    """
    Get pipeline execution statistics.
    
    Query Parameters:
        days (int): Number of days to look back for statistics (default: 30)
    
    Returns:
        JSON with pipeline statistics
    """
    try:
        service = get_enhanced_pipeline_service(db)
        statistics = service.get_pipeline_statistics(days)
        
        return StatisticsResponse(
            success=True,
            statistics=statistics
        )
        
    except Exception as e:
        logger.error(f"Error getting pipeline statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cleanup", response_model=CleanupResponse)
@log_api_request
@log_function_call
def cleanup_expired_outputs(
    db: Session = Depends(get_db)
):
    """
    Clean up expired build outputs.
    
    This endpoint should be called periodically to remove old build artifacts.
    
    Returns:
        JSON with cleanup statistics
    """
    try:
        service = get_enhanced_pipeline_service(db)
        result = service.cleanup_expired_outputs()
        
        logger.info(f"Completed cleanup of expired outputs", extra=result)
        
        return CleanupResponse(
            success=True,
            cleanup_result=result
        )
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/repositories/{repository_id}/usage", response_model=RepositoryUsageResponse)
@log_api_request
@log_function_call
def get_repository_usage(
    repository_id: int,
    db: Session = Depends(get_db)
):
    """
    Get usage statistics for a specific Git repository.
    
    URL Parameters:
        repository_id (int): Repository ID to analyze
    
    Returns:
        JSON with repository usage statistics
    """
    try:
        service = get_enhanced_pipeline_service(db)
        usage = service.get_repository_usage(repository_id)
        
        return RepositoryUsageResponse(
            success=True,
            repository_usage=usage
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting repository usage: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))