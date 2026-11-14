"""Collect several independent checks and report them together.

An end-to-end journey verifies many values (receipt fields, balances). Stopping at the first
mismatch hides the others and costs a rerun per defect, so each check is recorded and all
failures are raised at the end in one readable message.
"""

from __future__ import annotations

from types import TracebackType
from typing import Any


class SoftAssertions:
    def __init__(self) -> None:
        self._failures: list[str] = []

    def check(self, condition: bool, message: str) -> None:
        if not condition:
            self._failures.append(message)

    def equal(self, actual: Any, expected: Any, what: str) -> None:
        self.check(actual == expected, f"{what}: expected {expected!r}, got {actual!r}")

    def assert_all(self) -> None:
        if self._failures:
            details = "\n".join(f"  {i}. {failure}" for i, failure in enumerate(self._failures, 1))
            raise AssertionError(f"{len(self._failures)} check(s) failed:\n{details}")

    def __enter__(self) -> SoftAssertions:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        # Don't mask an unexpected exception raised inside the block.
        if exc_type is None:
            self.assert_all()
