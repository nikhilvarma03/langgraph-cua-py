from typing import Any

from langchain_core.runnables import RunnableConfig

from .browser_adapter import BrowserInstance, PlaywrightClient, get_playwright_client
from .types import get_configuration_with_defaults


def get_browser_client(headless: bool = False) -> PlaywrightClient:
    """
    Gets the Playwright browser client.

    Args:
        headless: Whether to run the browser in headless mode.

    Returns:
        The PlaywrightClient instance.
    """
    return get_playwright_client(headless=headless)


def get_instance(id: str, config: RunnableConfig) -> BrowserInstance:
    """
    Gets a browser instance by its ID.

    Args:
        id: The ID of the instance to get.
        config: The configuration for the runnable.

    Returns:
        The browser instance.
    """
    configuration = get_configuration_with_defaults(config)
    headless = configuration.get("headless", False)
    client = get_browser_client(headless=headless)
    return client.get(id)


def is_computer_tool_call(tool_outputs: Any) -> bool:
    """
    Checks if the given tool outputs are a computer call.

    Args:
        tool_outputs: The tool outputs to check.

    Returns:
        True if the tool outputs are a computer call, false otherwise.
    """
    if not tool_outputs or not isinstance(tool_outputs, list):
        return False

    return any(output.get("type") == "computer_call" for output in tool_outputs)
