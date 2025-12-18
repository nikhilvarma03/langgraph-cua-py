from langchain_core.runnables.config import RunnableConfig

from ..browser_adapter import BrowserInstance
from ..types import CUAState
from ..utils import get_browser_client, get_configuration_with_defaults

# Copied from the OpenAI example repository
# https://github.com/openai/openai-cua-sample-app/blob/eb2d58ba77ffd3206d3346d6357093647d29d99c/utils.py#L13
BLOCKED_DOMAINS = [
    "maliciousbook.com",
    "evilvideos.com",
    "darkwebforum.com",
    "shadytok.com",
    "suspiciouspins.com",
    "ilanbigio.com",
]


def create_vm_instance(state: CUAState, config: RunnableConfig):
    instance_id = state.get("instance_id")
    configuration = get_configuration_with_defaults(config)
    timeout_hours = configuration.get("timeout_hours")
    environment = configuration.get("environment")
    headless = configuration.get("headless", False)

    if instance_id is not None:
        # If the instance_id already exists in state, do nothing.
        return {}

    client = get_browser_client(headless=headless)

    instance: BrowserInstance

    if environment == "ubuntu":
        # Ubuntu VM not supported with free Playwright adapter
        raise NotImplementedError(
            "Ubuntu VM instances are not supported with the free Playwright adapter. "
            "Use environment='web' for browser-only automation."
        )
    elif environment == "windows":
        # Windows VM not supported with free Playwright adapter
        raise NotImplementedError(
            "Windows VM instances are not supported with the free Playwright adapter. "
            "Use environment='web' for browser-only automation."
        )
    elif environment == "web":
        blocked_domains = [
            domain.replace("https://", "").replace("www.", "") for domain in BLOCKED_DOMAINS
        ]
        instance = client.start_browser(
            timeout_hours=timeout_hours, blocked_domains=blocked_domains
        )
    else:
        raise ValueError(
            f"Invalid environment. Must be 'web' for browser automation. Received: {environment}"
        )

    stream_url = instance.get_stream_url().stream_url

    return {
        "instance_id": instance.id,
        "stream_url": stream_url,
    }
