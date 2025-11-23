"""Test script for human-in-the-loop confirmation with AGUI protocol

This script tests the AGUI protocol integration with human-in-the-loop confirmation
without starting a full server. It simulates the flow of:
1. Starting a run with a tool that requires confirmation
2. Agent pauses and generates StateSnapshotEvent
3. User confirms the tool
4. Continue the run with confirmed tools

Run `pip install openai agno` to install dependencies.
"""

import asyncio
import json
import tempfile

from agno.agent.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools import tool
from ag_ui.core import RunAgentInput, EventType
from agno.os.interfaces.agui.router import run_agent
from agno.db.sqlite import SqliteDb


import os
os.environ["OPENAI_API_KEY"] = "hk-8lze3v36h734mq6ckgqw2hvs7ej8tjdc7abume6sbe2ki5rt"
os.environ["OPENAI_BASE_URL"] = "https://api.openai-hk.com/v1"


@tool(requires_confirmation=True)
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to the specified recipient."""
    return f"Email sent to {to} with subject '{subject}'"


@tool
def get_weather(city: str) -> str:
    """Get the weather for a city."""
    return f"It is currently 70 degrees and sunny in {city}"


async def test_human_in_the_loop_confirmation():
    """Test the human-in-the-loop confirmation flow with AGUI."""
    
    print("=" * 80)
    print("Testing Human-in-the-Loop Confirmation with AGUI Protocol")
    print("=" * 80)
    
    # Create a temporary database for testing
    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db = SqliteDb(db_file=db_file.name)
    
    # Create an agent with a tool that requires confirmation
    agent = Agent(
        name="TestAgent",
        model=OpenAIChat(id="gpt-4o-mini"),
        instructions="You are a helpful assistant. Be concise.",
        tools=[send_email, get_weather],
        markdown=True,
        db=db,
    )
    
    # Test 1: Run with a tool that requires confirmation
    print("\n" + "=" * 80)
    print("Test 1: Initial run - tool requires confirmation")
    print("=" * 80)
    
    run_input = RunAgentInput(
        thread_id="test_thread_1",
        run_id="test_run_1",
        state={},
        messages=[
            {
                "id": "msg_1",
                "role": "user",
                "content": "Send an email to john@example.com with subject 'Test' and body 'Hello World'"
            }
        ],
        tools=[],
        context=[],
        forwarded_props={}
    )
    
    state_snapshot = None
    run_id = None
    
    async for event in run_agent(agent, run_input):
        print(f"\nEvent Type: {event.type}")
        
        if event.type == EventType.STATE_SNAPSHOT:
            print(f"State Snapshot: {json.dumps(event.snapshot, indent=2)}")
            state_snapshot = event.snapshot
            run_id = run_input.run_id
            
            # Check if we have the expected paused state
            assert state_snapshot.get("status") == "paused_for_confirmation", \
                "Expected status to be 'paused_for_confirmation'"
            assert "tools_to_confirm" in state_snapshot, \
                "Expected 'tools_to_confirm' in snapshot"
            assert len(state_snapshot["tools_to_confirm"]) > 0, \
                "Expected at least one tool to confirm"
            
            print("\n✓ Successfully received StateSnapshotEvent with paused_for_confirmation status")
            break
        elif event.type == EventType.RUN_STARTED:
            print(f"Run started: thread_id={event.thread_id}, run_id={event.run_id}")
        elif event.type == EventType.TEXT_MESSAGE_CONTENT:
            print(f"Content: {event.delta}", end="")
        elif event.type == EventType.RUN_FINISHED:
            print(f"Run finished: thread_id={event.thread_id}, run_id={event.run_id}")
    
    if state_snapshot is None:
        print("\n✗ Failed: Did not receive StateSnapshotEvent")
        return
    
    # Test 2: Continue the run with confirmed tools
    print("\n" + "=" * 80)
    print("Test 2: Continue run - user confirms the tool")
    print("=" * 80)
    
    # Mark the tool as confirmed
    tools_to_confirm = state_snapshot["tools_to_confirm"]
    tools_to_confirm[0]["confirmed"] = True
    
    # Create a new run input with the confirmed state
    continue_input = RunAgentInput(
        thread_id="test_thread_1",
        run_id=run_id,
        state={
            "status": "paused_for_confirmation",
            "tools_to_confirm": tools_to_confirm
        },
        messages=[],
        tools=[],
        context=[],
        forwarded_props={}
    )
    
    print(f"\nContinuing run with confirmed tools...")
    
    received_result = False
    async for event in run_agent(agent, continue_input):
        print(f"\nEvent Type: {event.type}")
        
        if event.type == EventType.TEXT_MESSAGE_CONTENT:
            print(f"Content: {event.delta}", end="")
        elif event.type == EventType.TOOL_CALL_RESULT:
            print(f"Tool Result: {event.content}")
            received_result = True
        elif event.type == EventType.RUN_FINISHED:
            print(f"\nRun finished: thread_id={event.thread_id}, run_id={event.run_id}")
    
    if received_result:
        print("\n✓ Successfully continued run and executed confirmed tool")
    else:
        print("\n✗ Failed: Did not receive tool result")
    
    # Test 3: Run with a tool that does NOT require confirmation
    print("\n" + "=" * 80)
    print("Test 3: Run with tool that does NOT require confirmation")
    print("=" * 80)
    
    run_input_no_confirm = RunAgentInput(
        thread_id="test_thread_2",
        run_id="test_run_2",
        state={},
        messages=[
            {
                "id": "msg_2",
                "role": "user",
                "content": "What's the weather in Tokyo?"
            }
        ],
        tools=[],
        context=[],
        forwarded_props={}
    )
    
    received_state_snapshot = False
    received_run_finished = False
    
    async for event in run_agent(agent, run_input_no_confirm):
        if event.type == EventType.STATE_SNAPSHOT:
            received_state_snapshot = True
            print(f"\n✗ Unexpected StateSnapshotEvent for tool without confirmation")
        elif event.type == EventType.TEXT_MESSAGE_CONTENT:
            print(f"{event.delta}", end="")
        elif event.type == EventType.RUN_FINISHED:
            received_run_finished = True
    
    if not received_state_snapshot and received_run_finished:
        print("\n✓ Tool without confirmation executed directly without pause")
    else:
        print("\n✗ Failed: Unexpected behavior for tool without confirmation")
    
    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_human_in_the_loop_confirmation())
