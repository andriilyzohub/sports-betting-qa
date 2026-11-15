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
    REMOVE_ALL_BUTTON: Locator = (By.ID, "bet-slip-remove-all")
    STAKE_WARNING: Locator = (By.CSS_SELECTOR, "#bet-slip .stakeWarning")

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

    @property
    def warning(self) -> str:
        """Validation message under the stake ("Insufficient balance", ...), or "" if none."""
        elements = self.driver.find_elements(*self.STAKE_WARNING)
        return elements[0].text.strip() if elements else ""

    def enter_stake(self, stake: str) -> None:
        self.type_into(self.STAKE_INPUT, stake)

    def is_place_bet_enabled(self) -> bool:
        return self.find_visible(self.PLACE_BET_BUTTON).is_enabled()

    def remove_all(self) -> None:
        self.click(self.REMOVE_ALL_BUTTON)
        self.find_visible(self.EMPTY_STATE)

    def submit(self) -> None:
        self.click(self.PLACE_BET_BUTTON)

    def is_empty(self) -> bool:
        return self.is_present(self.EMPTY_STATE)
