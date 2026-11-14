"""Domain model and business rules used to calculate expected results.

Tests derive expectations from these rules rather than hard-coding numbers, so they stay
valid when match data or odds change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any

CENT = Decimal("0.01")
MIN_STAKE = Decimal("1.00")
MAX_STAKE = Decimal("100.00")

_MONEY_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")


class Selection(str, Enum):
    """Possible outcomes of a match, as accepted by the place-bet API."""

    HOME = "HOME"
    DRAW = "DRAW"
    AWAY = "AWAY"

    @property
    def odds_key(self) -> str:
        """Key of this outcome in the ``odds`` object returned by ``GET /api/matches``."""
        return self.value.lower()

    @property
    def label(self) -> str:
        """Human-readable name as shown in the bet slip ("Match Winner: Home")."""
        return self.value.capitalize()


@dataclass(frozen=True)
class Match:
    """A football match as returned by ``GET /api/matches``."""

    id: str
    competition: str
    kickoff_date: date
    home_team: str
    away_team: str
    odds: dict[Selection, Decimal]

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> Match:
        return cls(
            id=payload["id"],
            competition=payload["competition"],
            kickoff_date=date.fromisoformat(payload["kickoffDate"]),
            home_team=payload["homeTeam"],
            away_team=payload["awayTeam"],
            odds={
                selection: to_decimal(payload["odds"][selection.odds_key])
                for selection in Selection
            },
        )

    @property
    def display_name(self) -> str:
        """Fixture name with the home team first, e.g. "Chelsea vs Liverpool"."""
        return f"{self.home_team} vs {self.away_team}"

    def is_upcoming(self, today: date | None = None) -> bool:
        """True when kickoff is strictly after ``today`` (pre-match betting only)."""
        return self.kickoff_date > (today or date.today())


def to_decimal(value: Any) -> Decimal:
    """Convert a JSON number or string to ``Decimal`` without binary float artefacts."""
    return Decimal(str(value))


def expected_payout(stake: Decimal, odds: Decimal) -> Decimal:
    """Potential payout = stake × odds (stake included), rounded to cents half-up."""
    return (stake * odds).quantize(CENT, rounding=ROUND_HALF_UP)


def parse_money(text: str) -> Decimal:
    """Extract the amount from UI text such as "Balance: €-30.00", "€27.50" or "Odds: 2.75"."""
    match = _MONEY_PATTERN.search(text.replace(",", ""))
    if match is None:
        raise ValueError(f"No numeric amount found in {text!r}")
    return Decimal(match.group())
