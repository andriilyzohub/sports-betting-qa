"""Match list component: match cards with 1 / X / 2 odds buttons."""

from __future__ import annotations

import re

from selenium.webdriver.common.by import By

from betting_qa.domain import Selection
from betting_qa.ui.base_view import BaseView, Locator


class MatchList(BaseView):
    ANY_CARD: Locator = (By.CSS_SELECTOR, "#match-list [id^='match-card-']")
    SHOWN_COUNT: Locator = (By.ID, "match-list-count")
    # Cards labelled PAST that still contain at least one enabled odds button.
    PAST_CARDS_WITH_SELECTABLE_ODDS: Locator = (
        By.XPATH,
        "//div[starts-with(@id, 'match-card-')]"
        "[.//span[@class='badge' and normalize-space()='PAST']]"
        "[.//button[contains(@class, 'oddsButton') and not(@disabled)]]",
    )
    CARD_PREFIX = "match-card-"

    @staticmethod
    def odds_button(match_id: str, selection: Selection) -> Locator:
        return By.ID, f"odds-{match_id}-{selection.odds_key}"

    def wait_until_loaded(self) -> None:
        self.find_visible(self.ANY_CARD)

    def select_odds(self, match_id: str, selection: Selection) -> None:
        self.click(self.odds_button(match_id, selection))

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
        cards = self.driver.find_elements(*self.PAST_CARDS_WITH_SELECTABLE_ODDS)
        return [card.get_attribute("id").removeprefix(self.CARD_PREFIX) for card in cards]
