from __future__ import annotations
import logging
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright, Playwright, Browser, Page, TimeoutError, Error

logger = logging.getLogger(__name__)


class BrowserAgent:
    """Asynchronous browser controller utilizing Playwright to interact with pages.

    Managed as an asynchronous context manager to ensure proper resource cleanup.
    """

    def __init__(self, record_video_dir: str | Path | None = None) -> None:
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: Any | None = None
        self.page: Page | None = None
        self.network_traffic: list[dict[str, Any]] = []
        self.record_video_dir = record_video_dir

    async def __aenter__(self, record_video_dir: str | Path | None = None) -> BrowserAgent:
        if record_video_dir is not None:
            self.record_video_dir = record_video_dir

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        
        context_args = {}
        if self.record_video_dir:
            Path(self.record_video_dir).mkdir(parents=True, exist_ok=True)
            context_args["record_video_dir"] = str(self.record_video_dir)
            context_args["record_video_size"] = {"width": 1280, "height": 720}

        self.context = await self.browser.new_context(**context_args)
        self.page = await self.context.new_page()
        self.network_traffic = []
        self.page.on("request", self._handle_request)
        self.page.on("response", self._handle_response)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.page:
            try:
                await self.page.close()
            except Exception:
                pass
            self.page = None
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
            self.context = None
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
            self.browser = None
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass
            self.playwright = None

    async def navigate(self, url: str) -> None:
        """Navigate the active browser page to the given URL.

        Handles TimeoutError if the target server isn't responsive or fully booted yet.
        """
        if not self.page:
            raise RuntimeError("Browser is not initialized. Use inside 'async with' context.")
        try:
            await self.page.goto(url, wait_until="load")
        except TimeoutError as e:
            logger.error(f"Timeout occurred while navigating to {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {e}")
            raise

    async def extract_interactive_elements(self) -> dict[str, list[dict[str, Any]]]:
        """Extract all interactive elements (buttons, links, inputs/forms) from the current page.

        Returns:
            dict: Structured counts and metadata of discovered interactive elements.
        """
        if not self.page:
            raise RuntimeError("Browser is not initialized. Use inside 'async with' context.")

        buttons: list[dict[str, Any]] = []
        links: list[dict[str, Any]] = []
        inputs: list[dict[str, Any]] = []

        # Extract Buttons: <button> or role="button"
        buttons_locator = self.page.locator("button, [role='button']")
        btn_count = await buttons_locator.count()
        for i in range(btn_count):
            loc = buttons_locator.nth(i)
            text = (await loc.inner_text()) or (await loc.text_content()) or ""
            buttons.append({
                "text": text.strip()
            })

        # Extract Links: <a>
        links_locator = self.page.locator("a")
        link_count = await links_locator.count()
        for i in range(link_count):
            loc = links_locator.nth(i)
            href = await loc.get_attribute("href") or ""
            text = (await loc.inner_text()) or (await loc.text_content()) or ""
            links.append({
                "href": href,
                "text": text.strip()
            })

        # Extract Inputs/Forms: <input>, <textarea>
        inputs_locator = self.page.locator("input, textarea")
        input_count = await inputs_locator.count()
        for i in range(input_count):
            loc = inputs_locator.nth(i)
            input_type = await loc.get_attribute("type") or ""
            name = await loc.get_attribute("name") or ""
            placeholder = await loc.get_attribute("placeholder") or ""
            inputs.append({
                "type": input_type,
                "name": name,
                "placeholder": placeholder
            })

        return {
            "buttons": buttons,
            "links": links,
            "inputs": inputs
        }

    async def capture_screenshot(self, output_path: str, full_page: bool = True) -> None:
        """Capture a screenshot of the current page and save it to the output path."""
        if not self.page:
            raise RuntimeError("Browser is not initialized. Use inside 'async with' context.")

        path_obj = Path(output_path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        await self.page.screenshot(path=str(path_obj), full_page=full_page)

    def _handle_request(self, request: Any) -> None:
        """Log intercepted request if it's fetch, xhr, or document."""
        try:
            resource_type = request.resource_type
            if resource_type in ["fetch", "xhr", "document"]:
                post_data = request.post_data
                self.network_traffic.append({
                    "url": request.url,
                    "method": request.method,
                    "resource_type": resource_type,
                    "post_data": post_data,
                    "status": None,
                })
        except Exception as e:
            logger.error(f"Error handling request interception: {e}")

    def _handle_response(self, response: Any) -> None:
        """Log intercepted response status back to the corresponding request."""
        try:
            req = response.request
            resource_type = req.resource_type
            if resource_type in ["fetch", "xhr", "document"]:
                for item in reversed(self.network_traffic):
                    if item["url"] == response.url and item["method"] == req.method and item["status"] is None:
                        item["status"] = response.status
                        break
        except Exception as e:
            logger.error(f"Error handling response interception: {e}")

    def get_network_traffic(self) -> list[dict[str, Any]]:
        """Return the collected network traffic list."""
        return self.network_traffic

    async def click_and_trace(self, text_to_click: str) -> dict[str, Any]:
        """Click an element containing the specified text and trace network traffic."""
        if not self.page:
            raise RuntimeError("Browser is not initialized. Use inside 'async with' context.")
        self.network_traffic.clear()

        locator = self.page.get_by_text(text_to_click, exact=False).first

        try:
            await locator.click(timeout=5000)
        except (TimeoutError, Error) as e:
            logger.error(f"Failed to find or click element with text '{text_to_click}': {e}")
            raise ValueError(f"Element containing '{text_to_click}' was not found or not clickable.")
        except Exception as e:
            logger.error(f"Failed to click element with text '{text_to_click}': {e}")
            raise

        try:
            await self.page.wait_for_load_state("networkidle", timeout=3000)
        except TimeoutError:
            logger.warning("Timeout waiting for network idle after click. Continuing with intercepted traffic.")
        except Exception as e:
            logger.error(f"Error waiting for network idle: {e}")

        return {
            "action": text_to_click,
            "traffic": self.network_traffic,
        }

    async def record_workflow(self, actions_to_click: list[str], output_filename: str) -> str:
        """Execute a sequence of click actions while recording video, then finalize and save the video."""
        if not self.page:
            raise RuntimeError("Browser is not initialized. Use inside 'async with' context.")

        if not self.record_video_dir:
            raise ValueError("record_video_dir must be configured on BrowserAgent to record workflows.")

        # Execute actions in sequence
        for action in actions_to_click:
            try:
                locator = self.page.get_by_text(action, exact=False).first
                await locator.click(timeout=5000)
                await self.page.wait_for_timeout(1500)
            except Exception as e:
                logger.warning(f"Failed to click element with text '{action}' in sequence: {e}")

        # Get temporary video path from page before closing
        temp_video_path = None
        if self.page and getattr(self.page, "video", None):
            try:
                temp_video_path = await self.page.video.path()
            except Exception as e:
                logger.warning(f"Could not retrieve video path: {e}")

        # Gracefully close page and context to finalize the video
        if self.page:
            try:
                await self.page.close()
            except Exception:
                pass
            self.page = None
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
            self.context = None

        video_dir_path = Path(self.record_video_dir)
        final_video_path = video_dir_path / output_filename

        # Find and rename the video file
        src_path = None
        if temp_video_path and Path(temp_video_path).exists():
            src_path = Path(temp_video_path)
        else:
            # Fallback: search the video directory for .webm files
            webm_files = list(video_dir_path.glob("*.webm"))
            if webm_files:
                webm_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                src_path = webm_files[0]

        if src_path and src_path.exists():
            src_path.rename(final_video_path)
            return str(final_video_path.resolve())
        else:
            raise FileNotFoundError(f"No video file found in {video_dir_path}")


