"""
Browser adapter that provides a Scrapybara-compatible interface using Playwright.
This allows the CUA to work with a local browser instead of Scrapybara's cloud VMs.
"""

import asyncio
import base64
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright


@dataclass
class ComputerResponse:
    """Response from a computer action, mimics scrapybara.types.ComputerResponse"""

    base_64_image: str


@dataclass
class StreamUrlResponse:
    """Response containing stream URL, mimics scrapybara.types.InstanceGetStreamUrlResponse"""

    stream_url: str


class BrowserInstance:
    """
    A browser instance that mimics Scrapybara's BrowserInstance interface.
    Uses Playwright under the hood for browser automation.
    """

    def __init__(
        self,
        browser: Browser,
        context: BrowserContext,
        page: Page,
        instance_id: str,
    ):
        self._browser = browser
        self._context = context
        self._page = page
        self.id = instance_id
        self._viewport_width = 1280
        self._viewport_height = 720

    async def _take_screenshot(self) -> str:
        """Take a screenshot and return base64 encoded image."""
        screenshot_bytes = await self._page.screenshot(type="png", full_page=False)
        return base64.b64encode(screenshot_bytes).decode("utf-8")

    def computer(
        self,
        action: str,
        coordinates: Optional[List[int]] = None,
        button: Optional[str] = None,
        num_clicks: Optional[int] = 1,
        text: Optional[str] = None,
        keys: Optional[List[str]] = None,
        path: Optional[List[List[int]]] = None,
        delta_x: Optional[int] = None,
        delta_y: Optional[int] = None,
        **kwargs: Any,
    ) -> ComputerResponse:
        """
        Execute a computer action and return a screenshot.
        Mimics the Scrapybara instance.computer() interface.
        """
        # Run the async method in a new event loop or get existing one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a new task
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._computer_async(
                            action=action,
                            coordinates=coordinates,
                            button=button,
                            num_clicks=num_clicks,
                            text=text,
                            keys=keys,
                            path=path,
                            delta_x=delta_x,
                            delta_y=delta_y,
                            **kwargs,
                        ),
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self._computer_async(
                        action=action,
                        coordinates=coordinates,
                        button=button,
                        num_clicks=num_clicks,
                        text=text,
                        keys=keys,
                        path=path,
                        delta_x=delta_x,
                        delta_y=delta_y,
                        **kwargs,
                    )
                )
        except RuntimeError:
            return asyncio.run(
                self._computer_async(
                    action=action,
                    coordinates=coordinates,
                    button=button,
                    num_clicks=num_clicks,
                    text=text,
                    keys=keys,
                    path=path,
                    delta_x=delta_x,
                    delta_y=delta_y,
                    **kwargs,
                )
            )

    async def _computer_async(
        self,
        action: str,
        coordinates: Optional[List[int]] = None,
        button: Optional[str] = None,
        num_clicks: Optional[int] = 1,
        text: Optional[str] = None,
        keys: Optional[List[str]] = None,
        path: Optional[List[List[int]]] = None,
        delta_x: Optional[int] = None,
        delta_y: Optional[int] = None,
        **kwargs: Any,
    ) -> ComputerResponse:
        """Async implementation of computer actions."""

        if action == "click_mouse":
            if coordinates:
                x, y = coordinates[0], coordinates[1]
                pw_button = "left"
                if button == "right":
                    pw_button = "right"
                elif button == "middle":
                    pw_button = "middle"

                await self._page.mouse.click(x, y, button=pw_button, click_count=num_clicks or 1)

        elif action == "double_click":
            if coordinates:
                x, y = coordinates[0], coordinates[1]
                await self._page.mouse.dblclick(x, y)

        elif action == "move_mouse":
            if coordinates:
                x, y = coordinates[0], coordinates[1]
                await self._page.mouse.move(x, y)

        elif action == "drag_mouse":
            if path and len(path) >= 2:
                start = path[0]
                await self._page.mouse.move(start[0], start[1])
                await self._page.mouse.down()
                for point in path[1:]:
                    await self._page.mouse.move(point[0], point[1])
                await self._page.mouse.up()

        elif action == "type_text":
            if text:
                await self._page.keyboard.type(text)

        elif action == "press_key":
            if keys:
                for key in keys:
                    # Map Scrapybara key names to Playwright key names
                    pw_key = self._map_key(key)
                    await self._page.keyboard.press(pw_key)

        elif action == "scroll":
            if coordinates and (delta_x is not None or delta_y is not None):
                x, y = coordinates[0], coordinates[1]
                await self._page.mouse.move(x, y)
                # Playwright uses wheel event with deltaX/deltaY
                await self._page.mouse.wheel(delta_x or 0, delta_y or 0)

        elif action == "take_screenshot":
            pass  # Screenshot is taken at the end anyway

        else:
            raise ValueError(f"Unknown action: {action}")

        # Always take a screenshot after the action
        screenshot_base64 = await self._take_screenshot()
        return ComputerResponse(base_64_image=screenshot_base64)

    def _map_key(self, key: str) -> str:
        """Map Scrapybara key names to Playwright key names."""
        key_map = {
            "Return": "Enter",
            "BackSpace": "Backspace",
            "Escape": "Escape",
            "Tab": "Tab",
            "Delete": "Delete",
            "Insert": "Insert",
            "Home": "Home",
            "End": "End",
            "Page_Up": "PageUp",
            "Page_Down": "PageDown",
            "Up": "ArrowUp",
            "Down": "ArrowDown",
            "Left": "ArrowLeft",
            "Right": "ArrowRight",
            "Meta_L": "Meta",
            "Alt_L": "Alt",
            "Caps_Lock": "CapsLock",
            "slash": "/",
            "backslash": "\\",
        }
        return key_map.get(key, key)

    def get_stream_url(self) -> StreamUrlResponse:
        """
        Return a stream URL. For local browser, this returns a placeholder
        since there's no remote stream available.
        """
        # For local Playwright, there's no stream URL like Scrapybara provides
        # Return a placeholder that indicates local browser
        return StreamUrlResponse(stream_url=f"local://browser/{self.id}")

    def authenticate(self, auth_state_id: str) -> None:
        """
        Authentication placeholder. For local browser, this is a no-op
        since auth would be handled differently (e.g., cookies, storage state).
        """
        # In a real implementation, you could load a Playwright storage state file
        pass

    async def close(self) -> None:
        """Close the browser instance."""
        await self._context.close()
        await self._browser.close()


class PlaywrightClient:
    """
    Client that mimics Scrapybara's client interface using Playwright.
    """

    def __init__(self, headless: bool = False):
        self._headless = headless
        self._instances: Dict[str, BrowserInstance] = {}
        self._playwright = None

    def start_browser(
        self,
        timeout_hours: Optional[float] = None,
        blocked_domains: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> BrowserInstance:
        """Start a new browser instance."""
        return asyncio.run(
            self._start_browser_async(
                timeout_hours=timeout_hours, blocked_domains=blocked_domains, **kwargs
            )
        )

    async def _start_browser_async(
        self,
        timeout_hours: Optional[float] = None,
        blocked_domains: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> BrowserInstance:
        """Async implementation of start_browser."""
        self._playwright = await async_playwright().start()
        browser = await self._playwright.chromium.launch(headless=self._headless)

        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
        )

        # Block domains if specified
        if blocked_domains:
            await context.route(
                lambda url: any(domain in url for domain in blocked_domains),
                lambda route: route.abort(),
            )

        page = await context.new_page()
        await page.goto("about:blank")

        instance_id = str(uuid.uuid4())
        instance = BrowserInstance(
            browser=browser,
            context=context,
            page=page,
            instance_id=instance_id,
        )
        self._instances[instance_id] = instance
        return instance

    def get(self, instance_id: str) -> BrowserInstance:
        """Get an existing browser instance by ID."""
        if instance_id not in self._instances:
            raise ValueError(f"Instance {instance_id} not found")
        return self._instances[instance_id]

    def start_ubuntu(self, **kwargs: Any) -> BrowserInstance:
        """
        Ubuntu VM is not supported in the free Playwright adapter.
        Falls back to browser mode.
        """
        raise NotImplementedError(
            "Ubuntu VM instances are not supported with the free Playwright adapter. "
            "Use environment='web' for browser-only automation, or use Scrapybara for full VM support."
        )

    def start_windows(self, **kwargs: Any) -> BrowserInstance:
        """
        Windows VM is not supported in the free Playwright adapter.
        Falls back to browser mode.
        """
        raise NotImplementedError(
            "Windows VM instances are not supported with the free Playwright adapter. "
            "Use environment='web' for browser-only automation, or use Scrapybara for full VM support."
        )


# Global client instance cache
_client_instance: Optional[PlaywrightClient] = None


def get_playwright_client(headless: bool = False) -> PlaywrightClient:
    """Get or create the Playwright client singleton."""
    global _client_instance
    if _client_instance is None:
        _client_instance = PlaywrightClient(headless=headless)
    return _client_instance
