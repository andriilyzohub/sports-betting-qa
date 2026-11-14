"""Session-wide fixtures shared by API and UI tests."""

from __future__ import annotations

import os
from collections.abc import Iterator
from decimal import Decimal

import pytest

from betting_qa.api import BettingApiClient
from betting_qa.config import DEFAULT_BASE_URL, Settings
from betting_qa.domain import Match, Selection


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes"}


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("betting", "Sports Betting QA settings")
    group.addoption(
        "--app-url",
        default=os.getenv("BETTING_BASE_URL", DEFAULT_BASE_URL),
        help="Application base URL (env: BETTING_BASE_URL).",
    )
    group.addoption(
        "--user-id",
        default=os.getenv("BETTING_USER_ID", ""),
        help="User id for ?user-id= and the x-user-id header (env: BETTING_USER_ID).",
    )
    group.addoption(
        "--headed",
        action="store_true",
        default=_env_flag("BETTING_HEADED"),
        help="Run Chrome with a visible window (env: BETTING_HEADED=1).",
    )
    group.addoption(
        "--ui-timeout",
        type=float,
        default=float(os.getenv("BETTING_UI_TIMEOUT", "15")),
        help="Default explicit-wait timeout in seconds.",
    )


@pytest.fixture(scope="session")
def settings(pytestconfig: pytest.Config) -> Settings:
    user_id = pytestconfig.getoption("--user-id")
    if not user_id:
        pytest.exit("Provide a user id via --user-id=<id> or BETTING_USER_ID.", returncode=4)
    return Settings(
        base_url=pytestconfig.getoption("--app-url"),
        user_id=user_id,
        headless=not pytestconfig.getoption("--headed"),
        ui_timeout=pytestconfig.getoption("--ui-timeout"),
    )


@pytest.fixture(scope="session")
def api_client(settings: Settings) -> Iterator[BettingApiClient]:
    client = BettingApiClient(settings.base_url, settings.user_id, timeout=settings.api_timeout)
    yield client
    client.close()


@pytest.fixture
def starting_balance(api_client: BettingApiClient) -> Decimal:
    """Put the account in a known state and return the *persisted* balance.

    The reset response body is ignored on purpose: it doesn't match the stored value
    (BUG-10), and tests must compare against what the backend actually holds.
    """
    api_client.reset_balance()
    return api_client.get_balance()


@pytest.fixture(scope="session")
def upcoming_match(api_client: BettingApiClient) -> Match:
    """First match with kickoff after today, taken from the live catalogue so tests don't
    break when fixtures roll over.

    Matches with home odds of exactly 2.00 are skipped: there, stake × odds equals
    stake × 2, which would hide a whole class of payout calculation errors.
    """
    candidates = [
        match
        for match in api_client.get_matches()
        if match.is_upcoming() and match.odds[Selection.HOME] != Decimal("2")
    ]
    if not candidates:
        pytest.skip("No upcoming match available in the catalogue")
    return candidates[0]
