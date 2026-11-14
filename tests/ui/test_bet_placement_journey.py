"""E2E UI test: place a single bet and verify every money value end to end.

Why this test was chosen for automation
---------------------------------------
* It's the core revenue journey, used on every bet, and it touches every component of the
  feature: match list, bet slip, placement, receipt, and the balance in the header and backend.
* The spec requires receipt values to be *consistent with what was shown before placement*.
  Comparing slip, receipt, header and API values is tedious and error-prone by hand, and it
  is exactly what regresses silently: manual execution found a wrong receipt payout (BUG-03),
  reversed team order (BUG-05), a missing selection (BUG-06) and a stale balance (BUG-04).
* Expected values are derived from live API data (odds, persisted balance) and the payout
  rule, so the test keeps working when the match catalogue changes.

Receipt and balance checks are collected with ``SoftAssertions``, so one run reports every
mismatch instead of stopping at the first one.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from betting_qa.api import BettingApiClient
from betting_qa.domain import Match, Selection, expected_payout
from betting_qa.ui.pages import BettingPage
from betting_qa.utils import SoftAssertions

STAKE = Decimal("10.00")
SELECTION = Selection.HOME


@pytest.mark.ui
def test_single_bet_receipt_and_balance_match_bet_slip(
    betting_page: BettingPage,
    api_client: BettingApiClient,
    starting_balance: Decimal,
    upcoming_match: Match,
) -> None:
    odds = upcoming_match.odds[SELECTION]
    payout = expected_payout(STAKE, odds)
    balance_after_bet = starting_balance - STAKE

    page = betting_page.open()
    assert page.header_balance == starting_balance, "Header must show the persisted balance on load"

    # Arrange the bet slip. These are preconditions for the receipt checks, so they are hard
    # asserts: if the slip is wrong, the comparisons below would be meaningless.
    page.match_list.select_odds(upcoming_match.id, SELECTION)
    slip = page.bet_slip
    assert slip.selection_count == 1
    assert slip.match_label == upcoming_match.display_name
    assert slip.market_label == f"Match Winner: {SELECTION.label}"
    assert slip.odds == odds

    slip.enter_stake(str(STAKE))
    assert slip.total_stake == STAKE
    assert slip.potential_payout == payout, "Slip payout must equal stake × odds"

    # Act
    receipt = page.place_bet()

    # Assert: the receipt confirms exactly what was on the slip, and the money moved once.
    with SoftAssertions() as soft:
        soft.check(bool(receipt.bet_id), "Receipt must show a bet id")
        soft.equal(receipt.match, upcoming_match.display_name, "Receipt match (home team first)")
        soft.check(
            SELECTION.label in receipt.full_text,
            f"Receipt must show the selection {SELECTION.label!r}; got {receipt.full_text!r}",
        )
        soft.equal(receipt.stake, STAKE, "Receipt stake")
        soft.equal(receipt.odds, odds, "Receipt odds at placement")
        soft.equal(receipt.payout, payout, "Receipt potential payout (stake × odds)")
        soft.check(bool(receipt.placed_at), "Receipt must show a placement timestamp")

        page.receipt.close()
        soft.check(page.bet_slip.is_empty(), "Bet slip must be empty after closing the receipt")
        soft.equal(
            page.wait_for_header_balance(balance_after_bet),
            balance_after_bet,
            "Header balance after placement",
        )
        soft.equal(api_client.get_balance(), balance_after_bet, "Persisted balance after placement")
