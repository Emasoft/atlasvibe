# Workflow Queues API Documentation

## Overview

The Workflow Queues API provides a clean interface for the frontend to interact with the WorkflowQueueCoordinator, which manages two separate queues:

1. **Workflow Changes Queue (WCQ)** - Processes code updates, manifest regeneration, and other block changes
2. **Workflow Execution Queue (WEQ)** - Executes the workflow topology with the latest changes

## Base URL

All endpoints are prefixed with `/workflow-queues`.

## Core Endpoints

### 1. Enqueue Change

**POST** `/workflow-queues/enqueue`

Enqueue a workflow change for processing. Returns immediately (milliseconds).

**Request Body:**

```json
{
  "type": "code_update", // ChangeType enum
  "block_id": "ADDITION_1",
  "data": {
    "code": "def ADDITION_1(x, y):\n    return x + y"
  }
}
```

**Response:**

```json
{
  "change_id": "change_123abc",
  "queue_status": {
    "coordinator": {...},
    "wcq": {...},
    "weq": {...}
  }
}
```

**Change Types:**

- `code_update` - Update block code
- `manifest_regen` - Regenerate block manifest
- `metadata_update` - Update block metadata
- `block_rename` - Rename a block
- `connection_change` - Update block connections
- `parameter_update` - Update block parameters

### 2. Get Queue Status

**GET** `/workflow-queues/status`

Get current status of both workflow queues.

**Response:**

```json
{
  "coordinator": {
    "running": true,
    "has_topology": true,
    "pending_execution": false,
    "stats": {
      "coordinator_started": "2025-06-20T19:00:00Z",
      "topology_updates": 5,
      "execution_triggers": 10,
      "execution_cancellations": 2
    }
  },
  "wcq": {
    "is_processing": false,
    "queue_length": 0,
    "current_change": null,
    "total_processed": 15,
    "stats": {...}
  },
  "weq": {
    "is_running": false,
    "execution_id": null,
    "current_job": null,
    "stats": {...}
  },
  "timestamp": "2025-06-20T19:00:00Z"
}
```

### 3. Set Topology

**POST** `/workflow-queues/topology`

Set the current workflow topology for execution.

**Request Body:**

```json
{
  "job_id": "job_123",
  "name": "My Workflow",
  "graph": {
    "nodes": [
      { "id": "INPUT_1", "type": "INPUT" },
      { "id": "ADDITION_1", "type": "ADDITION" },
      { "id": "OUTPUT_1", "type": "OUTPUT" }
    ],
    "edges": [
      { "source": "INPUT_1", "target": "ADDITION_1" },
      { "source": "ADDITION_1", "target": "OUTPUT_1" }
    ]
  },
  "run_config": {
    "nodeDelay": 0.1,
    "maximumRuntime": 300,
    "maximumConcurrentWorkers": 4
  },
  "project_path": "/path/to/project"
}
```

### 4. Get Execution Outputs

**GET** `/workflow-queues/outputs`

Get outputs from the last workflow execution.

**Response:**

```json
{
  "execution_id": "exec_456def",
  "outputs": {
    "ADDITION_1": {"result": 5},
    "OUTPUT_1": {"displayed": true}
  },
  "differences": {
    "changed_nodes": ["ADDITION_1"],
    "details": {...}
  },
  "timestamp": "2025-06-20T19:00:00Z"
}
```

### 5. Cancel Execution

**POST** `/workflow-queues/cancel`

Cancel the current workflow execution.

**Response:**

```json
{
  "message": "Execution cancelled",
  "weq_status": {...}
}
```

## Convenience Endpoints

### Update Block Code

**POST** `/workflow-queues/update-code`

```json
{
  "block_id": "ADDITION_1",
  "code": "def ADDITION_1(x, y):\n    return x + y + 1"
}
```

### Regenerate Manifest

**POST** `/workflow-queues/regenerate-manifest/{block_id}`

### Update Metadata

**POST** `/workflow-queues/update-metadata`

```json
{
  "block_id": "ADDITION_1",
  "metadata": { "description": "Adds two numbers" }
}
```

### Rename Block

**POST** `/workflow-queues/rename-block`

```json
{
  "old_block_id": "ADDITION_1",
  "new_block_id": "ADD_NUMBERS_1"
}
```

### Update Connections

**POST** `/workflow-queues/update-connections`

```json
{
  "block_id": "ADDITION_1",
  "connections": {...}
}
```

### Update Parameters

**POST** `/workflow-queues/update-parameters`

```json
{
  "block_id": "ADDITION_1",
  "parameters": { "default_value": 0 }
}
```

## WebSocket Events

The system broadcasts various events via WebSocket for real-time status updates:

### From WCQ:

- `wcq_change_enqueued` - When a change is added to the queue
- `wcq_processing_started` - When change processing begins
- `wcq_change_processed` - When change processing completes
- `wcq_error` - When an error occurs processing a change

### From WEQ:

- `weq_execution_started` - When workflow execution begins
- `weq_block_started` - When a block starts executing
- `weq_block_completed` - When a block finishes executing
- `weq_execution_completed` - When entire workflow finishes
- `weq_execution_cancelled` - When execution is cancelled

### From Coordinator:

- `coordinator_change_enqueued` - When change is enqueued via coordinator
- `coordinator_topology_updated` - When topology is set/updated
- `coordinator_execution_triggered` - When execution is triggered after changes
- `coordinator_output_differences` - When outputs differ from previous execution

## Error Handling

All endpoints return standard HTTP status codes:

- `200` - Success
- `400` - Bad Request (invalid input)
- `500` - Internal Server Error

Error responses include a `detail` field with the error message.

## Usage Example

```javascript
// 1. Set the workflow topology
await fetch('/workflow-queues/topology', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    job_id: 'job_123',
    name: 'My Workflow',
    graph: {...},
    project_path: '/path/to/project'
  })
});

// 2. Update block code
const response = await fetch('/workflow-queues/update-code', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    block_id: 'ADDITION_1',
    code: 'def ADDITION_1(x, y):\n    return x + y + 1'
  })
});

const {change_id} = await response.json();

// 3. Listen for WebSocket events
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'wcq_change_processed' && data.change_id === change_id) {
    console.log('Code update completed!');
  }
  if (data.type === 'weq_execution_completed') {
    // Fetch the results
    fetch('/workflow-queues/outputs')
      .then(res => res.json())
      .then(outputs => console.log('Results:', outputs));
  }
};
```
