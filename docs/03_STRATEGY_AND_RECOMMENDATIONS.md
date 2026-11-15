# Strategy and Recommendations

## 1. Why these two tests were automated

I scored every candidate on four criteria: **risk** (money or compliance impact if it regresses), **execution
frequency** (how often the journey or rule is used), **manual cost** (how tedious and error-prone it is to
check by hand), and **automation stability** (deterministic data, stable locators).

| Candidate | Risk | Frequency | Manual cost | Stability | Decision |
|-----------|------|-----------|-------------|-----------|----------|
| **E2E: one betting session (browse, filter, cancel, place, overspend)** | Critical | Every bet | High (many values in 4 places, multi-step) | High (stable `id` locators, data taken from API) | **Automated (UI)** |
| **API: placement guards (stake limits, balance, past match); rejected bet never charges** | Critical | Every request | Medium (many boundary cases) | Very high (no browser; one setup bet for the balance case) | **Automated (API)** |
| API: same-day match after kickoff rejected | Critical | Daily | Low | Low (the API has no kickoff time yet, BUG-18) | After the contract change |
| Error modal / Rebet | High | Rare | High | Low (needs a fault-injection hook) | Manual for now |
| Odds / date filters | Medium | Common | Low | Medium | Component-level later |

**E2E UI test: `test_betting_session_browse_filter_cancel_place_and_overspend`**

- It follows one realistic customer session without reloads: browse the list, filter by date and odds, clear
  the slip with Remove All, place a bet, then try to bet again with the remaining funds. It covers the most
  important journey and every component of the feature on the way.
- Its oracles come from the spec: only pre-match events are bettable; filters show exactly the matching
  events (inclusive ranges); Remove All charges nothing; *receipt values = values shown before placement*; the
  balance moves exactly once, in the UI and the backend; a stake above the balance is blocked.
- The overspend step is the UI path to the critical BUG-02: because the UI keeps a stale balance (BUG-04) and
  the API has no balance check, two ordinary bets drive the balance negative. One run reports every defect
  on the way (BUG-02/04, 03, 05, 06, 07, 15), because outcome checks use soft assertions.
- Hard asserts guard only the preconditions (the intended bet is in the slip, the target match is visible
  after filtering), so a wrong selection never produces misleading receipt failures.
- Expected values come from the live catalogue and the payout rule, not hard-coded numbers. The test avoids
  odds of exactly 2.00 (where `stake × odds` and `stake × 2` coincide) and picks an odds-filter minimum that
  doesn't equal any of the target's own odds (BUG-14 would hide the target for an unrelated reason).

**API test: `test_place_bet_rejects_invalid_bet_without_charging`** (9 cases)

- Business rule: *a bet that breaks a placement rule is rejected, and a rejected bet never moves money.*
  The cases cover stake limits, precision and type (7), stake above the available balance, and a bet on a
  past match.
- The API is the real enforcement point. The UI masks the stake input and works from a balance that can be
  stale (BUG-04), and any client (scripts, mobile, partners) can bypass the UI.
- It catches all three critical defects reachable through the API: a negative stake credits the balance
  (BUG-01), a stake above the balance drives it negative (BUG-02), and past matches are accepted (BUG-07).
- Each case checks status, the contract's error code (where one is defined) **and** that the persisted
  balance didn't change.
- It's the cheapest high-value check: no browser, about a second per case, safe to run on every commit.

Both tests reset the account via the API and read the **persisted** balance as their baseline, instead of
trusting the reset response (BUG-10).

## 2. What I intentionally left manual, and why

| Area | Why manual (for now) |
|------|----------------------|
| **Error modal, Rebet / Close / X** | Needs a deterministic way to make placement fail. The only option today is client-side request stubbing, which tests the stub more than the app. Worth automating once the backend offers a fault-injection hook (see recommendations). |
| **Double-submit / in-progress state** (BUG-08) | Timing-dependent. A reliable automated version needs control over response latency. Otherwise it's flaky in both directions. |
| **Receipt timestamp format, relative date labels ("Tuesday")** | Wording and format rules are underspecified (spec ambiguity #3). Automating them would freeze guesses into assertions. |
| **Visual layout** (fixed slip, highlighted selection, horizontal overflow at 1024 px) | Human judgement is cheaper than brittle pixel or CSS assertions at this stage. Visual regression tooling is a later step. |
| **Filters** | Lower risk (no money moves). They would be better covered by component or unit tests of the filter logic than by slow E2E tests. |
| **Exploratory testing** | Most of the high-impact defects (negative stake, past matches, stale balance leading to a negative balance) came from exploration, not from scripted cases. It should stay a recurring manual activity. |

## 3. Recommendations if the project scales

### 3.1 Clarify and harden the specification first

Several defects are really missing or contradictory rules. I'd turn these into explicit, testable acceptance
criteria before writing more automation:

- **Minimum stake:** €1.00 (Business Rules) vs €1.01 (Validation Rules).
- **Negative and zero stakes** stated explicitly, plus **insufficient balance**: HTTP status and error code.
- **Payout rounding mode** (half-up vs half-even). Money must not depend on float behaviour.
- **Event eligibility:** cut-off rule at kickoff *time*. The API currently has only a date (BUG-18),
  and past matches are bettable (BUG-07).
- **reset-balance:** the Swagger note "payload may differ from persisted balance" contradicts the spec.
- **Idempotency:** a client-generated idempotency key on `place-bet` would remove the duplicate-bet class (BUG-08) at its root.
- **Product improvements** that also make the system more testable (past-date-free calendar, unique match IDs,
  bet history by bet ID) are listed in [section 5 of the bug report](02_EXECUTION_AND_BUG_REPORTS.md#5-improvement-suggestions).

### 3.2 Test layers and CI/CD

- **Shift the pyramid down.** Most rules here are pure functions: stake validation, payout, eligibility.
  Unit tests in the app repo should cover them exhaustively. API contract tests (schema validation against
  the OpenAPI document, for example with `jsonschema`) would have caught `currency: "USD"` and
  `GET place-bet → 200` automatically. Keep E2E to a handful of critical journeys.
- **Pipeline:** lint → API tests on every PR (fast, about a minute) → UI smoke on merge to main → full
  regression nightly. Publish JUnit XML and screenshots as artifacts. A starter GitHub Actions workflow is
  included in `.github/workflows/tests.yml` (it needs a `BETTING_USER_ID` secret).
- **Reporting:** add Allure or pytest-html when the suite grows, and tag tests with bug and requirement IDs
  (as done with `negative-BUG-01`) for traceability.
- **Cross-browser:** extend the driver factory with Firefox, Edge and a remote Selenium Grid or cloud
  provider, selected through a CLI option. The page objects don't need to change.

### 3.3 Test data and environment strategy

- **One account per test (or per worker).** Today all tests share one user and one balance, so they can't
  run in parallel (`pytest-xdist`), and a crashed test leaves state behind. Ask the team for a test-only
  endpoint that creates users, sets a balance, and fixes "today", so that eligibility tests are deterministic.
- **Fault injection for the backend.** A header or flag that forces `500`, `409` or a delay on `place-bet`.
  That makes the error modal, Rebet and in-progress tests automatable and stable.
- **Seeded catalogue** with known edge cases: odds at 1.01 and 1000.00, a match kicking off today, a past
  match. Tests can then target boundaries explicitly instead of discovering them from live data.
- **Stable test hooks:** the app already exposes good `id` attributes. Ask developers to keep them as a
  contract, or add `data-testid`, so UI tests survive styling refactors.
