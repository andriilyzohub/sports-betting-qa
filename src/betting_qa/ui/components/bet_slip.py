"""Bet slip component: the right-hand panel with the active selection, stake and totals."""

from __future__ import annotations

from decimal import Decimal

from selenium.webdriver.common.by import By

from betting_qa.domain import parse_money
from betting_qa.ui.base_view import BaseView, Locator


class BetSlip(BaseView):
    SELECTION_COUNT: Locator = (By.ID, "bet-slip-count")
    EMPTY_STATE: Locator = (By.CSS_SELECTOR, "#bet-slip .betSlipBodyEmpty")
    SELECTION_TEAMS: Locator = (By.CSS_SELECTOR, "#bet-slip .betSelectionTeams")
    SELECTION_MARKET: Locator = (By.CSS_SELECTOR, "#bet-slip .betSelectionMarket")
    SELECTION_ODDS: Locator = (By.CSS_SELECTOR, "#bet-slip .betSelectionOdds")
    STAKE_INPUT: Locator = (By.ID, "bet-slip-stake-input")
    TOTAL_STAKE: Locator = (By.ID, "bet-slip-total-stake")
    POTENTIAL_PAYOUT: Locator = (By.ID, "bet-slip-potential-payout")
    PLACE_BET_BUTTON: Locator = (By.ID, "bet-slip-place-bet")

    @property
    def selection_count(self) -> int:
        return int(self.text_of(self.SELECTION_COUNT))

    @property
    def match_label(self) -> str:
        return self.text_of(self.SELECTION_TEAMS)

    @property
    def market_label(self) -> str:
        return self.text_of(self.SELECTION_MARKET)

    @property
    def odds(self) -> Decimal:
        return parse_money(self.text_of(self.SELECTION_ODDS))

    @property
    def total_stake(self) -> Decimal:
        return parse_money(self.text_of(self.TOTAL_STAKE))

    @property
    def potential_payout(self) -> Decimal:
        return parse_money(self.text_of(self.POTENTIAL_PAYOUT))

    def enter_stake(self, stake: str) -> None:
        field = self.find_visible(self.STAKE_INPUT)
        field.clear()
        field.send_keys(stake)

    def submit(self) -> None:
        self.click(self.PLACE_BET_BUTTON)

    def is_empty(self) -> bool:
        return self.is_present(self.EMPTY_STATE)
