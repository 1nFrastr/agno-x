"""Human-in-the-Loop Confirmation with AGUI Protocol

This example demonstrates how to use human-in-the-loop confirmation with the AGUI protocol.
When a tool requires confirmation, the agent will pause execution and wait for user approval
before proceeding with the tool call.

The AGUI protocol handles the pause/resume flow:
1. Agent encounters a tool marked with requires_confirmation=True
2. Agent pauses and emits a StateSnapshotEvent with status "paused_for_confirmation"
3. AGUI client can present the tool call to the user for approval
4. User approves/modifies the tool call
5. Client continues the run by sending back the updated state with confirmed tools
6. Agent resumes execution with the confirmed tools

Run `pip install openai agno` to install dependencies.
"""

from agno.agent.agent import Agent
from agno.models.openai import OpenAIChat
from agno.os import AgentOS
from agno.os.interfaces.agui import AGUI
from agno.tools import tool
from agno.db.sqlite import SqliteDb

import os
os.environ["OPENAI_API_KEY"] = "hk-8lze3v36h734mq6ckgqw2hvs7ej8tjdc7abume6sbe2ki5rt"
os.environ["OPENAI_BASE_URL"] = "https://api.openai-hk.com/v1"

@tool(requires_confirmation=True)
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to the specified recipient.
    
    Args:
        to: Email address of the recipient
        subject: Subject line of the email
        body: Body content of the email
        
    Returns:
        str: Confirmation message
    """
    return f"Email sent to {to} with subject '{subject}'"


@tool(requires_confirmation=True)
def delete_file(filename: str) -> str:
    """Delete a file from the system.
    
    Args:
        filename: Name of the file to delete
        
    Returns:
        str: Confirmation message
    """
    return f"File '{filename}' has been deleted"


@tool
def get_weather(city: str) -> str:
    """Get the weather for a city.
    
    This is a safe operation that does not require confirmation.
    
    Args:
        city: Name of the city
        
    Returns:
        str: Weather information
    """
    return f"It is currently 70 degrees and sunny in {city}"


# Create a database for storing agent runs
# This is required for human-in-the-loop confirmation to work properly
db = SqliteDb(db_file="tmp/agent_runs.db")

# Create an agent with tools that require confirmation
assistant = Agent(
    name="Assistant",
    model=OpenAIChat(id="gpt-4o"),
    instructions=(
        "You are a helpful AI assistant. "
        "When the user asks you to perform an operation, directly call the appropriate tool. "
        "Do NOT ask for confirmation - the system will handle that automatically. "
        "Just call the tool with the provided parameters."
    ),
    tools=[send_email, delete_file, get_weather],
    add_datetime_to_context=True,
    markdown=True,
    db=db,  # Required for pausing and resuming runs
)

# Setup your AgentOS app with AGUI interface
agent_os = AgentOS(
    agents=[assistant],
    interfaces=[AGUI(agent=assistant)],
)
app = agent_os.get_app()


if __name__ == "__main__":
    """Run your AgentOS with human-in-the-loop confirmation support.

    You can see the configuration and available apps at:
    http://localhost:9002/config

    To test the human-in-the-loop confirmation:
    1. Start the server: python human_in_the_loop_confirmation.py
    2. Open the AGUI interface in your browser
    3. Ask the agent to send an email or delete a file
    4. The agent will pause and show you the tool call for confirmation
    5. Approve or reject the tool call
    6. The agent will continue with your decision

    Example prompts:
    - "Send an email to john@example.com with subject 'Meeting Tomorrow' and body 'Let's meet at 10 AM'"
    - "Delete the file named 'old_report.pdf'"
    - "What's the weather in Tokyo?" (this won't require confirmation)
    
    
    Testing with curl:
    ==================
    
    Step 1: Send a request that requires confirmation (will pause and return STATE_SNAPSHOT):
    
    curl -X POST http://localhost:9002/agui \
      -H "Content-Type: application/json" \
      -d '{
        "thread_id": "test_thread_1",
        "run_id": "test_run_1",
        "messages": [{
          "id": "msg_1",
          "role": "user",
          "content": "Send an email to alice@example.com with subject Hello and body World"
        }],
        "state": {},
        "tools": [],
        "context": [],
        "forwarded_props": {}
      }'
    
    Expected response will include:
    data: {"type":"STATE_SNAPSHOT","snapshot":{"status":"paused_for_confirmation","tools_to_confirm":[...]}}
    
    
    Step 2: Confirm and continue execution (extract tool_call_id from Step 1 response):
    
    curl -X POST http://localhost:9002/agui \
      -H "Content-Type: application/json" \
      -d '{
        "thread_id": "test_thread_1",
        "run_id": "test_run_1",
        "state": {
          "status": "paused_for_confirmation",
          "tools_to_confirm": [{
            "tool_call_id": "<tool_call_id_from_step_1>",
            "tool_name": "send_email",
            "tool_args": {"to": "alice@example.com", "subject": "Hello", "body": "World"},
            "requires_confirmation": true,
            "confirmed": true
          }]
        },
        "messages": [],
        "tools": [],
        "context": [],
        "forwarded_props": {}
      }'
    
    
    KNOWN LIMITATIONS:
    ==================
    
    1. Database persistence in streaming mode:
       - When using agent.arun() with stream=True (as AGUI does), the run state may not be 
         fully persisted to the database before the pause event is emitted
       - This causes "No runs found for run ID" error when trying to continue the run
       
    2. Workaround for full testing:
       - Use agent.run() (non-streaming) for the initial request to ensure DB persistence
       - Then use AGUI's continue endpoint for resuming with confirmed tools
       - See test_continue_run.py for a working example of this approach
    
    3. LLM behavior considerations:
       - The agent instructions must explicitly tell the LLM to call tools directly
       - Phrases like "requires user confirmation" in tool descriptions may cause the LLM
         to ask for confirmation instead of calling the tool
       - Current instructions are optimized to ensure tool calls are made immediately
    
    4. For production use:
       - Consider implementing a background task to ensure run persistence
       - Or use non-streaming initial calls with streaming only for continuation
       - The AGUI protocol itself works correctly; the issue is in the persistence layer
    """
    agent_os.serve(app="human_in_the_loop_confirmation:app", reload=True, port=9002)
