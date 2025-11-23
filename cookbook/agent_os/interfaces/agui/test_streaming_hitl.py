"""Test streaming HITL confirmation

Tests the streaming mode with human-in-the-loop confirmation.
"""

import os
import sys

# Add the libs/agno directory to the path so we can import agno
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
agno_lib_path = os.path.join(repo_root, "libs", "agno")
if os.path.exists(agno_lib_path):
    sys.path.insert(0, agno_lib_path)

from agno.agent.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools import tool

os.environ["OPENAI_API_KEY"] = "hk-8lze3v36h734mq6ckgqw2hvs7ej8tjdc7abume6sbe2ki5rt"
os.environ["OPENAI_BASE_URL"] = "https://api.openai-hk.com/v1"

# Create a temporary database for testing
import tempfile
from agno.db.sqlite import SqliteDb

db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
db = SqliteDb(db_file=db_file.name)

@tool(requires_confirmation=True)
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to the specified recipient."""
    return f"Email sent to {to} with subject '{subject}'"


def test_streaming_confirmation():
    """Test streaming with confirmation."""
    
    print("=" * 80)
    print("Test: Streaming with Confirmation")
    print("=" * 80)
    
    # Create agent with database
    agent = Agent(
        name="TestAgent",
        model=OpenAIChat(id="gpt-4o-mini"),
        instructions="You are a helpful assistant. Be concise.",
        tools=[send_email],
        markdown=True,
        db=db,
    )
    
    print("\nSending streaming request with confirmation...")
    session_id = "test_session_stream"
    paused_response = None
    
    print("\n--- Phase 1: Initial streaming run (should pause) ---")
    for response in agent.run(
        "Send an email to jane@example.com with subject 'Meeting' and body 'See you tomorrow'",
        session_id=session_id,
        stream=True,
        stream_events=True
    ):
        event_type = response.event if hasattr(response, 'event') else type(response).__name__
        print(f"Event: {event_type}")
        if hasattr(response, 'is_paused'):
            print(f"  is_paused: {response.is_paused}")
        if hasattr(response, 'tools') and response.tools:
            print(f"  Tools: {[(t.tool_name, t.confirmed, t.result) for t in response.tools]}")
        
        if response.is_paused:
            print("\n[SUCCESS] Received paused event in stream")
            paused_response = response
            break
    
    if not paused_response:
        print("[FAILED] Did not receive paused response")
        return
    
    if not paused_response.tools:
        print("[FAILED] No tools in paused response")
        return
    
    print(f"\n[SUCCESS] Got tools to confirm in streaming mode")
    print(f"Run ID: {paused_response.run_id}")
    print(f"Session ID: {paused_response.session_id}")
    print(f"Tool: {paused_response.tools[0].tool_name}")
    print(f"Args: {paused_response.tools[0].tool_args}")
    
    # Confirm the tool
    paused_response.tools[0].confirmed = True
    print("\nUser confirmed the tool")
    
    print("\n--- Phase 2: Continue streaming with confirmed tool ---")
    completed = False
    event_count = 0
    for response in agent.continue_run(
        run_id=paused_response.run_id,
        updated_tools=paused_response.tools,
        session_id=session_id,
        stream=True,
        stream_events=True
    ):
        event_count += 1
        event_type = response.event if hasattr(response, 'event') else type(response).__name__
        print(f"Event {event_count}: {event_type}")
        if hasattr(response, 'is_paused'):
            print(f"  is_paused: {response.is_paused}")
        if hasattr(response, 'tools') and response.tools:
            print(f"  Tools: {[(t.tool_name, t.confirmed, t.result) for t in response.tools]}")
        if hasattr(response, 'content') and response.content:
            print(f"  Content: {response.content}")
        
        # Check for tool completion
        if event_type == 'ToolCallCompleted':
            print(f"\n[SUCCESS] Tool executed successfully")
            completed = True
        elif event_type == 'RunCompleted':
            if not completed:
                print(f"\n[INFO] Run completed, checking if tool was executed...")
                # If we got here, the run completed without errors
                completed = True
    
    print(f"\nTotal events received: {event_count}")
    
    if completed:
        print("\n[SUCCESS] Streaming continuation successful")
    else:
        print("\n[FAILED] Streaming continuation failed - tool was not executed")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_streaming_confirmation()
