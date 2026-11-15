"""Shared helpers for page objects and page components.

All interactions go through explicit waits; there are no ``time.sleep`` calls in the framework.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from contextlib import suppress
from typing import TypeVar

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

Locator = tuple[str, str]
SELECT_ALL_MODIFIER = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL
T = TypeVar("T")


class BaseView:
    """Base class for anything that wraps a part of the UI."""

    def __init__(self, driver: WebDriver, timeout: float) -> None:
        self.driver = driver
        self.timeout = timeout

    def _wait(self, timeout: float | None = None) -> WebDriverWait:
        return WebDriverWait(self.driver, timeout or self.timeout)

    def find_visible(self, locator: Locator, timeout: float | None = None) -> WebElement:
        return self._wait(timeout).until(
            ec.visibility_of_element_located(locator),
            message=f"Element {locator} not visible",
        )

    def click(self, locator: Locator) -> None:
        self._wait().until(
            ec.element_to_be_clickable(locator), message=f"Element {locator} not clickable"
        ).click()

    def type_into(self, locator: Locator, text: str) -> None:
        """Replace a field's value the way a user does (select all, then type), so that
        JavaScript frameworks receive real input events."""
        field = self.find_visible(locator)
        field.click()
        field.send_keys(SELECT_ALL_MODIFIER, "a")
        field.send_keys(text)

    def text_of(self, locator: Locator) -> str:
        return self.find_visible(locator).text.strip()

    def is_present(self, locator: Locator) -> bool:
        return bool(self.driver.find_elements(*locator))

    def wait_until_gone(self, locator: Locator) -> None:
        self._wait().until(
            ec.invisibility_of_element_located(locator), message=f"{locator} still visible"
        )

    def poll_value(
        self, read: Callable[[], T], is_expected: Callable[[T], bool], timeout: float
    ) -> T:
        """Poll ``read`` until ``is_expected`` holds or the timeout expires.

        Returns the last observed value instead of raising, so the caller can report the
        actual value in a meaningful assertion message.
        """
        observed: list[T] = []

        def _condition(_: WebDriver) -> bool:
            observed.append(read())
            return is_expected(observed[-1])

        with suppress(TimeoutException):
            self._wait(timeout).until(_condition)
        return observed[-1] if observed else read()
