"""
Browser adapter that provides a Scrapybara-compatible interface using Playwright.
This allows the CUA to work with a local browser instead of Scrapybara's cloud VMs.
"""

import base64
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright, Playwright


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

    def _take_screenshot(self) -> str:
        """Take a screenshot and return base64 encoded image."""
        screenshot_bytes = self._page.screenshot(type="png", full_page=False)
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
        if action == "click_mouse":
            if coordinates:
                x, y = coordinates[0], coordinates[1]
                pw_button = "left"
                if button == "right":
                    pw_button = "right"
                elif button == "middle":
                    pw_button = "middle"

                self._page.mouse.click(x, y, button=pw_button, click_count=num_clicks or 1)

        elif action == "double_click":
            if coordinates:
                x, y = coordinates[0], coordinates[1]
                self._page.mouse.dblclick(x, y)

        elif action == "move_mouse":
            if coordinates:
                x, y = coordinates[0], coordinates[1]
                self._page.mouse.move(x, y)

        elif action == "drag_mouse":
            if path and len(path) >= 2:
                start = path[0]
                self._page.mouse.move(start[0], start[1])
                self._page.mouse.down()
                for point in path[1:]:
                    self._page.mouse.move(point[0], point[1])
                self._page.mouse.up()

        elif action == "type_text":
            if text:
                self._page.keyboard.type(text)

        elif action == "press_key":
            if keys:
                # Map all keys first
                mapped_keys = [self._map_key(key) for key in keys]

                # Check if this is a key combination (modifier + key)
                modifiers = {"Control", "Shift", "Alt", "Meta"}
                has_modifier = any(k in modifiers for k in mapped_keys)

                if has_modifier and len(mapped_keys) > 1:
                    # Press as a combination (e.g., "Control+r")
                    combo = "+".join(mapped_keys)
                    self._page.keyboard.press(combo)
                else:
                    # Press keys individually
                    for pw_key in mapped_keys:
                        self._page.keyboard.press(pw_key)

        elif action == "scroll":
            if coordinates and (delta_x is not None or delta_y is not None):
                x, y = coordinates[0], coordinates[1]
                self._page.mouse.move(x, y)
                # Playwright uses wheel event with deltaX/deltaY
                self._page.mouse.wheel(delta_x or 0, delta_y or 0)

        elif action == "take_screenshot":
            pass  # Screenshot is taken at the end anyway

        else:
            raise ValueError(f"Unknown action: {action}")

        # Always take a screenshot after the action
        screenshot_base64 = self._take_screenshot()
        return ComputerResponse(base_64_image=screenshot_base64)

    def _map_key(self, key: str) -> str:
        """Map Scrapybara/CUA key names to Playwright key names (Mac-friendly)."""
        # Normalize to lowercase for matching
        key_lower = key.lower()
        key_map = {
            # Modifier keys (Mac uses Meta for Command key)
            "ctrl": "Meta",  # Map Ctrl to Cmd on Mac
            "control": "Meta",  # Map Ctrl to Cmd on Mac
            "cmd": "Meta",
            "command": "Meta",
            "meta": "Meta",
            "super": "Meta",
            "win": "Meta",
            "shift": "Shift",
            "alt": "Alt",
            "option": "Alt",
            # Special keys
            "return": "Enter",
            "enter": "Enter",
            "backspace": "Backspace",
            "escape": "Escape",
            "esc": "Escape",
            "tab": "Tab",
            "delete": "Delete",
            "insert": "Insert",
            "home": "Home",
            "end": "End",
            "pageup": "PageUp",
            "page_up": "PageUp",
            "pagedown": "PageDown",
            "page_down": "PageDown",
            "space": " ",
            # Arrow keys
            "up": "ArrowUp",
            "down": "ArrowDown",
            "left": "ArrowLeft",
            "right": "ArrowRight",
            "arrowup": "ArrowUp",
            "arrowdown": "ArrowDown",
            "arrowleft": "ArrowLeft",
            "arrowright": "ArrowRight",
            # Function keys
            "f1": "F1",
            "f2": "F2",
            "f3": "F3",
            "f4": "F4",
            "f5": "F5",
            "f6": "F6",
            "f7": "F7",
            "f8": "F8",
            "f9": "F9",
            "f10": "F10",
            "f11": "F11",
            "f12": "F12",
            # Legacy Scrapybara mappings
            "meta_l": "Meta",
            "alt_l": "Alt",
            "caps_lock": "CapsLock",
            "capslock": "CapsLock",
            "slash": "/",
            "backslash": "\\",
        }
        return key_map.get(key_lower, key)

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

    def close(self) -> None:
        """Close the browser instance."""
        self._context.close()
        self._browser.close()


class PlaywrightClient:
    """
    Client that mimics Scrapybara's client interface using Playwright.
    """

    def __init__(self, headless: bool = False):
        self._headless = headless
        self._instances: Dict[str, BrowserInstance] = {}
        self._playwright: Optional[Playwright] = None

    def start_browser(
        self,
        timeout_hours: Optional[float] = None,
        blocked_domains: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> BrowserInstance:
        """Start a new browser instance."""
        if self._playwright is None:
            self._playwright = sync_playwright().start()

        browser = self._playwright.chromium.launch(headless=self._headless)

        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
        )

        # Block domains if specified
        if blocked_domains:
            def should_abort(route):
                url = route.request.url
                if any(domain in url for domain in blocked_domains):
                    route.abort()
                else:
                    route.continue_()

            context.route("**/*", should_abort)

        page = context.new_page()
        page.goto("about:blank")

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
