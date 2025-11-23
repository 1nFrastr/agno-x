# Human-in-the-Loop Confirmation with AGUI Protocol

This directory contains examples and tests for human-in-the-loop (HITL) confirmation functionality integrated with the AGUI protocol.

## Overview

The AGUI protocol now supports pausing agent execution to request user confirmation before executing sensitive tools. This is based on [PR #4085](https://github.com/agno-agi/agno/pull/4085) and has been adapted to work with the latest version of the Agno framework.

## How It Works

### 1. Tool Marking
Tools can be marked as requiring confirmation:

```python
@tool(requires_confirmation=True)
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email - requires user confirmation."""
    return f"Email sent to {to}"
```

### 2. Pause Flow
When an agent encounters a tool requiring confirmation:
- The agent pauses execution
- A `StateSnapshotEvent` is emitted with:
  - `status`: `"paused_for_confirmation"`
  - `tools_to_confirm`: List of tools awaiting confirmation
- The run does NOT emit `RunFinishedEvent`

### 3. Continue Flow
To continue a paused run:
- Mark tools as confirmed: `tool["confirmed"] = True`
- Send a new request with the updated state:
  ```python
  RunAgentInput(
      thread_id=original_thread_id,
      run_id=original_run_id,
      state={
          "status": "paused_for_confirmation",
          "tools_to_confirm": confirmed_tools
      }
  )
  ```
- The router detects the paused state and calls `agent.acontinue_run()`

## Examples

### Full Server Example
`human_in_the_loop_confirmation.py` - Complete AGUI server with HITL support
- Demonstrates email sending and file deletion with confirmation
- Shows safe operations that don't require confirmation
- Run with: `python human_in_the_loop_confirmation.py`
- Access at: http://localhost:9002

### Test Script
`test_hitl_confirmation.py` - Automated test of HITL flow
- Tests the complete pause/resume cycle
- Validates StateSnapshotEvent generation
- Tests both confirmed and non-confirmed tools
- Run with: `python test_hitl_confirmation.py`

## Implementation Details

### Changes Made

1. **Router (`libs/agno/agno/os/interfaces/agui/router.py`)**
   - Added detection of `paused_for_confirmation` state in `RunAgentInput.state`
   - Calls `agent.acontinue_run()` when resuming from paused state
   - Passes updated tools from state to continue execution

2. **Utils (`libs/agno/agno/os/interfaces/agui/utils.py`)**
   - Added `StateSnapshotEvent` import
   - Modified `_create_completion_events()` to detect tools requiring confirmation
   - Generates `StateSnapshotEvent` instead of `RunFinishedEvent` when paused
   - Returns early to prevent normal completion flow

### Key Differences from Original PR

The original PR #4085 was proposed several months ago. This adaptation accounts for:
- Updated AGUI protocol event types
- Current agent execution flow with `stream_events=True`
- Modern `acontinue_run()` API
- Current event streaming architecture

## Testing

### Manual Testing
1. Start the server: `python human_in_the_loop_confirmation.py`
2. Open AGUI interface in browser
3. Request a sensitive operation: "Send an email to test@example.com"
4. Observe the pause and confirmation request
5. Approve or modify the tool call
6. Observe the execution completion

### Automated Testing
```bash
python test_hitl_confirmation.py
```

Expected output:
- ✓ StateSnapshotEvent received with correct status
- ✓ Tool confirmation and continuation works
- ✓ Non-confirmed tools execute directly

## Architecture

```
User Request
    ↓
AGUI Router (run_agent)
    ↓
Agent.arun() → Tool requires confirmation
    ↓
RunPausedEvent emitted
    ↓
Utils detects requires_confirmation=True
    ↓
StateSnapshotEvent generated
    ↓
Client receives snapshot, shows to user
    ↓
User approves/modifies tools
    ↓
Client sends continue request with state
    ↓
Router detects paused_for_confirmation state
    ↓
Agent.acontinue_run(updated_tools)
    ↓
Execution continues with confirmed tools
    ↓
Normal completion flow
```

## Requirements

- agno >= 0.6.0
- ag_ui >= 0.1.0
- openai (or other LLM provider)

## Related Documentation

- [Agno Tools Documentation](https://docs.agno.ai/tools)
- [AG-UI Protocol](https://docs.ag-ui.com/concepts/state#human-in-the-loop-collaboration)
- [Original PR #4085](https://github.com/agno-agi/agno/pull/4085)
