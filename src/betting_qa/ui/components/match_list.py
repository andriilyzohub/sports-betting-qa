"""Match list component: match cards with 1 / X / 2 odds buttons."""

from __future__ import annotations

import re
from decimal import Decimal

from selenium.webdriver.common.by import By

from betting_qa.domain import Selection, parse_money
from betting_qa.ui.base_view import BaseView, Locator


class MatchList(BaseView):
    ROOT: Locator = (By.ID, "match-list")
    ANY_CARD: Locator = (By.CSS_SELECTOR, "#match-list [id^='match-card-']")
    SHOWN_COUNT: Locator = (By.ID, "match-list-count")
    CARD_PREFIX = "match-card-"

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

    def visible_match_ids(self) -> list[str]:
        cards = self.driver.find_elements(*self.ANY_CARD)
        return [card.get_attribute("id").removeprefix(self.CARD_PREFIX) for card in cards]

    @property
    def shown_count(self) -> int:
        """Number from the "Showing N matches" label."""
        match = re.search(r"\d+", self.text_of(self.SHOWN_COUNT))
        if match is None:
            raise ValueError("Match counter has no number")
        return int(match.group())

    def past_matches_with_selectable_odds(self) -> list[str]:
        """IDs of cards labelled PAST whose odds buttons can still be clicked."""
        offending = []
        for card in self.driver.find_elements(*self.ANY_CARD):
            badge = card.find_elements(By.CSS_SELECTOR, ".badge")
            if not badge or badge[0].text.strip().upper() != "PAST":
                continue
            buttons = card.find_elements(By.CSS_SELECTOR, "button.oddsButton")
            if any(button.is_enabled() for button in buttons):
                offending.append(card.get_attribute("id").removeprefix(self.CARD_PREFIX))
        return offending
