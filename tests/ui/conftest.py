"""UI-only fixtures: browser lifecycle, page objects and failure screenshots."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from selenium.webdriver.remote.webdriver import WebDriver

from betting_qa.config import Settings
from betting_qa.ui.driver_factory import create_chrome_driver
from betting_qa.ui.pages import BettingPage

ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "screenshots"


@pytest.fixture
def driver(settings: Settings) -> Iterator[WebDriver]:
    browser = create_chrome_driver(headless=settings.headless)
    yield browser
    browser.quit()


@pytest.fixture
def betting_page(driver: WebDriver, settings: Settings) -> BettingPage:
    return BettingPage(driver, settings)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]):  # noqa: ARG001
    """Save a screenshot when a UI test fails, while the browser is still open."""
    outcome = yield
    report = outcome.get_result()
    driver = getattr(item, "funcargs", {}).get("driver")
    if report.when == "call" and report.failed and driver is not None:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        path = ARTIFACTS_DIR / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', item.name)}.png"
        driver.save_screenshot(str(path))
        report.sections.append(("screenshot", str(path)))
