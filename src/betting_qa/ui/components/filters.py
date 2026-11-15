"""Match list filters: date (single day or inclusive range) and odds (min/max)."""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal

from selenium.webdriver.common.by import By

from betting_qa.ui.base_view import BaseView, Locator

_MONTHS = {name: number for number, name in enumerate(calendar.month_name) if name}


class DateFilter(BaseView):
    TOGGLE: Locator = (By.ID, "date-filter-toggle")
    POPOVER: Locator = (By.ID, "date-filter-popover")
    CUSTOM_TAB: Locator = (
        By.XPATH,
        "//div[@id='date-filter-popover']//button[normalize-space()='Custom']",
    )
    MONTH_LABEL: Locator = (By.ID, "month-label")
    PREVIOUS_MONTH: Locator = (By.ID, "prev-month")
    NEXT_MONTH: Locator = (By.ID, "next-month")
    APPLY: Locator = (By.ID, "apply-date")

    @staticmethod
    def _day_cell(day: int) -> Locator:
        return By.XPATH, f"//div[@id='calendar-grid']/button[normalize-space()='{day}']"

    def select_range(self, start: date, end: date) -> None:
        """Pick start and end days in the calendar and apply (both days inclusive)."""
        self.click(self.TOGGLE)
        self.click(self.CUSTOM_TAB)
        for day in (start, end):
            self._show_month(day)
            self.click(self._day_cell(day.day))
        self.click(self.APPLY)
        self.wait_until_gone(self.POPOVER)

    def _show_month(self, day: date) -> None:
        for _ in range(24):
            month_name, year = self.text_of(self.MONTH_LABEL).split()
            shown = (int(year), _MONTHS[month_name])
            if shown == (day.year, day.month):
                return
            self.click(self.NEXT_MONTH if shown < (day.year, day.month) else self.PREVIOUS_MONTH)
        raise AssertionError(f"Calendar could not navigate to {day:%B %Y}")


class OddsFilter(BaseView):
    TOGGLE: Locator = (By.ID, "odds-filter-toggle")
    POPOVER: Locator = (By.ID, "odds-filter-popover")
    MIN_INPUT: Locator = (By.XPATH, "(//div[@id='odds-filter-popover']//input[@type='number'])[1]")
    MAX_INPUT: Locator = (By.XPATH, "(//div[@id='odds-filter-popover']//input[@type='number'])[2]")
    APPLY: Locator = (
        By.XPATH,
        "//div[@id='odds-filter-popover']//button[normalize-space()='Apply']",
    )

    def select_range(self, minimum: Decimal, maximum: Decimal) -> None:
        self.click(self.TOGGLE)
        self.type_into(self.MIN_INPUT, f"{minimum:.2f}")
        self.type_into(self.MAX_INPUT, f"{maximum:.2f}")
        self.click(self.APPLY)
        self.wait_until_gone(self.POPOVER)
