"""Thin client for the Sports Betting REST API.

Design notes:
* Methods that test business rules return the raw ``requests.Response`` so tests can assert
  on status codes and error bodies, including for deliberately invalid input.
* Convenience methods (``get_matches``, ``get_balance``) raise on unexpected status codes,
  because tests use them for setup and verification, not as the behaviour under test.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

import requests

from betting_qa.domain import Match, Selection, to_decimal

logger = logging.getLogger(__name__)

USER_ID_HEADER = "x-user-id"


class BettingApiClient:
    """API client bound to one base URL and one user context."""

    def __init__(
        self,
        base_url: str,
        user_id: str,
        timeout: float = 15.0,
        session: requests.Session | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = session or requests.Session()
        self._session.headers.update({USER_ID_HEADER: user_id, "Accept": "application/json"})

    # ----------------------------------------------------------------- endpoints

    def get_matches(self) -> list[Match]:
        response = self._request("GET", "/api/matches")
        self._expect_ok(response)
        return [Match.from_api(item) for item in response.json()]

    def get_balance(self) -> Decimal:
        """Current persisted balance; the source of truth for balance assertions."""
        response = self._request("GET", "/api/balance")
        self._expect_ok(response)
        return to_decimal(response.json()["balance"])

    def reset_balance(self) -> requests.Response:
        """Reset the balance. Read the result back with ``get_balance`` instead of trusting
        this response body (see BUG-10: response and persisted value differ)."""
        return self._request("POST", "/api/reset-balance")

    def place_bet(self, match_id: str, selection: Selection | str, stake: Any) -> requests.Response:
        """Place a bet. ``stake`` is deliberately untyped so that tests can send invalid
        values (strings, ``None``, too many decimals) exactly as a hostile client would."""
        payload = {
            "matchId": match_id,
            "selection": selection.value if isinstance(selection, Selection) else selection,
            "stake": stake,
        }
        return self.place_bet_raw(json=payload)

    def place_bet_raw(self, *, json: Any = None, data: str | None = None) -> requests.Response:
        """Send an arbitrary body to the place-bet endpoint (protocol-level tests)."""
        headers = {"Content-Type": "application/json"} if data is not None else None
        return self._request("POST", "/api/place-bet", json=json, data=data, headers=headers)

    def close(self) -> None:
        self._session.close()

    # ----------------------------------------------------------------- internals

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = f"{self._base_url}{path}"
        response = self._session.request(method, url, timeout=self._timeout, **kwargs)
        logger.info("%s %s -> %s %s", method, path, response.status_code, response.text[:300])
        return response

    @staticmethod
    def _expect_ok(response: requests.Response) -> None:
        if response.status_code != 200:
            raise AssertionError(
                f"Unexpected {response.status_code} from {response.request.method} "
                f"{response.url}: {response.text[:500]}"
            )
