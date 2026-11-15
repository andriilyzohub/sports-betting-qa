# Execution Results and Bug Reports

**Build:** https://qae-assignment-tau.vercel.app (footer: *Version 1.0.0*)
**Date:** 2026-11-14
**Browser:** desktop Chrome, 1024×768 viewport
**API calls:** made from the browser session with header `x-user-id: <candidate id>`
**Test account state:** reset with `POST /api/reset-balance` before each scenario

## 1. Execution summary (top 3 scenarios)

| Scenario | Result | Defects |
|----------|--------|---------|
| TC-01 Place a single bet end to end | ❌ **Failed** | BUG-03, BUG-04, BUG-05, BUG-06, BUG-09 |
| TC-02 Stake cannot exceed available balance | ❌ **Failed** | BUG-02 (API has no check at all; reachable from the UI via BUG-04) |
| TC-03 Stake limits and format, UI and API | ❌ **Failed** | BUG-01 (negative stake accepted by API). All other UI and API cases passed |

### TC-01: step results

| Step | Result | Notes |
|------|--------|-------|
| Select home odds (Chelsea vs Liverpool, 2.75) | ✅ | Slip: "Chelsea vs Liverpool / Match Winner: Home / Odds: 2.75". Button highlighted |
| Stake 10 → totals | ✅ | Total Stake €10.00, Potential Payout €27.50 |
| Place Bet → in-progress state | ✅ | Button shows spinner + "Placing..." (but stays clickable, see BUG-08) |
| Receipt values match the slip | ❌ | Match shown as **"Liverpool vs Chelsea"** (BUG-05). Payout **€20.00** instead of €27.50 (BUG-03). Selection not shown (BUG-06) |
| Balance after placement | ❌ | Header and slip still show **€120.00**. API shows €110.00 (BUG-04) |
| API response for the same bet | ⚠️ | Correct payout 27.5 and balance 110, but `"currency":"USD"` (BUG-09) |
| Close receipt → slip empty | ✅ | |

The bug reproduced with a second bet (Man Utd vs Newcastle, Away 3.70, stake 7): slip payout €25.90, receipt
payout **€14.00** (= 7 × 2), match "Newcastle vs Manchester Utd".

### TC-02: step results

| Step | Result | Notes |
|------|--------|-------|
| UI, balance €30.00, stake 30 / 30.01 / 50 | ✅ | 30 allowed. 30.01 and 50 show "Insufficient balance" and Place Bet is disabled |
| Place €30 bet | ⚠️ | Succeeds. Header and slip keep showing €30.00 (BUG-04) |
| Second €30 bet without reload | ❌ | UI allows it. API accepts it. **Balance = −€30.00** (BUG-02) |
| API stake 80 with balance 74.66 | ❌ | `200`, balance **−5.34**. Then stake 1 at balance 0 → `200`, balance **−1.00** |

### TC-03: step results

| Input | UI | API |
|-------|----|-----|
| 0.99 / 0 | ✅ "Minimum stake is €1.00", disabled | ✅ `422 invalid_stake_min` |
| 1.00, 1.01 | ✅ allowed | ✅ `200`, payout correct |
| 100.00 | ✅ allowed | ✅ `200`, payout 275.00 at odds 2.75 |
| 100.01 / 101 / 150 | ✅ "Maximum stake is €100.00", disabled | ✅ `422 invalid_stake_max` |
| 1.234 / 5.555 | ✅ mask keeps `1.23` | ✅ `422 invalid_stake_precision` |
| abc / "10" / null / missing | ✅ mask rejects letters | ✅ `422 invalid_stake_type` |
| **−5** | ✅ mask strips the sign | ❌ **`200`, balance increased by €5** (BUG-01) |

## 2. Exploratory session (time-boxed)

**Charter:** *"Explore the placement flow around in-progress states, repeated actions, event eligibility,
filters and the API contract, to find ways of losing or creating money."*

| Area | Observation | Outcome |
|------|-------------|---------|
| Match list vs API | 103 matches; teams, order and all 309 odds values match the API | ✅ |
| Event eligibility | 91 of 103 matches are dated before today, marked **PAST**, listed first and fully bettable. The API has no kickoff time, so a match dated today stays bettable after kickoff | BUG-07, BUG-18 |
| Catalogue data | 33 of 103 match IDs have no date suffix and 70 do. Team names are abbreviated inconsistently | BUG-17 |
| Payout rounding | API payout is truncated to cents (1.01 × 3.70 = 3.737 → 3.73), while the slip rounds (€3.74) | BUG-20 |
| Receipt Bet ID | Generated in the browser as `#B-` + a random number from 10000–99999. The API returns no bet identifier | BUG-19 |
| Repeated clicks | "Placing..." button stays enabled. Clicks after the first response creates a second bet | BUG-08 |
| Error modal (500 injected on the client side) | Title, body, Rebet (retries once, succeeds), Close and X (clear the slip) all match the spec | ✅ |
| Selection rules | A new odds button replaces the selection; × and Remove All clear it | ✅ |
| Reset balance | Response 125.50, persisted 120.00 | BUG-10 |
| API protocol | Malformed JSON → 500; GET on `/place-bet` → 200 `{}`; missing / invalid user → 401 ✅; PUT on `/matches` → 405 ✅; array body → 400 ✅; 3 parallel requests → one `409 bet_in_progress` ✅ | BUG-11, BUG-12 |
| Odds filter | min > max accepted silently; lower bound exclusive; counter never updates | BUG-13, BUG-14, BUG-15 |
| Date filter | Single day and inclusive range (21–27 Nov) work | ✅ (counter: BUG-15) |

---

## 3. Bug reports

### Severity overview

| ID | Title | Severity |
|----|-------|----------|
| BUG-01 | API accepts a negative stake and **credits** the balance | **Critical** |
| BUG-02 | API has no insufficient-balance check; balance goes negative | **Critical** |
| BUG-07 | Bets are accepted on past matches, which are listed first (UI and API) | **Critical** |
| BUG-18 | No kickoff time; matches dated today stay bettable after kickoff | **Critical** |
| BUG-03 | Receipt shows potential payout as stake × 2 instead of stake × odds | **High** |
| BUG-04 | Header and bet slip balance aren't updated after a bet is placed | **High** |
| BUG-05 | Receipt shows the teams in reversed order (away vs home) | **High** |
| BUG-08 | "Placing..." button stays clickable; repeated clicks place duplicate bets | **High** |
| BUG-06 | Receipt doesn't show the selection | Medium |
| BUG-09 | `place-bet` response returns currency `USD` | Medium |
| BUG-10 | `reset-balance` response doesn't match the persisted balance | Medium |
| BUG-11 | Malformed JSON returns 500 instead of 400 | Medium |
| BUG-13 | Odds filter accepts min > max without feedback | Medium |
| BUG-19 | Receipt Bet ID is a random client-side number; API returns no bet id | Medium |
| BUG-20 | API truncates the payout instead of rounding; it differs from the bet slip | Medium |
| BUG-12 | `GET /api/place-bet` returns 200 instead of 405 | Low |
| BUG-14 | Odds filter lower bound is exclusive | Low |
| BUG-15 | "Showing N matches" counter ignores filters | Low |
| BUG-16 | Bet slip hides the available balance once a selection is added | Low |
| BUG-17 | Inconsistent match ID format in `GET /api/matches` | Low |

The detailed reports below are ordered by severity.

---

### BUG-01: API accepts a negative stake and credits the user's balance

**Severity:** Critical
**Component:** API `POST /api/place-bet`

**Reproduction steps**
1. `POST /api/reset-balance` → `GET /api/balance` returns 120.
2. Send:
   ```http
   POST /api/place-bet
   x-user-id: <id>
   Content-Type: application/json

   {"matchId":"premier-league-chelsea-liverpool-2026-12-01","selection":"HOME","stake":-5}
   ```
3. `GET /api/balance`.

**Expected:** `422 {"error":"invalid_stake_min","message":"Stake must be at least 1.00."}`. The balance stays 120.
**Actual:** `200 {"message":"Bet placed successfully", "stake":-5, "odds":2.75, "payout":-13.75, "balance":125, "currency":"USD"}`. The balance goes **up** from 120 to 125.

**Business impact:** Anyone who calls the API directly can mint money on demand, with unlimited repetitions.
This is direct financial loss and a fraud vector. The UI input mask hides the issue, so it won't show up in
UI-only testing.

**Evidence:** API response above (reproduced several times). Values 0 and 0.99 are correctly rejected, so the minimum check doesn't cover negative numbers. Combined with BUG-07, it also works on a match that has already been played: `{"matchId":"premier-league-manutd-chelsea","selection":"AWAY","stake":-50}` → `200`, balance **120 → 170**.

---

### BUG-02: API has no insufficient-balance check; the balance can go negative

**Severity:** Critical
**Component:** API `POST /api/place-bet` (reachable from the UI through BUG-04)

**Reproduction steps (API)**
1. Bring the balance to 74.66 (any value below 100).
2. `POST /api/place-bet` with `{"matchId":"premier-league-chelsea-liverpool-2026-12-01","selection":"HOME","stake":80}`.
3. With the balance now negative, place another bet with `stake: 1`.

**Reproduction steps (UI only, normal user)**
1. Balance €30.00 (reload the page so the UI is fresh).
2. Select Napoli vs Lazio "1", stake 30 → Place Bet → close the receipt (the header still shows €30.00).
3. Select Napoli vs Lazio "X", stake 30 → Place Bet.

**Expected:** The bet is rejected with `422 insufficient_balance` (spec 4.1: "Must not exceed available balance, UI + API"). The balance never drops below 0.
**Actual:** Both requests return `200`. The balance becomes **−5.34**, then **−1.00** (API path), and **−€30.00** (UI path). After a reload the header shows "Balance: €-30.00".

**Business impact:** Customers can bet money they don't have. The operator carries unfunded liability and
effectively extends credit, which is a licensing and regulatory breach. Through the UI it takes only two
ordinary bets to trigger.

**Evidence:** [03_second_bet_on_stale_balance.jpg](evidence/03_second_bet_on_stale_balance.jpg) (second €30 bet accepted while the header shows €30.00), [05_negative_balance.jpg](evidence/05_negative_balance.jpg) (header and slip show €-30.00), [09_api_bet_on_past_match_with_negative_balance.jpg](evidence/09_api_bet_on_past_match_with_negative_balance.jpg) (API accepts a €100 bet on a balance that is already negative → `balance: -590`), [10_ui_negative_balance.jpg](evidence/10_ui_negative_balance.jpg) (UI shows €-180.00, matching `GET /api/balance`, with no warning or block).

---

### BUG-07: Bets are accepted on past matches, which are listed first (UI and API)

**Severity:** Critical
**Component:** UI match list and API `POST /api/place-bet`

**Reproduction steps**
1. Open the app. The list ("Upcoming Football Matches", "Showing 103 matches") starts with matches labelled **PAST** (for example Manchester Utd vs Chelsea, Fri 27 Feb).
2. Click its **1** (2.45), stake 2 → Place Bet.
3. API: `POST /api/place-bet` with `{"matchId":"premier-league-manutd-chelsea","selection":"HOME","stake":1}`.

**Expected:** Only upcoming, pre-match events can be bet on (spec §1). Past matches aren't listed, or their odds are disabled. The API rejects them with `422`.
**Actual:** 91 of the 103 matches returned by `GET /api/matches` have a `kickoffDate` before today. Their odds buttons are active, the UI bet succeeds (receipt #B-58785, €2 deducted), and the API returns `200`.

**Business impact:** Customers can bet on matches whose result is already known, which guarantees losses for the
operator and breaches the pre-match-only rule. The past matches aren't hidden: they're the default view, listed
*before* all upcoming ones (the first upcoming match is card 92 of 103), so any user can find them. Combined
with BUG-01, a bet on a finished match with a negative stake increases the balance (−50 → +€50).

**Evidence:** [01_match_list_past_matches.jpg](evidence/01_match_list_past_matches.jpg), [09_api_bet_on_past_match_with_negative_balance.jpg](evidence/09_api_bet_on_past_match_with_negative_balance.jpg) (`premier-league-manutd-chelsea`, 27 Feb, accepted with `200`). API response `200 {"matchId":"premier-league-manutd-chelsea", ...}`.

---

### BUG-18: No kickoff time; matches dated today stay bettable after kickoff

**Severity:** Critical
**Component:** API `GET /api/matches` (data contract) and UI match status

**Reproduction steps**
1. `GET /api/matches`. Each match has only `kickoffDate` (`YYYY-MM-DD`) and no kickoff time.
2. Check how the UI classifies a match dated today. The status logic in the app bundle (`index-*.js`) compares
   calendar days only: `date < today → "PAST"`, `same day → "TODAY"`, otherwise `"UPCOMING"`. The kickoff label is "Today".
3. On a day when a match is dated today, select its odds after kickoff (or after the final whistle) and place a bet.

**Expected:** The match shows a kickoff date **and time** (spec §2.1: "kickoff date/time label"). Betting closes
at kickoff (spec §1: pre-match only), in the UI and in the API.
**Actual:** No time exists anywhere in the contract, so neither the UI nor the API can tell "today, not started"
from "today, in progress" or "today, finished". A match dated today is shown with a "TODAY" / "Today" label and
stays bettable for the whole day. Even with BUG-07 fixed, in-play and finished matches remain bettable until midnight.

**Business impact:** Betting on matches in progress or already finished lets users bet with knowledge of the
score, which is guaranteed losses and a breach of the pre-match-only rule. It also can't be fixed in the UI
alone, because it needs a contract change (a kickoff timestamp).

**Evidence:** Reproduced live on 2026-11-13: [11_today_match_listed_and_bettable.jpg](evidence/11_today_match_listed_and_bettable.jpg)
shows Bayern Munich vs Leverkusen (`kickoffDate: "2026-11-13"`, no time) labelled **TODAY / Today** with active odds.
[06_today_match_receipt_vs_api_payout.jpg](evidence/06_today_match_receipt_vs_api_payout.jpg) shows a bet on it
accepted at **23:23** that evening, long after any normal kickoff. The OpenAPI `Match` schema has no time field,
and the app classifies status by calendar day only.

---

### BUG-03: Receipt shows potential payout as stake × 2 instead of stake × odds

**Severity:** High
**Component:** UI, success receipt modal (`#modal-success-payout`)

**Reproduction steps**
1. Select Chelsea vs Liverpool → **1** (odds 2.75).
2. Enter stake 10. The slip shows Potential Payout **€27.50**.
3. Click Place Bet.

**Expected:** The receipt shows Potential Payout **€27.50** (10 × 2.75), as on the slip and in the API response (`"payout":27.5`).
**Actual:** The receipt shows **€20.00**. The same happens for every bet: 7 @ 3.70 → €14.00 (should be €25.90), 30 @ 1.95 → €60.00 (should be €58.50), 3 @ 3.35 → €6.00 (should be €10.05).

**Business impact:** The receipt is the customer's confirmation of what the operator owes. Showing a different
payout from the slip leads to disputes, complaints and possible regulatory issues. Customers either think
they were short-changed or expect a payout the operator won't make.

**Evidence:** [02_receipt_wrong_payout_teams_balance.jpg](evidence/02_receipt_wrong_payout_teams_balance.jpg), [06_today_match_receipt_vs_api_payout.jpg](evidence/06_today_match_receipt_vs_api_payout.jpg) (1.01 @ 1.75: receipt €2.02, API `payout: 1.76`), [08_receipt_reversed_teams_stale_balance.jpg](evidence/08_receipt_reversed_teams_stale_balance.jpg) (1.00 @ 3.90: receipt €2.00). Slip before placement: [00_bet_slip_before_placement.jpg](evidence/00_bet_slip_before_placement.jpg). The backend calculates correctly, so the defect is in the UI.

---

### BUG-04: Header and bet slip balance aren't updated after a bet is placed

**Severity:** High
**Component:** UI, header balance (`#header-balance`) and bet slip balance

**Reproduction steps**
1. Reset the balance and reload. The header shows €120.00.
2. Place a €10 bet. Close the receipt.
3. Compare the header and slip with `GET /api/balance`.

**Expected:** The header and slip show **€110.00** right after placement (spec: "stake is deducted", balance shared across header and slip).
**Actual:** Both still show **€120.00**. The API returns 110 and the app even calls `GET /api/balance` after placement, but doesn't render the result. Only a page reload shows the correct value.

**Business impact:** The customer sees money they no longer have. The client-side "Insufficient balance" check
runs on this stale value, which makes BUG-02 reachable by ordinary users.

**Evidence:** [02_receipt_wrong_payout_teams_balance.jpg](evidence/02_receipt_wrong_payout_teams_balance.jpg) (header €120.00 behind the receipt). Network log: `POST /api/place-bet` → `"balance":110`, then `GET /api/balance` → `{"balance":110}`.

---

### BUG-05: Receipt shows the teams in reversed order (away vs home)

**Severity:** High
**Component:** UI, success receipt (`#modal-success-match`)

**Reproduction steps**
1. Select **Chelsea vs Liverpool** (Chelsea listed first, i.e. home) → **1**.
2. Stake 10 → Place Bet.

**Expected:** Match "**Chelsea vs Liverpool**". Per the domain rules, home is first everywhere, including the receipt.
**Actual:** "**Liverpool vs Chelsea**". This reproduced on all 8 receipts observed during the session: "Newcastle vs Manchester Utd", "Lazio vs Napoli", "Chelsea vs Manchester Utd", and so on.

**Business impact:** By convention, a reversed fixture reads as a bet on the *other* team. Together with BUG-06
(no selection on the receipt), the customer can't verify what they backed, which leads to disputes and
complaints.

**Evidence:** [02_receipt_wrong_payout_teams_balance.jpg](evidence/02_receipt_wrong_payout_teams_balance.jpg), [08_receipt_reversed_teams_stale_balance.jpg](evidence/08_receipt_reversed_teams_stale_balance.jpg) (list: Bayern Munich vs Leverkusen; receipt: "Leverkusen vs Bayern Munich").

---


### BUG-08: "Placing..." button stays clickable; repeated clicks place duplicate bets

**Severity:** High
**Component:** UI, Place Bet button (`#bet-slip-place-bet`)

**Reproduction steps**
1. Select Napoli vs Lazio **X** (3.35), stake 3. Balance €113.00.
2. Click **Place Bet**, then click it again while it shows "Placing...": once immediately and once about 0.5 s later.
3. `GET /api/balance`.

**Expected:** While "Placing..." is shown the button is disabled. Exactly one bet is placed. The balance becomes €110.00.
**Actual:** The in-progress button has no `disabled` attribute. Each click sends a new `POST /api/place-bet`. Responses: `200`, `409 bet_in_progress`, `200`. Two bets are placed and **€6.00** is deducted for one €3 slip (113 → 107). The server-side `409` lock only protects requests that overlap; a click after the first response completes is accepted as a new bet.

**Business impact:** Impatient customers get charged twice for one intended bet, which means refunds, complaints and chargebacks.

**Evidence:** Network log: 3 × `POST /api/place-bet` → 200 / 409 / 200. Balance 113 → 107. A fast double-click (two requests 32 ms apart) was caught by the `409`, so the duplicate depends on timing.

---

### BUG-06: Receipt doesn't show the selection

**Severity:** Medium
**Component:** UI, success receipt

**Steps:** Place any bet. **Expected:** The receipt includes the Selection (for example "Match Winner: Home"), as required by spec §2.4. **Actual:** It shows only Bet ID, Match, Stake, Odds, Payout and time.
**Business impact:** The customer can't confirm which outcome they backed, and BUG-05 makes this worse.
**Evidence:** [02_receipt_wrong_payout_teams_balance.jpg](evidence/02_receipt_wrong_payout_teams_balance.jpg), [07_receipt_missing_selection_payload_home.jpg](evidence/07_receipt_missing_selection_payload_home.jpg) (request payload has `selection: "HOME"`, the receipt shows no selection).

### BUG-09: `place-bet` response returns currency `USD`

**Severity:** Medium
**Component:** API `POST /api/place-bet`

**Steps:** Place any valid bet. **Expected:** `"currency":"EUR"` (spec §3, §5.3). **Actual:** `"currency":"USD"` on every success response. `GET /api/balance` returns `"EUR"`.
**Business impact:** Any client that displays or reconciles using this field shows the wrong currency. This is a data-integrity risk for downstream systems such as accounting and reporting.
**Evidence:** Every `200` response body quoted in this document; [06_today_match_receipt_vs_api_payout.jpg](evidence/06_today_match_receipt_vs_api_payout.jpg), [09_api_bet_on_past_match_with_negative_balance.jpg](evidence/09_api_bet_on_past_match_with_negative_balance.jpg).

### BUG-10: `reset-balance` response doesn't match the persisted balance

**Severity:** Medium
**Component:** API `POST /api/reset-balance`

**Steps:** `POST /api/reset-balance` → `GET /api/balance`. **Expected:** Both return **125.5** (spec: "response body and persisted state must be consistent"; initial balance €125.50). **Actual:** The response says `125.5`, but the persisted balance is **120**. The UI shows €120.00 after reload.
**Business impact:** Users are reset to the wrong amount, and any client that trusts the response shows a wrong balance. It also makes test data unreliable.
**Evidence:** `{"message":"Balance reset successfully","balance":125.5,"currency":"EUR"}` followed by `{"balance":120,"currency":"EUR"}`.

### BUG-11: Malformed JSON body returns 500 instead of 400

**Severity:** Medium
**Component:** API `POST /api/place-bet`

**Steps:** Send the body `{bad json` with `Content-Type: application/json`. **Expected:** `400 {"error":"invalid_json","message":"Malformed JSON body."}` (OpenAPI example). **Actual:** `500 {"error":"internal_server_error","message":"Unable to process request."}`.
**Business impact:** Client errors are reported as server outages, which creates false alerts and hides real 5xx errors. It also suggests unhandled exceptions in request parsing.
**Evidence:** Response body above. For comparison, an array body (`[1,2]`) is handled correctly: `400 invalid_request`.

### BUG-13: Odds filter accepts min > max without feedback

**Severity:** Medium
**Component:** UI, odds filter

**Steps:** Odds → Min 5.00, Max 2.00 → Apply. **Expected:** A validation message, and the range isn't applied (spec §2.6). **Actual:** The filter is applied. The label shows "Odds: 5.00 - 2.00", the list is empty, and "Showing 103 matches" is still displayed.
**Business impact:** Users see an empty market and may leave, which costs turnover.
**Evidence:** [04_odds_filter_invalid_range.jpg](evidence/04_odds_filter_invalid_range.jpg).

### BUG-19: Receipt Bet ID is a random client-side number; the API returns no bet identifier

**Severity:** Medium
**Component:** UI success receipt and API `POST /api/place-bet`

**Steps:** Place a bet and compare the receipt with the `place-bet` response. **Expected:** The receipt shows the
bet ID assigned by the backend when the bet was stored (spec §2.4). **Actual:** The `200` response has no ID
field. The receipt's "#B-61541"-style ID is built in the browser as `#B-` + a random number from 10000–99999
(app bundle), so it's not linked to any stored bet and can repeat. The placement timestamp is also client-side
and always starts with "Today".
**Business impact:** Customers and support can't look up or dispute a bet by its ID. Two customers can hold the
same "Bet ID". Audit trails for real-money bets need a server-side identifier.
**Evidence:** `place-bet` response fields: `message, matchId, selection, stake, odds, payout, balance, currency` (no ID).
App bundle: ``kl=`#B-${Math.floor(1e4+Math.random()*9e4)}` `` and ``_l=`Today, ${...}` ``. See also [06_today_match_receipt_vs_api_payout.jpg](evidence/06_today_match_receipt_vs_api_payout.jpg).

### BUG-20: API truncates the payout instead of rounding; it differs from the bet slip

**Severity:** Medium
**Component:** API `POST /api/place-bet` (payout calculation)

**Steps:** Place bets whose exact payout has a third decimal (for example stake 1.01 at odds 3.70 = 3.737), and compare
the API `payout` with the slip's Potential Payout for the same stake and odds.
**Expected:** One payout rule everywhere. Standard rounding to cents gives 3.74, which is what the slip shows.
**Actual:** The API always rounds **down**:

| Stake × odds | Exact | API `payout` | Rounded (half-up) |
|---|---|---|---|
| 1.01 × 1.75 | 1.7675 | **1.76** | 1.77 |
| 1.01 × 3.70 | 3.737 | **3.73** (slip shows €3.74) | 3.74 |
| 1.01 × 1.85 | 1.8685 | **1.86** | 1.87 |
| 1.07 × 4.10 | 4.387 | **4.38** | 4.39 |
| 2.35 × 3.70 | 8.695 | **8.69** | 8.70 |

**Business impact:** The customer is shown one potential payout before placing the bet and the backend records a
lower one, so the "values consistent before and after placement" rule fails at the source of truth. It's only up to
€0.01 per bet, but systematic under-settlement is a disputes and regulatory risk, and it adds up across volume.
**Evidence:** [06_today_match_receipt_vs_api_payout.jpg](evidence/06_today_match_receipt_vs_api_payout.jpg) (API `payout: 1.76`
for 1.01 × 1.75), plus the API runs in the table above. The rounding mode isn't specified (see section 4), but the slip
and the API must agree.

### BUG-12: `GET /api/place-bet` returns 200 instead of 405

**Severity:** Low. **Steps:** `GET /api/place-bet` with a valid `x-user-id` header. **Expected:** `405 method_not_allowed` (spec §4.3; other endpoints do this correctly). **Actual:** `200 {}`.
**Business impact:** An inconsistent API contract. Monitoring and caches may treat the endpoint as healthy and readable.
**Evidence:** `GET /api/place-bet` → `200 {}`, while `GET /api/reset-balance` → `405 {"error":"method_not_allowed"}` and `PUT /api/matches` → `405`.

### BUG-14: Odds filter hides every match that has any odds equal to the minimum

**Severity:** Low. **Steps:** Odds 7.20–7.50 → Apply. Then 1.35–1.45. **Expected:** Inclusive range (spec §2.6):
Bayern vs Stuttgart (away 7.20) and PSG vs Marseille (away 7.50) are both shown. For 1.35–1.45, PSG vs Marseille
(home 1.35) is shown. **Actual:** Only PSG vs Marseille is shown for 7.20–7.50, and it's missing for 1.35–1.45.
With 1.35–1.35 nothing is shown. The upper bound is inclusive. At the lower bound, the filter doesn't just exclude
the value: it hides the **whole match** when **any** of its three odds equals the minimum, even if another of its
odds is inside the range.
**Business impact:** Matches disappear from a filter they match, which hides markets from users filtering by odds.
**Evidence:** The filter condition in the app bundle:
`!odds.some(o => Math.abs(o - min) < Number.EPSILON) && odds.some(o => o > min && o <= max)`. Range 1.30–1.40
includes PSG vs Marseille, so the match itself isn't the problem.

### BUG-15: "Showing N matches" counter ignores filters

**Severity:** Low. **Steps:** Apply any date or odds filter. **Expected:** The counter shows the number of visible matches. **Actual:** It always shows "Showing 103 matches".
**Business impact:** Users get wrong feedback about their filter; with an invalid range (BUG-13) the list is empty while the counter says 103.
**Evidence:** [04_odds_filter_invalid_range.jpg](evidence/04_odds_filter_invalid_range.jpg) (0 cards, "Showing 103 matches"), [11_today_match_listed_and_bettable.jpg](evidence/11_today_match_listed_and_bettable.jpg) (date range applied, 4 cards, "Showing 103 matches").

### BUG-16: Bet slip hides the available balance once a selection is added

**Severity:** Low. **Steps:** Select any odds. **Expected:** The slip keeps showing the available balance next to stake and payout (spec §2.2). **Actual:** The balance is replaced by "Remove All" and is visible only while the slip is empty.
**Business impact:** Users can't see their available funds next to the stake they're entering, which leads to more "Insufficient balance" errors and a worse betting flow.
**Evidence:** [00_bet_slip_before_placement.jpg](evidence/00_bet_slip_before_placement.jpg).

### BUG-17: Inconsistent match ID format in `GET /api/matches`

**Severity:** Low. **Steps:** `GET /api/matches` and compare the `id` values. **Expected:** One consistent,
unique ID scheme. **Actual:** 33 of 103 IDs have no date (`premier-league-manutd-chelsea`) and 70 do
(`premier-league-west-ham-everton-2026-04-03`). Team slugs are abbreviated inconsistently (`manutd`,
`real-barca`, `juve-milan`, `atleti` vs full names elsewhere). The same fixture appears again later with a dated ID
(`serie-a-napoli-lazio` on 2026-03-05 and `serie-a-napoli-lazio-2026-12-12`), so date-less IDs are ambiguous for
a recurring fixture.
**Business impact:** There's a risk of ID collisions when a fixture recurs (a bet attached to the wrong match). It
also makes logs, support lookups and test data harder to work with.
**Evidence:** `GET /api/matches` analysis: 33 IDs without a date suffix, 70 with one; for example `premier-league-manutd-chelsea` vs `premier-league-west-ham-everton-2026-04-03`.

---

## 4. Spec ambiguities found during execution

These aren't reported as bugs. They are questions for the product owner:

1. **Minimum stake:** Business Rules and UI copy say **€1.00**, but Validation Rules §4.1 says "Minimum **€1.01**".
   The app accepts €1.00. I treated €1.00 as correct.
2. **Payout rounding mode** isn't specified. The slip rounds half-up, while the API truncates (BUG-20). The spec
   should name the rule, and both sides must use it.
3. **Date labels:** The missing kickoff time is reported as BUG-18. Separately, the label format is mixed:
   matches within a week show a weekday ("Tuesday"), while others show a date ("Sat 21 Nov"). The intended
   format should be confirmed.
4. **Insufficient-balance HTTP code:** The OpenAPI spec lists `insufficient_balance` only as an example error
   string, with no status code. I assumed `422`.
5. **Initial balance:** The first visit showed **€20.00** before any action. It's unclear whether the balance
   persists per user across sessions or should start at €125.50.
6. **Repeated identical bets:** Placing the same bet again (same match, selection and stake) is accepted
   (`200`, `200`). The spec only says *one active selection in the bet slip at a time*; it doesn't limit bets per
   event. Accidental duplicates from repeated clicks are a defect (BUG-08). Whether deliberate repeats should be
   blocked or limited needs a product decision.
7. **Swagger note:** The `reset-balance` 200 description says "response payload may differ from persisted
   balance". This contradicts spec §5.3, which requires them to be consistent. BUG-10 is reported against the
   functional spec.

## 5. Improvement suggestions

These aren't defects against the current spec. They are product and design improvements found during testing:

| ID | Suggestion | Why | Related |
|----|------------|-----|---------|
| IMP-01 | **Date filter: disable days before today.** Make today the earliest selectable start date, and default the list to upcoming matches only. | The feature is pre-match only, so selecting past dates has no valid use case. Today the calendar offers any past day and the list opens on 91 past matches. | BUG-07 |
| IMP-02 | **Opaque, server-generated match IDs** (for example MongoDB ObjectId, UUID or ULID) instead of IDs built from league and team names. Keep a readable slug as a separate field if needed. | The same teams play each other again, so name-based IDs repeat (`serie-a-napoli-lazio` already has a later `...-2026-12-12` twin). Unique IDs make collisions impossible and keep IDs stable if a team name or date changes. | BUG-17 |
| IMP-03 | **Bet history and lookup by bet ID:** a "My bets" view in the UI, plus `GET /api/bets` and `GET /api/bets/{betId}`. | Once a receipt is closed, the user can't see placed bets at all, and support can't look one up. It needs a server-side bet ID first (BUG-19). It would also give tests a direct way to verify that a bet was stored exactly once (BUG-08). | BUG-19, BUG-08 |
| IMP-04 | **Competitions as a separate entity with IDs.** Store competitions in their own table (`id`, `name`, `country`, ...). Matches reference them by `competitionId`, and requests and filters use the ID instead of the display string. | Today `competition` is a free-text string repeated on every match (10 distinct values across 103 matches). A string isn't a stable key: renaming or a typo silently splits data, and names aren't unique across countries (`Championship` is English here, but other countries have a "Championship" too). IDs keep the data normalized, allow reliable competition filtering and metadata (country, logo, localized names), and let the UI change display names without breaking API consumers or tests. | IMP-02, BUG-17 |
