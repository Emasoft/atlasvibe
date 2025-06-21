#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# CHANGELOG:
# - Initial implementation of workflow queues API endpoints
# - Provides clean interface for frontend to interact with WorkflowQueueCoordinator
# - Includes proper Pydantic models for type safety
# - Returns immediately for enqueue operations
# - Comprehensive error handling and logging
#

from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, validator

from captain.services.workflow_changes_queue import ChangeType
from captain.models.workflow_queue import TopologyRequest
from captain.utils.logger import logger

router = APIRouter(prefix="/workflow-queues", tags=["workflow-queues"])


# Request/Response Models


class EnqueueChangeRequest(BaseModel):
    """Request model for enqueueing a workflow change."""

    type: ChangeType = Field(..., description="Type of change to enqueue")
    block_id: str = Field(..., description="ID of the block being changed")
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Change-specific data"
    )

    @validator("type", pre=True)
    def validate_type(cls, v):
        if isinstance(v, str):
            try:
                return ChangeType(v)
            except ValueError:
                valid_types = [ct.value for ct in ChangeType]
                raise ValueError(f"Invalid change type. Must be one of: {valid_types}")
        return v

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "type": "code_update",
                "block_id": "ADDITION_1",
                "data": {"code": "def ADDITION_1(x, y):\n    return x + y"},
            }
        }


class EnqueueChangeResponse(BaseModel):
    """Response model for enqueue operations."""

    change_id: str = Field(..., description="Unique ID of the enqueued change")
    queue_status: Dict[str, Any] = Field(
        ..., description="Current status of both queues"
    )


class SetTopologyRequest(BaseModel):
    """Request model for setting workflow topology."""

    job_id: str = Field(..., description="Unique job identifier")
    name: str = Field(..., description="Name of the workflow")
    graph: Dict[str, List[Dict[str, Any]]] = Field(
        ..., description="Workflow graph with nodes and edges"
    )
    run_config: Dict[str, Any] = Field(
        default_factory=dict, description="Execution configuration"
    )
    project_path: Optional[str] = Field(None, description="Path to project directory")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job_123",
                "name": "My Workflow",
                "graph": {
                    "nodes": [
                        {"id": "INPUT_1", "type": "INPUT"},
                        {"id": "ADDITION_1", "type": "ADDITION"},
                        {"id": "OUTPUT_1", "type": "OUTPUT"},
                    ],
                    "edges": [
                        {"source": "INPUT_1", "target": "ADDITION_1"},
                        {"source": "ADDITION_1", "target": "OUTPUT_1"},
                    ],
                },
                "run_config": {
                    "nodeDelay": 0.1,
                    "maximumRuntime": 300,
                    "maximumConcurrentWorkers": 4,
                },
                "project_path": "/path/to/project",
            }
        }


class QueueStatusResponse(BaseModel):
    """Response model for queue status."""

    coordinator: Dict[str, Any] = Field(..., description="Coordinator status and stats")
    wcq: Dict[str, Any] = Field(..., description="Workflow Changes Queue status")
    weq: Dict[str, Any] = Field(..., description="Workflow Execution Queue status")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ExecutionOutputsResponse(BaseModel):
    """Response model for execution outputs."""

    execution_id: Optional[str] = Field(None, description="ID of the last execution")
    outputs: Optional[Dict[str, Any]] = Field(
        None, description="Node outputs from last execution"
    )
    differences: Optional[Dict[str, Any]] = Field(
        None, description="Differences from previous execution"
    )
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


# Convenience request models for specific change types


class UpdateCodeRequest(BaseModel):
    """Request model for updating block code."""

    block_id: str
    code: str

    class Config:
        json_schema_extra = {
            "example": {
                "block_id": "ADDITION_1",
                "code": "def ADDITION_1(x, y):\n    return x + y + 1  # Modified",
            }
        }


class UpdateMetadataRequest(BaseModel):
    """Request model for updating block metadata."""

    block_id: str
    metadata: Dict[str, Any]


class RenameBlockRequest(BaseModel):
    """Request model for renaming a block."""

    old_block_id: str
    new_block_id: str


class UpdateConnectionsRequest(BaseModel):
    """Request model for updating block connections."""

    block_id: str
    connections: Dict[str, Any]


class UpdateParametersRequest(BaseModel):
    """Request model for updating block parameters."""

    block_id: str
    parameters: Dict[str, Any]


# API Endpoints


@router.post("/enqueue", response_model=EnqueueChangeResponse)
async def enqueue_change(request: EnqueueChangeRequest, req: Request):
    """
    Enqueue a workflow change for processing.

    Returns immediately with a change ID. The change will be processed
    asynchronously by the WorkflowChangesQueue (WCQ).

    WebSocket events emitted:
    - coordinator_change_enqueued: When change is added to queue
    - wcq_processing_started: When change processing begins
    - wcq_change_processed: When change processing completes
    - coordinator_execution_triggered: When workflow re-execution starts
    """
    try:
        coordinator = req.app.state.workflow_coordinator

        # Convert request to change dict
        change = {
            "type": request.type.value,
            "block_id": request.block_id,
            "data": request.data,
        }

        # Enqueue the change
        change_id = await coordinator.enqueue_change(change)

        # Get current status
        status = coordinator.get_status()

        logger.info(
            f"Enqueued change {change_id}: {request.type.value} for {request.block_id}"
        )

        return EnqueueChangeResponse(change_id=change_id, queue_status=status)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error enqueueing change: {e}")
        raise HTTPException(status_code=500, detail="Failed to enqueue change")


@router.get("/status", response_model=QueueStatusResponse)
async def get_queue_status(req: Request):
    """
    Get current status of both workflow queues.

    Returns status information for:
    - Coordinator: Overall state and statistics
    - WCQ: Changes queue with pending/processing items
    - WEQ: Execution queue with current execution state
    """
    try:
        coordinator = req.app.state.workflow_coordinator
        status = coordinator.get_status()

        return QueueStatusResponse(
            coordinator=status["coordinator"], wcq=status["wcq"], weq=status["weq"]
        )

    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get queue status")


@router.post("/topology")
async def set_topology(request: SetTopologyRequest, req: Request):
    """
    Set the current workflow topology for execution.

    This should be called whenever the workflow structure changes.
    The topology will be used for all subsequent executions until updated.

    WebSocket events emitted:
    - coordinator_topology_updated: When topology is set
    """
    try:
        coordinator = req.app.state.workflow_coordinator

        # Create TopologyRequest object
        topology = TopologyRequest(
            job_id=request.job_id,
            name=request.name,
            graph=request.graph,
            project_path=request.project_path,
        )

        # Set the topology
        coordinator.set_topology(topology)

        logger.info(f"Set topology for job {request.job_id}")

        return {
            "message": "Topology set successfully",
            "job_id": request.job_id,
            "node_count": len(request.graph.get("nodes", [])),
            "edge_count": len(request.graph.get("edges", [])),
        }

    except Exception as e:
        logger.error(f"Error setting topology: {e}")
        raise HTTPException(status_code=500, detail="Failed to set topology")


@router.get("/outputs", response_model=ExecutionOutputsResponse)
async def get_execution_outputs(req: Request):
    """
    Get outputs from the last workflow execution.

    Returns:
    - Last execution outputs by node
    - Differences from previous execution (if available)
    """
    try:
        coordinator = req.app.state.workflow_coordinator

        # Get detailed status including outputs
        status = await coordinator.get_detailed_status()

        response = ExecutionOutputsResponse()

        if "last_execution" in status:
            response.execution_id = status["last_execution"].get("execution_id")
            response.outputs = status["last_execution"].get("outputs")

            # Get differences if available
            # Note: This would require tracking previous outputs separately
            # For now, differences are computed when changes are applied

        return response

    except Exception as e:
        logger.error(f"Error getting execution outputs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get execution outputs")


@router.post("/cancel")
async def cancel_execution(req: Request):
    """
    Cancel the current workflow execution.

    Only affects the Workflow Execution Queue (WEQ).
    Changes in WCQ will continue processing.

    WebSocket events emitted:
    - weq_execution_cancelled: When execution is cancelled
    """
    try:
        coordinator = req.app.state.workflow_coordinator

        # Cancel current execution
        coordinator.weq.cancel()

        logger.info("Cancelled workflow execution")

        return {
            "message": "Execution cancelled",
            "weq_status": coordinator.weq.get_status(),
        }

    except Exception as e:
        logger.error(f"Error cancelling execution: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel execution")


# Convenience endpoints for common change types


@router.post("/update-code")
async def update_block_code(request: UpdateCodeRequest, req: Request):
    """
    Update code for a specific block.

    Convenience endpoint that wraps the generic enqueue endpoint.
    """
    try:
        coordinator = req.app.state.workflow_coordinator
        change_id = await coordinator.update_block_code(request.block_id, request.code)

        return {
            "change_id": change_id,
            "message": f"Code update enqueued for {request.block_id}",
        }

    except Exception as e:
        logger.error(f"Error updating block code: {e}")
        raise HTTPException(status_code=500, detail="Failed to update block code")


@router.post("/regenerate-manifest/{block_id}")
async def regenerate_manifest(block_id: str, req: Request):
    """
    Regenerate manifest for a specific block.

    Convenience endpoint for triggering manifest regeneration.
    """
    try:
        coordinator = req.app.state.workflow_coordinator
        change_id = await coordinator.regenerate_manifest(block_id)

        return {
            "change_id": change_id,
            "message": f"Manifest regeneration enqueued for {block_id}",
        }

    except Exception as e:
        logger.error(f"Error regenerating manifest: {e}")
        raise HTTPException(status_code=500, detail="Failed to regenerate manifest")


@router.post("/update-metadata")
async def update_block_metadata(request: UpdateMetadataRequest, req: Request):
    """Update metadata for a specific block."""
    try:
        coordinator = req.app.state.workflow_coordinator
        change_id = await coordinator.update_metadata(
            request.block_id, request.metadata
        )

        return {
            "change_id": change_id,
            "message": f"Metadata update enqueued for {request.block_id}",
        }

    except Exception as e:
        logger.error(f"Error updating metadata: {e}")
        raise HTTPException(status_code=500, detail="Failed to update metadata")


@router.post("/rename-block")
async def rename_block(request: RenameBlockRequest, req: Request):
    """Rename a block."""
    try:
        coordinator = req.app.state.workflow_coordinator
        change_id = await coordinator.rename_block(
            request.old_block_id, request.new_block_id
        )

        return {
            "change_id": change_id,
            "message": f"Block rename enqueued: {request.old_block_id} -> {request.new_block_id}",
        }

    except Exception as e:
        logger.error(f"Error renaming block: {e}")
        raise HTTPException(status_code=500, detail="Failed to rename block")


@router.post("/update-connections")
async def update_connections(request: UpdateConnectionsRequest, req: Request):
    """Update connections for a specific block."""
    try:
        coordinator = req.app.state.workflow_coordinator
        change_id = await coordinator.update_connections(
            request.block_id, request.connections
        )

        return {
            "change_id": change_id,
            "message": f"Connection update enqueued for {request.block_id}",
        }

    except Exception as e:
        logger.error(f"Error updating connections: {e}")
        raise HTTPException(status_code=500, detail="Failed to update connections")


@router.post("/update-parameters")
async def update_parameters(request: UpdateParametersRequest, req: Request):
    """Update parameters for a specific block."""
    try:
        coordinator = req.app.state.workflow_coordinator
        change_id = await coordinator.update_parameters(
            request.block_id, request.parameters
        )

        return {
            "change_id": change_id,
            "message": f"Parameter update enqueued for {request.block_id}",
        }

    except Exception as e:
        logger.error(f"Error updating parameters: {e}")
        raise HTTPException(status_code=500, detail="Failed to update parameters")


# WebSocket Event Documentation
"""
WebSocket Events Reference:

From WorkflowChangesQueue (WCQ):
- wcq_change_enqueued: When a change is added to the queue
  {type: "wcq_change_enqueued", change_id: str, change_type: str, queue_length: int}

- wcq_processing_started: When change processing begins
  {type: "wcq_processing_started", change_id: str, change_type: str}

- wcq_change_processed: When change processing completes
  {type: "wcq_change_processed", change_id: str, duration_ms: float, success: bool}

- wcq_error: When an error occurs processing a change
  {type: "wcq_error", change_id: str, error: str}

From WorkflowExecutionQueue (WEQ):
- weq_execution_started: When workflow execution begins
  {type: "weq_execution_started", job_id: str, execution_id: str}

- weq_block_started: When a block starts executing
  {type: "weq_block_started", block_id: str, execution_id: str}

- weq_block_completed: When a block finishes executing
  {type: "weq_block_completed", block_id: str, execution_id: str, success: bool}

- weq_execution_completed: When entire workflow finishes
  {type: "weq_execution_completed", job_id: str, execution_id: str, duration_ms: float}

- weq_execution_cancelled: When execution is cancelled
  {type: "weq_execution_cancelled", job_id: str, reason: str}

From WorkflowQueueCoordinator:
- coordinator_change_enqueued: When change is enqueued via coordinator
  {type: "coordinator_change_enqueued", change_id: str, wcq_status: dict, weq_status: dict}

- coordinator_topology_updated: When topology is set/updated
  {type: "coordinator_topology_updated", job_id: str, node_count: int, edge_count: int}

- coordinator_execution_triggered: When execution is triggered after changes
  {type: "coordinator_execution_triggered", job_id: str, trigger_reason: str}

- coordinator_output_differences: When outputs differ from previous execution
  {type: "coordinator_output_differences", job_id: str, differences: dict}
"""
