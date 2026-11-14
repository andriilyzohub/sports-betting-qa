"""API business-rule test: stake limits on ``POST /api/place-bet``.

Why this test was chosen for automation
---------------------------------------
* The UI masks the stake input (no minus sign, at most 2 decimals), so UI tests can't prove the
  rules hold. Any client can call the API directly, which makes the API the real enforcement
  point for the operator's exposure limits.
* A gap here is directly exploitable for money. Exploratory testing found that a negative
  stake is accepted and *credits* the balance (BUG-01).
* It's fast, deterministic, needs no browser, and covers many boundary values cheaply.
  That's the best cost/value ratio for regression on every deploy.

Each case asserts three things: the HTTP status, the machine-readable error code from the
OpenAPI contract, and that the persisted balance didn't change. A rejected bet that still
moves money is the worst failure mode, so the balance check is never skipped.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from betting_qa.api import BettingApiClient
from betting_qa.domain import Match, Selection

INVALID_STAKES = [
    pytest.param(0.99, "invalid_stake_min", id="below-minimum-0.99"),
    pytest.param(0, "invalid_stake_min", id="zero"),
    pytest.param(-5, "invalid_stake_min", id="negative-BUG-01"),
    pytest.param(100.01, "invalid_stake_max", id="above-maximum-100.01"),
    pytest.param(5.555, "invalid_stake_precision", id="three-decimal-places"),
    pytest.param("10", "invalid_stake_type", id="numeric-string"),
    pytest.param(None, "invalid_stake_type", id="null"),
]


@pytest.mark.api
@pytest.mark.parametrize(("stake", "expected_error"), INVALID_STAKES)
def test_place_bet_rejects_invalid_stake_without_charging(
    api_client: BettingApiClient,
    starting_balance: Decimal,
    upcoming_match: Match,
    stake: Any,
    expected_error: str,
) -> None:
    response = api_client.place_bet(upcoming_match.id, Selection.HOME, stake)

    assert response.status_code == 422, (
        f"stake={stake!r} must be rejected with 422, got {response.status_code}: {response.text}"
    )
    assert response.json().get("error") == expected_error
    assert api_client.get_balance() == starting_balance, (
        "A rejected bet must not change the balance"
    )
