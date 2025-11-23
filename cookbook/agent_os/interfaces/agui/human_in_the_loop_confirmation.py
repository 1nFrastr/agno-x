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


@tool(requires_confirmation=True)
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to the specified recipient.
    
    This is a sensitive operation that requires user confirmation.
    
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
    
    This is a destructive operation that requires user confirmation.
    
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


# Create an agent with tools that require confirmation
assistant = Agent(
    name="Assistant",
    model=OpenAIChat(id="gpt-4o"),
    instructions=(
        "You are a helpful AI assistant. "
        "When you need to perform sensitive operations like sending emails or deleting files, "
        "you should use the appropriate tools. "
        "Be concise in your responses."
    ),
    tools=[send_email, delete_file, get_weather],
    add_datetime_to_context=True,
    markdown=True,
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
    """
    agent_os.serve(app="human_in_the_loop_confirmation:app", reload=True, port=9002)
