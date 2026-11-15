"""Page object for the single-page betting application."""

from __future__ import annotations

from decimal import Decimal

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec

from betting_qa.config import Settings
from betting_qa.domain import parse_money
from betting_qa.ui.base_view import BaseView, Locator
from betting_qa.ui.components import (
    BetSlip,
    DateFilter,
    ErrorModal,
    MatchList,
    OddsFilter,
    ReceiptDetails,
    SuccessReceipt,
)


class PlacementFailedError(AssertionError):
    """Raised when placement ends in the error modal instead of a receipt."""


class BettingPage(BaseView):
    HEADER_BALANCE: Locator = (By.ID, "header-balance")

    # Placement includes a deliberate in-progress phase, so allow more time than for
    # ordinary element waits.
    PLACEMENT_TIMEOUT = 30.0

    def __init__(self, driver: WebDriver, settings: Settings) -> None:
        super().__init__(driver, settings.ui_timeout)
        self._settings = settings
        self.match_list = MatchList(driver, settings.ui_timeout)
        self.date_filter = DateFilter(driver, settings.ui_timeout)
        self.odds_filter = OddsFilter(driver, settings.ui_timeout)
        self.bet_slip = BetSlip(driver, settings.ui_timeout)
        self.receipt = SuccessReceipt(driver, settings.ui_timeout)
        self.error_modal = ErrorModal(driver, settings.ui_timeout)

    def open(self) -> BettingPage:
        self.driver.get(self._settings.app_url)
        self.match_list.wait_until_loaded()
        return self

    @property
    def header_balance(self) -> Decimal:
        return parse_money(self.text_of(self.HEADER_BALANCE))

    def wait_for_header_balance(self, expected: Decimal, timeout: float = 5.0) -> Decimal:
        """Give the UI a short grace period to refresh, then return what it shows."""
        return self.poll_value(
            lambda: self.header_balance, lambda value: value == expected, timeout
        )

    def place_bet(self) -> ReceiptDetails:
        """Submit the bet slip and wait for the single final outcome.

        Returns the receipt on success. Raises ``PlacementFailedError`` with the modal text
        if the error modal appears, so that a failed placement is never mistaken for a
        receipt mismatch.
        """
        self.bet_slip.submit()
        self._wait(self.PLACEMENT_TIMEOUT).until(
            ec.any_of(
                ec.visibility_of_element_located(SuccessReceipt.ROOT),
                ec.visibility_of_element_located(ErrorModal.ROOT),
            ),
            message="Neither the success receipt nor the error modal appeared",
        )
        if self.is_present(ErrorModal.ROOT):
            raise PlacementFailedError(f"Bet placement failed: {self.error_modal.message!r}")
        return self.receipt.read()
