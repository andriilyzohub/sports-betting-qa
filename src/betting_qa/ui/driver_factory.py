"""WebDriver creation. Kept separate so that browser choice and options live in one place."""

from __future__ import annotations

from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver

DEFAULT_WINDOW_SIZE = (1440, 900)


def create_chrome_driver(
    headless: bool = True, window_size: tuple[int, int] = DEFAULT_WINDOW_SIZE
) -> WebDriver:
    """Start desktop Chrome. Selenium Manager (bundled with Selenium 4.6+) downloads a
    matching chromedriver automatically, so no manual driver setup is needed."""
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    width, height = window_size
    options.add_argument(f"--window-size={width},{height}")
    options.add_argument("--disable-search-engine-choice-screen")
    # Fixed UI language: the app formats dates and month names with the browser locale.
    options.add_argument("--lang=en-GB")
    return webdriver.Chrome(options=options)
