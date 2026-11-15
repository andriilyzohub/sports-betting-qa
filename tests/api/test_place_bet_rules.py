"""API business-rule test: money guards on ``POST /api/place-bet``.

Why this test was chosen for automation
---------------------------------------
* The API is the real enforcement point. The UI masks the stake input (no minus sign, at most
  2 decimals) and works from a balance that can be stale (BUG-04), but any client can call the
  API directly, so only the API can prove the rules hold.
* Every case guards money. A gap is either directly exploitable (a negative stake *credits*
  the balance, BUG-01), lets users bet money they don't have (BUG-02), or allows bets on
  matches whose result is already known (BUG-07).
* It's fast, needs no browser, and covers many boundaries cheaply: the best cost/value ratio
  for regression on every deploy.

Business rule under test: **a bet that breaks a placement rule is rejected, and a rejected bet
never moves money.** Each case checks the HTTP status, the error code from the OpenAPI contract
(where the contract defines one) and that the persisted balance is unchanged.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import pytest

from betting_qa.api import BettingApiClient
from betting_qa.domain import Match, Selection


@dataclass(frozen=True)
class BetContext:
    """What a case may use to prepare its request."""

    api: BettingApiClient
    upcoming_match: Match
    past_match: Match


@dataclass(frozen=True)
class RejectedBet:
    """The request to send and the rejection expected for it."""

    match_id: str
    stake: Any
    expected_error: str | None  # None: status-only check, the contract defines no code


CaseBuilder = Callable[[BetContext], RejectedBet]


def invalid_stake(stake: Any, expected_error: str) -> CaseBuilder:
    """A valid upcoming match with an invalid stake (limits, precision, type, sign)."""
    return lambda ctx: RejectedBet(ctx.upcoming_match.id, stake, expected_error)


def stake_above_balance(ctx: BetContext) -> RejectedBet:
    """Stake = balance + €0.01, kept under the €100 maximum so that only the balance rule
    can reject it. A valid €50 bet first brings the balance below the maximum stake."""
    setup = ctx.api.place_bet(ctx.upcoming_match.id, Selection.HOME, 50)
    assert setup.status_code == 200, f"Setup bet failed: {setup.text}"
    stake = ctx.api.get_balance() + Decimal("0.01")
    return RejectedBet(ctx.upcoming_match.id, float(stake), "insufficient_balance")


def bet_on_past_match(ctx: BetContext) -> RejectedBet:
    """A valid stake on a match that has already been played (pre-match betting only).
    The contract defines no error code for this case, so only the status is asserted."""
    return RejectedBet(ctx.past_match.id, 10, None)


CASES = [
    pytest.param(invalid_stake(0.99, "invalid_stake_min"), id="below-minimum-0.99"),
    pytest.param(invalid_stake(0, "invalid_stake_min"), id="zero"),
    pytest.param(invalid_stake(-5, "invalid_stake_min"), id="negative-BUG-01"),
    pytest.param(invalid_stake(100.01, "invalid_stake_max"), id="above-maximum-100.01"),
    pytest.param(invalid_stake(5.555, "invalid_stake_precision"), id="three-decimal-places"),
    pytest.param(invalid_stake("10", "invalid_stake_type"), id="numeric-string"),
    pytest.param(invalid_stake(None, "invalid_stake_type"), id="null"),
    pytest.param(stake_above_balance, id="above-balance-BUG-02"),
    pytest.param(bet_on_past_match, id="past-match-BUG-07"),
]


@pytest.mark.api
@pytest.mark.usefixtures("clean_account")
@pytest.mark.parametrize("build_case", CASES)
def test_place_bet_rejects_invalid_bet_without_charging(
    api_client: BettingApiClient,
    upcoming_match: Match,
    past_match: Match,
    build_case: CaseBuilder,
) -> None:
    case = build_case(BetContext(api_client, upcoming_match, past_match))
    balance_before = api_client.get_balance()

    response = api_client.place_bet(case.match_id, Selection.HOME, case.stake)

    assert response.status_code == 422, (
        f"{case} must be rejected with 422, got {response.status_code}: {response.text}"
    )
    if case.expected_error is not None:
        assert response.json().get("error") == case.expected_error
    assert api_client.get_balance() == balance_before, "A rejected bet must not change the balance"
