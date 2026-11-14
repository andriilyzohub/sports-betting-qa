"""Run-time settings shared by API and UI tests.

Values come from pytest command-line options, which fall back to environment variables
(see ``tests/conftest.py``), so the same suite runs locally and in CI without code changes.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_BASE_URL = "https://qae-assignment-tau.vercel.app"


@dataclass(frozen=True)
class Settings:
    """Immutable configuration for one test session."""

    base_url: str
    user_id: str
    headless: bool = True
    ui_timeout: float = 15.0
    api_timeout: float = 15.0

    def __post_init__(self) -> None:
        if not self.user_id:
            raise ValueError("A user id is required (use --user-id or BETTING_USER_ID).")
        # Normalise once so that callers can safely join paths with "/".
        object.__setattr__(self, "base_url", self.base_url.rstrip("/"))

    @property
    def app_url(self) -> str:
        """Entry URL of the web application for the configured user."""
        return f"{self.base_url}/?user-id={self.user_id}"
