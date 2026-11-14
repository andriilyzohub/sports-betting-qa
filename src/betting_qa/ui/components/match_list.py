"""Match list component: match cards with 1 / X / 2 odds buttons."""

from __future__ import annotations

from decimal import Decimal

from selenium.webdriver.common.by import By

from betting_qa.domain import Selection, parse_money
from betting_qa.ui.base_view import BaseView, Locator


class MatchList(BaseView):
    ROOT: Locator = (By.ID, "match-list")
    ANY_CARD: Locator = (By.CSS_SELECTOR, "#match-list [id^='match-card-']")

    @staticmethod
    def odds_button(match_id: str, selection: Selection) -> Locator:
        return By.ID, f"odds-{match_id}-{selection.odds_key}"

    def wait_until_loaded(self) -> None:
        self.find_visible(self.ANY_CARD)

    def select_odds(self, match_id: str, selection: Selection) -> None:
        self.click(self.odds_button(match_id, selection))

    def displayed_odds(self, match_id: str, selection: Selection) -> Decimal:
        return parse_money(self.text_of(self.odds_button(match_id, selection)).splitlines()[-1])

    def is_selected(self, match_id: str, selection: Selection) -> bool:
        button = self.find_visible(self.odds_button(match_id, selection))
        return "oddsButtonSelected" in (button.get_attribute("class") or "")
