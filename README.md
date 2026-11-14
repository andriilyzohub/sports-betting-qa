# Sports Betting QA: Single Bet Placement

Take-home assignment: test strategy, manual execution, bug reports and a small automation framework for the
single-bet placement flow of https://qae-assignment-tau.vercel.app.

## Deliverables

| Part | Document |
|------|----------|
| A1: Test plan (6 prioritized scenarios) | [docs/01_TEST_PLAN.md](docs/01_TEST_PLAN.md) |
| A2: Execution results and bug reports (20 defects, 4 critical) | [docs/02_EXECUTION_AND_BUG_REPORTS.md](docs/02_EXECUTION_AND_BUG_REPORTS.md) |
| B: Automation framework and 2 tests | this README, `src/`, `tests/` |
| C: Strategy and recommendations | [docs/03_STRATEGY_AND_RECOMMENDATIONS.md](docs/03_STRATEGY_AND_RECOMMENDATIONS.md) |

## Stack

Python 3.10+ · pytest · Selenium WebDriver 4 (desktop Chrome) · requests

Additional tooling (all optional):

- **Selenium Manager** (built into Selenium ≥ 4.6) downloads the matching chromedriver, so no manual driver setup.
- **ruff** for linting and formatting, configured in `pyproject.toml`.
- **GitHub Actions** workflow in `.github/workflows/tests.yml` as a CI starting point.

No Poetry or Allure, to keep setup to one `pip install`.

## Project structure

```
.
├── src/betting_qa/              # reusable framework code (no tests here)
│   ├── config.py                # Settings dataclass (base URL, user id, timeouts, headless)
│   ├── domain.py                # Match/Selection models, payout rule, money parsing (Decimal)
│   ├── api/client.py            # BettingApiClient: thin requests wrapper, x-user-id header
│   ├── ui/
│   │   ├── driver_factory.py    # Chrome creation and options in one place
│   │   ├── base_view.py         # explicit-wait helpers shared by pages and components
│   │   ├── components/          # MatchList, BetSlip, SuccessReceipt / ErrorModal
│   │   └── pages/betting_page.py# page object composing the components
│   └── utils/soft_assert.py     # collect multiple checks, report them together
├── tests/
│   ├── conftest.py              # CLI options, settings, API client, account reset, test match
│   ├── api/test_place_bet_stake_rules.py
│   └── ui/
│       ├── conftest.py          # driver lifecycle, page fixture, screenshot on failure
│       └── test_bet_placement_journey.py
├── docs/                        # Part A and Part C deliverables and screenshot evidence
├── pyproject.toml               # pytest, ruff and project metadata
└── requirements.txt
```

**Design choices**

- **Layers.** Tests describe *what* is verified. Page objects and components know *how* to find things
  (`id` locators only). The domain module holds business rules such as `expected_payout`. No locators or
  URLs live in tests.
- **Data from the system, not hard-coded.** The test match is picked from `GET /api/matches` (first
  upcoming match). The baseline balance is read from `GET /api/balance` after a reset.
- **Money uses `Decimal`** everywhere, with half-up rounding to cents, so float artefacts can't cause false
  passes or false failures.
- **Explicit waits only**, no `sleep`. Placement has its own longer timeout because the app shows an
  in-progress state.
- **Failure diagnostics.** API calls are logged and shown on failure. UI failures save a screenshot to
  `artifacts/screenshots/`. The E2E test reports *all* receipt and balance mismatches in one run.

## Setup

Requires Python 3.10+ and Google Chrome.

```bash
git clone <repo-url> && cd sports-betting-qa
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running the tests

The user id is required. Pass it as an option or set it as an environment variable:

```bash
export BETTING_USER_ID=<your-user-id>      # Windows (PowerShell): $env:BETTING_USER_ID="<your-user-id>"

pytest                      # everything
pytest -m api               # API tests only (no browser)
pytest -m ui                # UI test only (headless Chrome)
pytest -m ui --headed       # watch the browser
pytest --user-id=<id> -v    # pass the user id on the command line instead
```

| Option | Env variable | Default |
|--------|--------------|---------|
| `--user-id` | `BETTING_USER_ID` | *(required)* |
| `--app-url` | `BETTING_BASE_URL` | `https://qae-assignment-tau.vercel.app` |
| `--headed` | `BETTING_HEADED=1` | headless |
| `--ui-timeout` | `BETTING_UI_TIMEOUT` | `15` seconds |

> The tests reset and change the balance of the given user, and all tests share that one account.
> Don't run them in parallel (`-n`), and don't use the app manually with the same user during a run.

Lint: `pip install ruff && ruff check . && ruff format --check .`

## The two automated tests

| Test | Type | Why it was chosen |
|------|------|-------------------|
| `tests/ui/test_bet_placement_journey.py::test_single_bet_receipt_and_balance_match_bet_slip` | E2E UI | Core revenue journey. Verifies the spec rule that the receipt matches the slip, and that the balance (header and backend) drops by exactly the stake. |
| `tests/api/test_place_bet_stake_rules.py::test_place_bet_rejects_invalid_stake_without_charging` | API, 7 cases | The UI mask hides stake rule violations, so only the API can enforce them. Each case checks status, error code and an unchanged balance. |

Each test module has a docstring with the full rationale. See also
[docs/03_STRATEGY_AND_RECOMMENDATIONS.md](docs/03_STRATEGY_AND_RECOMMENDATIONS.md).

### Results on the current build (Version 1.0.0)

Last run: 2026-11-14, macOS, Python 3.13, desktop Chrome. **2 failed, 6 passed in 27 s.**

The tests are written against the specification, so on the current build they **fail by design** and each
failure maps to a reported defect:

| Test | Result | Failing checks |
|------|--------|----------------|
| API stake rules | 6 passed, **1 failed** | `negative-BUG-01`: a stake of −5 is accepted with `200` instead of `422 invalid_stake_min` |
| E2E bet placement | **failed** (soft assertions) | receipt match reversed (BUG-05), selection missing (BUG-06), receipt payout = stake × 2 (BUG-03), header balance not updated (BUG-04) |

Actual UI failure output (all bet slip checks passed; the 4 failures are app defects):

```
AssertionError: 4 check(s) failed:
  1. Receipt match (home team first): expected 'Marseille vs PSG', got 'PSG vs Marseille'
  2. Receipt must show the selection 'Home'; got '... MATCH PSG vs Marseille STAKE €10.00 ODDS 4.10 ...'
  3. Receipt potential payout (stake × odds): expected Decimal('41.00'), got Decimal('20.00')
  4. Header balance after placement: expected Decimal('110.00'), got Decimal('120.00')
```

When the bugs are fixed, the tests pass without changes.
