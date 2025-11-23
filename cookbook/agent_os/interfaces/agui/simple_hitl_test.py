"""Simplified test for human-in-the-loop confirmation

This script tests the core HITL functionality without requiring the full AgentOS setup.
It directly tests the agent's pause/continue behavior.

Run this from the repository root:
    cd D:/work/agno-framework/agno
    python cookbook/agent_os/interfaces/agui/simple_hitl_test.py

Or install agno in your environment:
    pip install -e libs/agno
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


@tool
def get_weather(city: str) -> str:
    """Get the weather for a city."""
    return f"It is currently 70 degrees and sunny in {city}"


def test_basic_confirmation():
    """Test basic tool confirmation without AGUI protocol."""
    
    print("=" * 80)
    print("Test 1: Basic Tool Confirmation Flow")
    print("=" * 80)
    
    # Create agent with tool requiring confirmation (with database for session persistence)
    agent = Agent(
        name="TestAgent",
        model=OpenAIChat(id="gpt-4o-mini"),
        instructions="You are a helpful assistant. Be concise.",
        tools=[send_email, get_weather],
        markdown=True,
        db=db,
    )
    
    print("\nSending request to send email (requires confirmation)...")
    response = agent.run(
        "Send an email to john@example.com with subject 'Test' and body 'Hello World'"
    )
    
    # Check if the run is paused
    print(f"\nRun paused: {response.is_paused}")
    if response.is_paused:
        print("✓ Agent correctly paused for confirmation")
        
        # Check the tools
        if response.tools and len(response.tools) > 0:
            tool = response.tools[0]
            print(f"\nTool requiring confirmation:")
            print(f"  - Name: {tool.tool_name}")
            print(f"  - Args: {tool.tool_args}")
            print(f"  - Requires confirmation: {tool.requires_confirmation}")
            
            # Mark as confirmed
            print("\nUser confirms the tool...")
            tool.confirmed = True
            
            # Continue the run
            print("\nContinuing the run with confirmed tool...")
            response = agent.continue_run(response)
            
            if not response.is_paused:
                print("✓ Run continued successfully")
                if response.tools and response.tools[0].result:
                    print(f"✓ Tool executed with result: {response.tools[0].result}")
                else:
                    print("✗ Tool did not execute")
            else:
                print("✗ Run is still paused")
        else:
            print("✗ No tools found in paused run")
    else:
        print("✗ Agent did not pause as expected")
    
    print("\n" + "=" * 80)
    print("Test 2: Tool Without Confirmation")
    print("=" * 80)
    
    print("\nSending request for weather (no confirmation needed)...")
    response = agent.run("What's the weather in Tokyo?")
    
    if not response.is_paused:
        print("✓ Agent executed directly without pause")
        if "Tokyo" in str(response.content):
            print("✓ Got weather response")
    else:
        print("✗ Agent paused unexpectedly")
    
    print("\n" + "=" * 80)
    print("Test 3: Streaming with Confirmation")
    print("=" * 80)
    
    print("\nSending streaming request with confirmation...")
    session_id = "test_session_stream"
    paused_response = None
    for response in agent.run(
        "Send an email to jane@example.com with subject 'Meeting' and body 'See you tomorrow'",
        session_id=session_id,
        stream=True,
        stream_events=True
    ):
        if response.is_paused:
            print("\n✓ Received paused event in stream")
            paused_response = response
            break
    
    if paused_response and paused_response.tools:
        print("✓ Got tools to confirm in streaming mode")
        paused_response.tools[0].confirmed = True
        
        print("\nContinuing stream with confirmed tool...")
        completed = False
        for response in agent.continue_run(
            run_id=paused_response.run_id,
            updated_tools=paused_response.tools,
            session_id=session_id,
            stream=True,
            stream_events=True
        ):
            event_type = response.event if hasattr(response, 'event') else type(response).__name__
            # Check for tool completion
            if event_type == 'ToolCallCompleted':
                print(f"[OK] Tool executed successfully")
                completed = True
                break
        
        if completed:
            print("✓ Streaming continuation successful")
        else:
            print("✗ Streaming continuation failed")
    else:
        print("✗ Did not get paused response in stream")
    
    print("\n" + "=" * 80)
    print("All Tests Completed!")
    print("=" * 80)


if __name__ == "__main__":
    test_basic_confirmation()
