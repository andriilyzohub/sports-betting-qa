"""Placement outcome modals: success receipt and error modal."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from selenium.webdriver.common.by import By

from betting_qa.domain import parse_money
from betting_qa.ui.base_view import BaseView, Locator


@dataclass(frozen=True)
class ReceiptDetails:
    """Snapshot of everything the success receipt displays."""

    bet_id: str
    match: str
    stake: Decimal
    odds: Decimal
    payout: Decimal
    placed_at: str
    full_text: str


class SuccessReceipt(BaseView):
    ROOT: Locator = (By.ID, "modal-success")
    BET_ID: Locator = (By.ID, "modal-success-bet-id")
    MATCH: Locator = (By.ID, "modal-success-match")
    STAKE: Locator = (By.ID, "modal-success-stake")
    ODDS: Locator = (By.ID, "modal-success-odds")
    PAYOUT: Locator = (By.ID, "modal-success-payout")
    PLACED_AT: Locator = (By.ID, "modal-success-placed-at")
    CLOSE_BUTTON: Locator = (By.ID, "modal-success-close")

    def read(self) -> ReceiptDetails:
        return ReceiptDetails(
            bet_id=self.text_of(self.BET_ID),
            match=self.text_of(self.MATCH),
            stake=parse_money(self.text_of(self.STAKE)),
            odds=parse_money(self.text_of(self.ODDS)),
            payout=parse_money(self.text_of(self.PAYOUT)),
            placed_at=self.text_of(self.PLACED_AT),
            full_text=self.text_of(self.ROOT),
        )

    def close(self) -> None:
        self.click(self.CLOSE_BUTTON)
        self.wait_until_gone(self.ROOT)


class ErrorModal(BaseView):
    ROOT: Locator = (By.ID, "modal-error")
    MESSAGE: Locator = (By.ID, "modal-error-message")
    REBET_BUTTON: Locator = (By.ID, "modal-error-rebet")
    CLOSE_BUTTON: Locator = (By.ID, "modal-error-close")

    @property
    def message(self) -> str:
        return self.text_of(self.ROOT)
