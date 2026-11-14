# Test Plan: Single Bet Placement

**Scope:** Single Bet Placement feature (match list → bet slip → placement → receipt / error modal) and the
backing API (`/api/matches`, `/api/balance`, `/api/place-bet`, `/api/reset-balance`).
**Sources:** *Single Bet Placement Feature Specification*, OpenAPI spec (`/api/docs?format=json`), assignment domain context.
**Environment:** https://qae-assignment-tau.vercel.app/?user-id=`<user-id>`, desktop Chrome.

## How the scenarios were selected

This is a real-money flow, so I ranked risk by **financial and regulatory impact first** and by usage frequency second:

1. **Money integrity.** Balance, stake and payout must always be correct. An error here costs the operator
   money directly or misleads the customer about their winnings.
2. **Business-rule enforcement at the API.** The UI is only one client. Every rule the spec marks "UI + API"
   must hold when the API is called directly.
3. **Bet eligibility.** Accepting bets on events that already happened is a known way to lose money, and it
   is a compliance risk.
4. **Resilience of the placement interaction.** Failures, retries and repeated clicks must not create
   duplicate bets or lose bets.
5. **Discovery features** (filters). They are visible to users, but a defect here costs money only indirectly.

Each scenario covers one risk with several targeted checks. I avoided exhaustive permutations on purpose.
Boundary values are chosen around the spec limits (€1.00 / €100.00 / balance / 2 decimal places).

| ID | Title | Priority | Type |
|----|-------|----------|------|
| TC-01 | Place a single bet on an upcoming match (end to end, values consistent everywhere) | **Critical** | Happy path |
| TC-02 | Stake cannot exceed available balance; balance never goes negative | **Critical** | Negative + boundary |
| TC-03 | Stake limits and format are enforced in UI and API (min, max, precision, sign, type) | **High** | Validation + boundary |
| TC-04 | Placement failure, retry and repeated submit don't lose or duplicate bets | High | Negative / resilience |
| TC-05 | Only upcoming (pre-match) events can be bet on | High | Business rule |
| TC-06 | Odds filter: inclusive range and invalid-range feedback | Medium | Validation + boundary |

TC-01, TC-02 and TC-03 are the top-3 scenarios executed in [02_EXECUTION_AND_BUG_REPORTS.md](02_EXECUTION_AND_BUG_REPORTS.md).

---

## TC-01: Place a single bet on an upcoming match (end to end)

**Priority:** Critical

**Risk rationale:** This is the core revenue journey and is executed on every bet. It touches every
money-related value: odds, stake, payout and balance, shown in four places (slip, receipt, header, API). An
inconsistency here either misinforms the customer (a regulatory and trust problem) or misstates the operator's
liability. The spec explicitly requires receipt values to be *consistent with what was shown before placement*.

**Preconditions:** Balance reset via `POST /api/reset-balance`. Current balance read with `GET /api/balance` (B).
Pick an upcoming match whose home odds (O) are not 2.00, so that `stake × odds` can't coincide with simpler
wrong formulas.

**Steps**
1. Open the app with `?user-id=<id>`. Note the header balance.
2. Click the **1** (home) odds button of the chosen match.
3. Check the bet slip: count = 1, "`<Home> vs <Away>`", "Match Winner: Home", "Odds: O".
4. Enter stake **10** and check Total Stake and Potential Payout.
5. Click **Place Bet**. Watch the button state.
6. When the receipt appears, compare every field with steps 3–4.
7. Check the header balance and `GET /api/balance`.
8. Close the receipt.

**Expected result**
- Step 3: the selected button is highlighted and the slip shows exactly one selection, with the home team listed first.
- Step 4: Total Stake = €10.00. Potential Payout = €(10 × O), rounded to 2 decimal places.
- Step 5: the button shows **Placing...** and can't be activated again until the request resolves.
- Step 6: the receipt shows a Bet ID, "`<Home> vs <Away>`" (home first), selection = Home, stake €10.00,
  odds O, potential payout equal to the slip value, and a placement timestamp.
- Step 7: header, bet slip and API all show B − 10.00 (EUR).
- Step 8: the slip returns to the empty state ("Select odds to place a bet") and no odds button stays selected.

---

## TC-02: Stake cannot exceed the available balance

**Priority:** Critical

**Risk rationale:** If a stake larger than the balance is accepted, the customer bets money they don't have.
The operator then carries unfunded liability, and the platform effectively gives credit, which is a licensing
issue in most jurisdictions. The spec requires the check in **both** the UI and the API. The UI check is only
as good as the balance it holds, so the test also covers a stale balance after a bet.

**Preconditions:** Balance B < €100, so the balance limit is reached before the max-stake limit. For example,
reset, then place an API bet so that B = €30.00.

**Steps**
1. Reload the app. Select any upcoming odds.
2. Enter stake = **B** (exact balance), then **B + 0.01**, then **50**.
3. With stake = B, place the bet. Close the receipt.
4. *Without reloading*, select another odds button and enter stake = B again. Try to place it.
5. API: `POST /api/place-bet` with `stake` = current balance + 0.01 (still ≤ 100).
6. Check `GET /api/balance` after each step.

**Expected result**
- Step 2: stake = B is allowed. B + 0.01 and 50 show **"Insufficient balance"** and Place Bet is disabled.
- Step 3: the bet succeeds and the balance becomes €0.00 in the header, the slip and the API.
- Step 4: the slip shows **"Insufficient balance"** (the balance is €0.00), and the bet can't be placed.
- Step 5: `422` with error `insufficient_balance`. The balance doesn't change.
- Step 6: the balance is never negative.

---

## TC-03: Stake limits and format are enforced in UI and API

**Priority:** High

**Risk rationale:** Stake limits (€1.00–€100.00, at most 2 decimal places, positive) are the operator's
exposure controls and responsible-gambling guardrails. The UI masks input, but any client can call the API
directly. A gap at the API (for example a negative stake) is directly exploitable for money. Boundary values are
where off-by-one and precision bugs live.

**Steps (UI)**: select any upcoming odds, then enter each value in the stake field:

| Input | Expected UI behaviour |
|-------|-----------------------|
| *(empty)* | Place Bet disabled, no error shown |
| `0.99` | "Minimum stake is €1.00", Place Bet disabled |
| `1.00` | Valid; payout = 1 × odds |
| `100.00` | Valid; payout = 100 × odds |
| `100.01` | "Maximum stake is €100.00", Place Bet disabled |
| `1.234` | Input limited to 2 decimal places (`1.23`) |
| `abc`, `-5`, `1e2` | Non-numeric characters and signs rejected by the input mask |

**Steps (API)**: `POST /api/place-bet` against an upcoming match with:

| `stake` | Expected |
|---------|----------|
| `0`, `0.99`, `-5` | `422 invalid_stake_min` |
| `100.01`, `101` | `422 invalid_stake_max` |
| `5.555` | `422 invalid_stake_precision` |
| `"10"`, `"abc"`, `null`, missing | `422 invalid_stake_type` |
| `1.00`, `100.00` | `200`, payout = stake × odds, currency `EUR` |

**Expected result:** every rejected request leaves `GET /api/balance` unchanged, and every accepted request
deducts exactly the stake.

---

## TC-04: Placement failure, retry and repeated submit

**Priority:** High

**Risk rationale:** Network or server failures and impatient double-clicks are common in production. A lost
bet (charged but not confirmed) or a duplicated bet (charged twice) leads to disputes and refunds. The spec
defines an in-progress state, a single final outcome, an error modal with Rebet / Close / X, and a `409` for a
bet already in progress.

**Steps**
1. Select odds, enter stake 5. Simulate a failed placement: block or stub `/api/place-bet` to return 500
   (DevTools request blocking, a proxy, or a test hook).
2. Click Place Bet. Wait for the outcome.
3. Click **Rebet** with the API healthy again.
4. Repeat steps 1–2 and click **Close**. Repeat again and click the top-right **X**.
5. With a healthy API, click **Place Bet** quickly 2–3 times.
6. Check `GET /api/balance` after each step.

**Expected result**
- Step 2: "Placing..." shows, then the modal "**Something went wrong**" with an explanation and a suggestion to retry. No deduction.
- Step 3: the modal closes, the bet is retried once and the success receipt is shown. Deduction = one stake.
- Step 4: Close and X both close the modal and clear the selection and stake. No deduction.
- Step 5: exactly **one** bet is placed and one stake is deducted. The button is inactive while placing.

---

## TC-05: Only upcoming (pre-match) events can be bet on

**Priority:** High

**Risk rationale:** The spec scopes the feature to *upcoming / pre-match events only*. Accepting a bet on a
match that already started or finished lets a customer bet with a known result. This is the classic way
sportsbooks lose money, and it is a regulatory breach.

**Steps**
1. `GET /api/matches`. Compare each `kickoffDate` with today's date.
2. In the UI, find a match labelled **PAST**. Try to select its odds and place a €2 bet.
3. API: `POST /api/place-bet` with the `matchId` of a past match.
4. For a match dated today, check that the kickoff time is shown and that betting closes at kickoff.

**Expected result**
- Step 1: the list contains only upcoming matches. If past matches are listed for information, they are clearly marked.
- Step 2: odds of past matches can't be selected (disabled or hidden).
- Step 3: the request is rejected with `422`. The balance doesn't change.
- Step 4: the kickoff date **and time** are shown, and after kickoff the odds are disabled and the API rejects bets.

---

## TC-06: Odds filter, inclusive range and invalid-range feedback

**Priority:** Medium

**Risk rationale:** The spec explicitly requires an inclusive min/max range and *clear feedback for invalid
ranges*. A wrong filter hides markets from users, which costs turnover, and invalid input without feedback
makes users think the list is empty. The impact is lower than in TC-01–05 because no money moves.

**Steps**
1. Open **Odds** filter. Set Min = 1.35, Max = 1.45 → Apply.
2. Set Min = 7.20, Max = 7.50 → Apply.
3. Set Min = 5.00, Max = 2.00 → Apply.
4. Reset.

**Expected result**
- Steps 1–2: matches with any odds equal to the boundary values (1.35, 1.45, 7.20, 7.50) are included. The
  "Showing N matches" counter reflects the filtered count.
- Step 3: the range is rejected with a visible validation message, and the filter is not applied.
- Step 4: all matches are shown again.

---

## Out of scope / not covered by this plan

Live betting, multi-bets, other sports and mobile UX are out of scope per the spec. Cross-browser testing,
performance and accessibility are not covered in this short plan. The recommendations note lists them for later.
