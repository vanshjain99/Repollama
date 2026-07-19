from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import pytest
from repollama.engines.browser import BrowserAgent
from playwright.async_api import TimeoutError


@pytest.mark.anyio
async def test_browser_agent_lifecycle() -> None:
    # Mock playwright
    mock_playwright = AsyncMock()
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_page.on = MagicMock()

    mock_playwright.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    with patch("repollama.engines.browser.async_playwright") as mock_async_playwright:
        mock_instance = AsyncMock()
        mock_async_playwright.return_value = mock_instance
        mock_instance.start.return_value = mock_playwright

        async with BrowserAgent() as agent:
            assert agent.playwright == mock_playwright
            assert agent.browser == mock_browser
            assert agent.context == mock_context
            assert agent.page == mock_page

        mock_instance.start.assert_called_once()
        mock_playwright.chromium.launch.assert_called_once_with(headless=True)
        mock_browser.new_context.assert_called_once()
        mock_context.new_page.assert_called_once()
        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()


@pytest.mark.anyio
async def test_browser_agent_navigate_success() -> None:
    mock_page = AsyncMock()
    agent = BrowserAgent()
    agent.page = mock_page

    await agent.navigate("http://example.com")
    mock_page.goto.assert_called_once_with("http://example.com", wait_until="load")


@pytest.mark.anyio
async def test_browser_agent_navigate_timeout() -> None:
    mock_page = AsyncMock()
    mock_page.goto.side_effect = TimeoutError("Navigation timeout")

    agent = BrowserAgent()
    agent.page = mock_page

    with pytest.raises(TimeoutError):
        await agent.navigate("http://slow-website.com")


@pytest.mark.anyio
async def test_browser_agent_extract_elements() -> None:
    mock_page = AsyncMock()

    # Mock locator for buttons (count and inner_text/text_content are async, nth is sync)
    mock_buttons_loc = MagicMock()
    mock_buttons_loc.count = AsyncMock(return_value=1)
    mock_btn_el = AsyncMock()
    mock_btn_el.inner_text.return_value = "Click Me"
    mock_btn_el.text_content.return_value = "Click Me"
    mock_buttons_loc.nth = MagicMock(return_value=mock_btn_el)

    # Mock locator for links (count, get_attribute, inner_text/text_content are async, nth is sync)
    mock_links_loc = MagicMock()
    mock_links_loc.count = AsyncMock(return_value=1)
    mock_link_el = AsyncMock()
    mock_link_el.get_attribute.side_effect = lambda attr: "https://example.com" if attr == "href" else None
    mock_link_el.inner_text.return_value = "Example Link"
    mock_link_el.text_content.return_value = "Example Link"
    mock_links_loc.nth = MagicMock(return_value=mock_link_el)

    # Mock locator for inputs
    mock_inputs_loc = MagicMock()
    mock_inputs_loc.count = AsyncMock(return_value=1)
    mock_input_el = AsyncMock()
    mock_input_el.get_attribute.side_effect = lambda attr: {
        "type": "text",
        "name": "username",
        "placeholder": "Enter username"
    }.get(attr, "")
    mock_inputs_loc.nth = MagicMock(return_value=mock_input_el)

    # locator itself is sync
    mock_page.locator = MagicMock()

    def locator_side_effect(selector: str) -> MagicMock:
        if "button" in selector:
            return mock_buttons_loc
        elif "a" == selector:
            return mock_links_loc
        elif "input" in selector:
            return mock_inputs_loc
        return MagicMock()

    mock_page.locator.side_effect = locator_side_effect

    agent = BrowserAgent()
    agent.page = mock_page

    elements = await agent.extract_interactive_elements()

    assert len(elements["buttons"]) == 1
    assert elements["buttons"][0]["text"] == "Click Me"

    assert len(elements["links"]) == 1
    assert elements["links"][0]["href"] == "https://example.com"
    assert elements["links"][0]["text"] == "Example Link"

    assert len(elements["inputs"]) == 1
    assert elements["inputs"][0]["type"] == "text"
    assert elements["inputs"][0]["name"] == "username"
    assert elements["inputs"][0]["placeholder"] == "Enter username"


@pytest.mark.anyio
async def test_browser_agent_capture_screenshot(tmp_path: Path) -> None:
    mock_page = AsyncMock()
    agent = BrowserAgent()
    agent.page = mock_page

    output_path = tmp_path / "screenshot.png"
    await agent.capture_screenshot(str(output_path), full_page=True)

    mock_page.screenshot.assert_called_once_with(path=str(output_path), full_page=True)


@pytest.mark.anyio
async def test_browser_agent_network_traffic() -> None:
    agent = BrowserAgent()

    mock_page = MagicMock()
    callbacks = {}
    def on_side_effect(event_name: str, callback: Any) -> None:
        callbacks[event_name] = callback
    mock_page.on.side_effect = on_side_effect

    mock_playwright = AsyncMock()
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    mock_playwright.chromium.launch.return_value = mock_browser

    with patch("repollama.engines.browser.async_playwright") as mock_async_playwright:
        mock_instance = AsyncMock()
        mock_async_playwright.return_value = mock_instance
        mock_instance.start.return_value = mock_playwright

        async with agent:
            # Check listeners are registered
            assert "request" in callbacks
            assert "response" in callbacks

            # Simulate a request event
            mock_request = MagicMock()
            mock_request.url = "http://example.com/api/data"
            mock_request.method = "POST"
            mock_request.resource_type = "fetch"
            mock_request.post_data = '{"key": "val"}'

            callbacks["request"](mock_request)

            # Check traffic recorded
            traffic = agent.get_network_traffic()
            assert len(traffic) == 1
            assert traffic[0]["url"] == "http://example.com/api/data"
            assert traffic[0]["method"] == "POST"
            assert traffic[0]["resource_type"] == "fetch"
            assert traffic[0]["post_data"] == '{"key": "val"}'
            assert traffic[0]["status"] is None

            # Simulate response event matching URL
            mock_response = MagicMock()
            mock_response.url = "http://example.com/api/data"
            mock_response.status = 200
            mock_response.request = mock_request

            callbacks["response"](mock_response)

            # Check traffic updated with status
            traffic = agent.get_network_traffic()
            assert len(traffic) == 1
            assert traffic[0]["status"] == 200


@pytest.mark.anyio
async def test_browser_agent_click_and_trace_success() -> None:
    mock_page = AsyncMock()
    mock_page.get_by_text = MagicMock()
    mock_locator = AsyncMock()

    # Mock locator chaining: page.get_by_text().first
    mock_get_by_text = MagicMock()
    mock_get_by_text.first = mock_locator
    mock_page.get_by_text.return_value = mock_get_by_text

    agent = BrowserAgent()
    agent.page = mock_page
    # Put some mock traffic to test clearing
    agent.network_traffic = [{"url": "http://prev.com", "method": "GET"}]

    # Simulate a network request getting logged during click/wait
    mock_traffic_entry = {"url": "http://example.com/api", "method": "POST", "status": 200}

    async def side_effect_click(*args, **kwargs):
        agent.network_traffic.append(mock_traffic_entry)

    mock_locator.click.side_effect = side_effect_click

    res = await agent.click_and_trace("Click Me")

    assert res["action"] == "Click Me"
    assert len(res["traffic"]) == 1
    assert res["traffic"][0] == mock_traffic_entry
    assert len(agent.network_traffic) == 1

    mock_page.get_by_text.assert_called_once_with("Click Me", exact=False)
    mock_locator.click.assert_called_once_with(timeout=5000)
    mock_page.wait_for_load_state.assert_called_once_with("networkidle", timeout=3000)


@pytest.mark.anyio
async def test_browser_agent_click_and_trace_click_timeout() -> None:
    mock_page = AsyncMock()
    mock_page.get_by_text = MagicMock()
    mock_locator = AsyncMock()
    mock_locator.click.side_effect = TimeoutError("Click timeout")

    mock_get_by_text = MagicMock()
    mock_get_by_text.first = mock_locator
    mock_page.get_by_text.return_value = mock_get_by_text

    agent = BrowserAgent()
    agent.page = mock_page

    with pytest.raises(ValueError) as exc_info:
        await agent.click_and_trace("Nonexistent Link")

    assert "was not found or not clickable" in str(exc_info.value)
    mock_locator.click.assert_called_once_with(timeout=5000)


@pytest.mark.anyio
async def test_browser_agent_click_and_trace_network_idle_timeout() -> None:
    mock_page = AsyncMock()
    mock_page.get_by_text = MagicMock()
    mock_locator = AsyncMock()
    mock_page.wait_for_load_state.side_effect = TimeoutError("Idle timeout")

    mock_get_by_text = MagicMock()
    mock_get_by_text.first = mock_locator
    mock_page.get_by_text.return_value = mock_get_by_text

    agent = BrowserAgent()
    agent.page = mock_page

    res = await agent.click_and_trace("Slow Page Link")

    assert res["action"] == "Slow Page Link"
    mock_locator.click.assert_called_once_with(timeout=5000)
    mock_page.wait_for_load_state.assert_called_once_with("networkidle", timeout=3000)


@pytest.mark.anyio
async def test_browser_agent_record_workflow(tmp_path: Path) -> None:
    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_page.get_by_text = MagicMock()
    mock_locator = AsyncMock()

    # Mock locator chain: page.get_by_text().first
    mock_get_by_text = MagicMock()
    mock_get_by_text.first = mock_locator
    mock_page.get_by_text.return_value = mock_get_by_text

    # Mock video path retrieving
    mock_video = AsyncMock()
    # Create a fake video file in tmp_path
    fake_temp_webm = tmp_path / "playwright_temp.webm"
    fake_temp_webm.write_text("fake video content")
    
    mock_video.path = AsyncMock(return_value=str(fake_temp_webm))
    mock_page.video = mock_video

    agent = BrowserAgent(record_video_dir=str(tmp_path))
    agent.page = mock_page
    agent.context = mock_context

    video_path = await agent.record_workflow(["Click 1", "Click 2"], "workflow.webm")

    # Assertions
    assert mock_page.get_by_text.call_count == 2
    mock_page.get_by_text.assert_any_call("Click 1", exact=False)
    mock_page.get_by_text.assert_any_call("Click 2", exact=False)
    assert mock_locator.click.call_count == 2
    assert mock_page.wait_for_timeout.call_count == 2
    mock_page.wait_for_timeout.assert_any_call(1500)

    # Context closed and files renamed
    mock_page.close.assert_called_once()
    mock_context.close.assert_called_once()
    
    assert agent.page is None
    assert agent.context is None

    expected_final_path = tmp_path / "workflow.webm"
    assert video_path == str(expected_final_path.resolve())
    assert expected_final_path.exists()
    assert not fake_temp_webm.exists()


@pytest.mark.anyio
async def test_browser_agent_record_workflow_graceful_error(tmp_path: Path) -> None:
    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_page.get_by_text = MagicMock()
    mock_locator = AsyncMock()
    
    # Click 1 fails, Click 2 succeeds
    mock_locator.click.side_effect = [Exception("Click failed"), None]

    mock_get_by_text = MagicMock()
    mock_get_by_text.first = mock_locator
    mock_page.get_by_text.return_value = mock_get_by_text

    mock_video = AsyncMock()
    fake_temp_webm = tmp_path / "playwright_temp.webm"
    fake_temp_webm.write_text("fake video content")
    mock_video.path = AsyncMock(return_value=str(fake_temp_webm))
    mock_page.video = mock_video

    agent = BrowserAgent(record_video_dir=str(tmp_path))
    agent.page = mock_page
    agent.context = mock_context

    video_path = await agent.record_workflow(["Failed Click", "Success Click"], "workflow.webm")

    # Assertions
    assert mock_page.get_by_text.call_count == 2
    assert mock_locator.click.call_count == 2
    mock_page.close.assert_called_once()
    mock_context.close.assert_called_once()

    expected_final_path = tmp_path / "workflow.webm"
    assert video_path == str(expected_final_path.resolve())
    assert expected_final_path.exists()
