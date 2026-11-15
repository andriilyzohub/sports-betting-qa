"""E2E UI test: one realistic betting session, from browsing to running out of funds.

Why this test was chosen for automation
---------------------------------------
* It follows the core revenue journey the way a customer uses it, in one browser session
  without reloads: browse the match list, narrow it with the date and odds filters, change
  their mind and clear the slip, place a bet, then try to bet again with the remaining funds.
* Every stage guards money or the customer's trust, and each maps to defects found manually:

  1. Browse: only pre-match events may be offered for betting (BUG-07).
  2. Filter: the list shows exactly the events in the chosen date and odds range, and the
     counter agrees (BUG-15). The range's upper bound is the target's odds (inclusive).
  3. Cancel: "Remove All" clears the selection and charges nothing.
  4. Place: the receipt confirms what the slip showed and the balance drops by the stake,
     in the UI and in the backend (BUG-03, BUG-04, BUG-05, BUG-06).
  5. Overspend: without a reload, a stake above the remaining balance must be blocked.
     Today the UI keeps the stale balance (BUG-04) and the API has no balance check (BUG-02),
     so a normal user can drive the balance negative.

* Expected values come from live API data (catalogue, odds, persisted balance) and the payout
  rule, so the test keeps working when the catalogue changes.

Hard asserts guard preconditions (the intended bet is in the slip): if one fails, later steps
would act on the wrong selection. Every outcome check is a soft assertion, so one run reports
all mismatches instead of stopping at the first one.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from betting_qa.api import BettingApiClient
from betting_qa.domain import MIN_STAKE, Match, Selection, expected_payout
from betting_qa.ui.pages import BettingPage
from betting_qa.utils import SoftAssertions

SELECTION = Selection.HOME
FIRST_STAKE = Decimal("100.00")  # maximum stake: a boundary, and it leaves less than SECOND_STAKE
SECOND_STAKE = Decimal("50.00")
ODDS_WINDOW = Decimal("0.10")  # odds filter = [target odds - window, target odds]
MIN_ODDS = Decimal("1.01")
CENT = Decimal("0.01")


def _lower_odds_bound(match: Match, upper: Decimal) -> Decimal:
    """Lower bound of the odds filter, just below ``upper``.

    It must not equal any of the target's own odds: the app hides a match entirely when one of
    its odds equals the minimum (BUG-14), which would make the target vanish for that reason
    instead of the ones this test checks.
    """
    lower = max(upper - ODDS_WINDOW, MIN_ODDS)
    while lower in match.odds.values() and lower > MIN_ODDS:
        lower -= CENT
    return lower


@pytest.mark.ui
def test_betting_session_browse_filter_cancel_place_and_overspend(
    betting_page: BettingPage,
    api_client: BettingApiClient,
    starting_balance: Decimal,
    upcoming_match: Match,
) -> None:
    odds = upcoming_match.odds[SELECTION]
    payout = expected_payout(FIRST_STAKE, odds)
    balance_after_bet = starting_balance - FIRST_STAKE
    date_range = (date.today(), upcoming_match.kickoff_date)
    odds_range = (_lower_odds_bound(upcoming_match, odds), odds)
    assert MIN_STAKE <= balance_after_bet < SECOND_STAKE, (
        "Test data must make the 2nd stake overspend"
    )

    page = betting_page.open()
    assert page.header_balance == starting_balance, "Header must show the persisted balance on load"
    soft = SoftAssertions()

    # 1. Browse: only pre-match events may be offered for betting.
    bettable_past = page.match_list.past_matches_with_selectable_odds()
    soft.check(
        not bettable_past,
        f"{len(bettable_past)} PAST matches offer selectable odds, e.g. {bettable_past[:3]}",
    )

    # 2. Filter by date and odds: the list must show exactly the matching events.
    page.date_filter.select_range(*date_range)
    page.odds_filter.select_range(*odds_range)
    expected_ids = {
        match.id
        for match in api_client.get_matches()
        if date_range[0] <= match.kickoff_date <= date_range[1]
        and any(odds_range[0] <= value <= odds_range[1] for value in match.odds.values())
    }
    visible_ids = page.match_list.visible_match_ids()
    assert upcoming_match.id in visible_ids, "Target match must be visible after filtering"
    soft.equal(set(visible_ids), expected_ids, "Matches shown for the date and odds filters")
    soft.equal(page.match_list.shown_count, len(visible_ids), "'Showing N matches' counter")

    # 3. Cancel: a selection cleared with "Remove All" leaves no bet and no charge.
    page.match_list.select_odds(upcoming_match.id, SELECTION)
    page.bet_slip.enter_stake(str(FIRST_STAKE))
    page.bet_slip.remove_all()
    soft.check(page.bet_slip.is_empty(), "Bet slip must be empty after Remove All")
    soft.check(
        not page.match_list.is_selected(upcoming_match.id, SELECTION),
        "Odds button must not stay selected after Remove All",
    )
    soft.equal(page.header_balance, starting_balance, "Header balance after Remove All")
    soft.equal(api_client.get_balance(), starting_balance, "Persisted balance after Remove All")

    # 4. Place: preconditions prove the intended bet is in the slip (hard asserts).
    page.match_list.select_odds(upcoming_match.id, SELECTION)
    slip = page.bet_slip
    assert slip.selection_count == 1
    assert slip.match_label == upcoming_match.display_name
    assert slip.market_label == f"Match Winner: {SELECTION.label}"
    assert slip.odds == odds

    slip.enter_stake(str(FIRST_STAKE))
    soft.equal(slip.total_stake, FIRST_STAKE, "Slip total stake")
    soft.equal(slip.potential_payout, payout, "Slip potential payout (stake × odds)")

    receipt = page.place_bet()
    soft.check(bool(receipt.bet_id), "Receipt must show a bet id")
    soft.equal(receipt.match, upcoming_match.display_name, "Receipt match (home team first)")
    soft.check(
        SELECTION.label in receipt.full_text,
        f"Receipt must show the selection {SELECTION.label!r}; got {receipt.full_text!r}",
    )
    soft.equal(receipt.stake, FIRST_STAKE, "Receipt stake")
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

    # 5. Overspend: in the same session, a stake above the remaining balance must be blocked.
    page.match_list.select_odds(upcoming_match.id, Selection.DRAW)
    page.bet_slip.enter_stake(str(SECOND_STAKE))
    soft.equal(
        page.bet_slip.warning,
        "Insufficient balance",
        f"Slip warning for a €{SECOND_STAKE} stake with €{balance_after_bet} left",
    )
    soft.check(
        not page.bet_slip.is_place_bet_enabled(),
        f"Place Bet must be disabled for a €{SECOND_STAKE} stake with €{balance_after_bet} left",
    )

    soft.assert_all()
