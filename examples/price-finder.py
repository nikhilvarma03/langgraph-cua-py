"""
Price Finder: A LangGraph workflow that routes user requests to either a general response
or a Computer Use Agent (CUA) for web-based price lookups.
"""

from typing import List, Literal

from dotenv import load_dotenv
from langchain_core.messages import AnyMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from langgraph_cua import create_cua
from langgraph_cua.types import CUAState
from langgraph_cua.report import CUAReportGenerator

# Load environment variables from .env file
load_dotenv()


def print_clean_update(update):
    """Print a clean, readable summary of the update without base64 image data."""
    if isinstance(update, tuple) and len(update) == 2:
        path, data = update
        path_str = " > ".join(str(p) for p in path) if path else "root"
    else:
        path_str = "root"
        data = update

    if not isinstance(data, dict):
        return

    for node_name, node_data in data.items():
        print(f"\n[{path_str}] {node_name}")

        if node_name == "process_input":
            route = node_data.get("route", "unknown")
            print(f"  → Routing to: {route}")

        elif node_name == "create_vm_instance":
            instance_id = node_data.get("instance_id", "")[:8] + "..." if node_data.get("instance_id") else "N/A"
            print(f"  → Browser instance created: {instance_id}")

        elif node_name == "call_model":
            messages = node_data.get("messages", {})
            if hasattr(messages, "additional_kwargs"):
                tool_outputs = messages.additional_kwargs.get("tool_outputs", [])
                for output in tool_outputs:
                    if output.get("type") == "computer_call":
                        action = output.get("action", {})
                        action_type = action.get("type", "unknown")
                        details = ""
                        if action_type == "click":
                            details = f" at ({action.get('x')}, {action.get('y')})"
                        elif action_type == "type":
                            text = action.get("text", "")[:30]
                            details = f' "{text}..."' if len(action.get("text", "")) > 30 else f' "{text}"'
                        elif action_type == "scroll":
                            details = f" by ({action.get('scroll_x')}, {action.get('scroll_y')})"
                        print(f"  → AI requests: {action_type}{details}")
            elif hasattr(messages, "content"):
                content = messages.content
                if isinstance(content, list) and content:
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text = item.get("text", "")[:100]
                            print(f"  → AI says: {text}...")
                elif isinstance(content, str) and content:
                    print(f"  → AI says: {content[:100]}...")

        elif node_name == "take_computer_action":
            error = node_data.get("messages", {}).get("additional_kwargs", {}).get("error")
            if error:
                print(f"  → Action failed: {error[:50]}...")
            else:
                print(f"  → Action completed ✓ (screenshot captured)")

        elif node_name == "respond":
            print(f"  → Generating response...")

# Create the Computer Use Agent (CUA) graph
cua_graph = create_cua()


class PriceFinderState(CUAState):
    """State class for the Price Finder workflow, extending the CUA state."""

    route: Literal["respond", "computer_use_agent"]


def process_input(state: PriceFinderState):
    """
    Analyzes the user's latest message and determines whether to route to the
    computer use agent or to generate a direct response.

    Args:
        state: Current workflow state containing message history

    Returns:
        Dict with routing decision
    """
    system_message = {
        "role": "system",
        "content": (
            "You're an advanced AI assistant tasked with routing the user's query to the appropriate node."
            + "Your options are: computer use or respond. You should pick computer use if the user's request requires "
            + "using a computer (e.g. looking up a price on a website), and pick respond for ANY other inputs."
        ),
    }

    class RoutingToolSchema(BaseModel):
        """Route the user's request to the appropriate node."""

        route: Literal["respond", "computer_use_agent"] = Field(
            ...,
            description="The node to route to, either 'computer_use_agent' for any input which might require using a computer to assist the user, or 'respond' for any other input",
        )

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    model_with_tools = model.with_structured_output(RoutingToolSchema)

    messages = [system_message, {"role": "user", "content": state.get("messages")[-1].content}]

    response = model_with_tools.invoke(messages)
    return {"route": response.route}


def respond(state: PriceFinderState):
    """
    Generates a general response to the user based on the entire conversation history.

    Args:
        state: Current workflow state containing full message history

    Returns:
        Dict containing the generated response
    """

    def format_messages(messages: List[AnyMessage]) -> str:
        """Formats a list of messages into a single string with type and content."""
        return "\n".join([f"{message.type}: {message.content}" for message in messages])

    system_message = {
        "role": "system",
        "content": (
            "You're an advanced AI assistant tasked with responding to the user's input."
            + "You're provided with the full conversation between the user, and the AI assistant. "
            + "This conversation may include messages from a computer use agent, along with "
            + "general user inputs and AI responses. \n\n"
            + "Given all of this, please RESPOND to the user. If there is nothing to respond to, you may return something like 'Let me know if you have any other questions.'"
        ),
    }
    human_message = {
        "role": "user",
        "content": "Here are all of the messages in the conversation:\n\n"
        + format_messages(state.get("messages")),
    }

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    response = model.invoke([system_message, human_message])
    return {"response": response}


def route_after_processing_input(state: PriceFinderState):
    """
    Conditional router that returns the route determined by process_input.

    Args:
        state: Current workflow state with route decision

    Returns:
        String route name for the next node
    """
    return state.get("route")


workflow = StateGraph(PriceFinderState)
workflow.add_node("process_input", process_input)
workflow.add_node("respond", respond)
workflow.add_node("computer_use_agent", cua_graph)

workflow.add_edge(START, "process_input")
workflow.add_conditional_edges("process_input", route_after_processing_input)
workflow.add_edge("respond", END)
workflow.add_edge("computer_use_agent", END)

graph = workflow.compile()
graph.name = "Price Finder"


async def main():
    """Run the Price Finder workflow with a sample tire price query."""
    # Define the initial conversation messages
    messages = [
        {
            "role": "system",
            "content": (
                "You're an advanced AI computer use assistant. The browser you are using "
                "is already initialized, and visiting google.com."
            ),
        },
        {
            "role": "user",
            "content": (
                "Can you find the best price for new all season tires which will fit on my 2019 Subaru Forester?"
            ),
        },
    ]

    # Collect all updates for report generation
    all_updates = []

    # Stream the graph execution with updates visible
    stream = graph.astream({"messages": messages}, subgraphs=True, stream_mode="updates")
    print("Stream started")

    # Process and display the stream updates
    try:
        async for update in stream:
            all_updates.append(update)
            # Print a cleaner summary instead of raw data
            print_clean_update(update)
    except KeyboardInterrupt:
        print("\n\nTask interrupted by user.")
    except Exception as e:
        print(f"\n\nTask ended with error: {e}")

    # Generate and display the analysis report
    print("\n" + "=" * 60)
    print("Generating Analysis Report...")
    print("=" * 60)

    report = CUAReportGenerator.from_stream_updates(all_updates)

    # Print summary to console
    report.print_summary()

    # Save detailed markdown report
    report_path = "cua_report.md"
    with open(report_path, "w") as f:
        f.write(report.to_markdown())
    print(f"Detailed report saved to: {report_path}")

    # Also save JSON report
    json_report_path = "cua_report.json"
    with open(json_report_path, "w") as f:
        f.write(report.to_json())
    print(f"JSON report saved to: {json_report_path}")

    print("\nDone")


if __name__ == "__main__":
    import asyncio
    import signal

    # Handle Ctrl+C gracefully
    def handle_interrupt(signum, frame):
        print("\n\nInterrupt received, generating report...")
        raise KeyboardInterrupt()

    signal.signal(signal.SIGINT, handle_interrupt)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScript interrupted.")
