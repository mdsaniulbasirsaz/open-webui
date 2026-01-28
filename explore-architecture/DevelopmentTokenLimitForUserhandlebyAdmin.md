# Development Plan - Token Limit for User (Admin-managed) (MVP)

This document is the detailed engineering plan to implement the MVP described in:
- `open-webui/explore-architecture/TokenLimitForUserhandlebyAdmin.md`

## MVP Summary (What we are building)
- Admin sets a **monthly** token limit per user (global across all models).
- Enforce token budget for **WebUI chat completions** (the main request path).
- Persist usage events + maintain a monthly aggregate for concurrency-safe enforcement.
- If exceeded: block with HTTP `429` and stable JSON payload.

## Non-goals (Explicitly out of MVP)
- Per-model/per-provider limits
- Group/workspace pooled budgets
- Auto downgrade/fallback models
- Billing integration
- Enforcing `/openai/*` and `/ollama/*` proxy endpoints

---

## 0) Discovery / Current Code Touchpoints
Confirm these before coding:
- Entry path for chat completions:
  - `open_webui/utils/middleware.py` (stream handlers + emits `usage`)
  - `open_webui/utils/chat.py` (shared helper used by chat flows)
- Auth + admin gating:
  - `open_webui/utils/auth.py` (`get_admin_user`, `get_verified_user`)
- Existing token usage format:
  - `open_webui/utils/response.py` (Ollama -> OpenAI usage conversion)

---

## Phase 1 - Data Model + Migrations
**Outcome:** DB support for per-user budgets + monthly aggregation + usage ledger.

**Deliverables**
- New tables: `token_budget`, `token_usage_event`, `token_window_aggregate`
- SQLAlchemy models (following existing patterns in `open_webui/models/`)
- Alembic migration(s) (following existing patterns in `open_webui/migrations/versions/`)

### 1.1 New DB tables
Create 3 tables (MVP):

1) `token_budget` (1 row per user)
- `id` (uuid/text)
- `user_id` (text, unique, indexed)
- `window_type` (text, default `monthly`)
- `timezone` (text, nullable; fallback UTC)
- `limit_tokens` (int, >= 0)
- `enabled` (bool, default true)
- `created_by` (text user id)
- `created_at` (epoch int)
- `updated_at` (epoch int)

2) `token_usage_event` (append-only; idempotent by `request_id`)
- `id` (uuid/text)
- `request_id` (text, unique, indexed)
- `user_id` (text, indexed)
- `model_id` (text, nullable)
- `provider` (text, nullable)
- `route` (text, nullable)
- `prompt_tokens` (int, default 0)
- `completion_tokens` (int, default 0)
- `total_tokens` (int, default 0)
- `status` (text: `success|error|canceled`)
- `created_at` (epoch int, indexed)
- `metadata` (json, nullable)

3) `token_window_aggregate` (fast totals + concurrency-safe reservations)
- `id` (uuid/text) OR composite unique key (either is fine)
- `user_id` (text, indexed)
- `window_start` (epoch int; first second of month in chosen timezone)
- `limit_tokens_snapshot` (int)
- `used_tokens` (int, default 0)
- `reserved_tokens` (int, default 0)
- `updated_at` (epoch int)
- UNIQUE(`user_id`, `window_start`)

### 1.2 Where to put models (consistent with repo)
Create new model modules following existing conventions:
- `open-webui/backend/open_webui/models/token_budgets.py`
- `open-webui/backend/open_webui/models/token_usage.py` (events + aggregates)

### 1.3 Migration approach
Use the same migration mechanism the repo already uses (confirm by searching existing migrations).
Deliverables:
- Migration script creating the 3 tables and indexes.
- Optional backfill: none needed for MVP (budgets created via Admin UI).

---

## Phase 2 - Core Service: TokenBudgetService
**Outcome:** A single service that owns window math + atomic reservations + event writes.

**Deliverables**
- New service module implementing: `reserve`, `finalize`, `release`, `get_status`
- Deterministic monthly windowing with timezone support (fallback UTC)
- Idempotent reservation keyed by `request_id`

### 2.1 Module location
Add a new service module:
- Preferred (matches current repo structure): `open-webui/backend/open_webui/utils/token_budget.py`
- Alternative: create `open-webui/backend/open_webui/services/` and place `token_budget.py` there (only if you want a dedicated services layer)

### 2.2 Core responsibilities
TokenBudgetService is the only place that:
- Resolves whether a user has an enabled budget (or unlimited if not configured).
- Computes month window boundaries and reset time.
- Reserves tokens atomically to prevent overspend under concurrency.
- Finalizes reservations into actual usage and writes `token_usage_event`.
- Releases reservation on early failure/cancel.

### 2.3 Window calculation (monthly)
Inputs:
- `now` (UTC epoch)
- `timezone` (budget.timezone or user.timezone or UTC)
Outputs:
- `window_start` epoch (start of current month in timezone)
- `reset_at` epoch (start of next month in timezone)

Implementation note:
- Use timezone-aware datetime (pytz is already used in repo).

### 2.4 Reservation algorithm (strict)
Pre-flight:
1. Load user budget row; if none or disabled -> allow (no enforcement).
2. Compute `window_start`.
3. Create-or-get `token_window_aggregate` row.
4. Atomic reserve update:
   - only succeed if `used_tokens + reserved_tokens + estimate_tokens <= limit_tokens_snapshot`
5. Persist a "reservation marker" tied to `request_id`:
   - MVP option A: store in `token_usage_event` with status `reserved` (then update later)
   - MVP option B (cleaner): create a small `token_reservation` table keyed by `request_id`

Recommendation for MVP simplicity:
- Use option A: insert a `token_usage_event` immediately with `total_tokens=estimate_tokens` and `status="reserved"`, then update to final values on completion.
  - This keeps idempotency and avoids another table.

Finalize:
1. Compute `actual_total_tokens` from provider response usage.
2. Update `token_usage_event` row: prompt/completion/total/status.
3. Adjust aggregate:
   - `reserved_tokens -= estimate_tokens`
   - `used_tokens += actual_total_tokens`

Release (failure before completion):
- `reserved_tokens -= estimate_tokens`
- Update `token_usage_event.status` to `error|canceled` with whatever tokens are known (0 if unknown).

### 2.5 Estimating tokens (MVP-safe)
Estimate must be conservative but not too strict:
- Completion estimate:
  - Prefer request param `max_tokens` (or mapped variants) if present
  - Else use a default small number (e.g., 256) to avoid locking users out due to unknown estimate
- Prompt estimate:
  - MVP: 0 (safe but may allow slightly more until finalize)
  - If you want stricter: approximate by message length / 4, capped

Given "strict no overspend" is desired:
- Use `max_tokens` as estimate; if missing, use a conservative default (configurable).

---

## Phase 3 - Enforcement Hook (WebUI Chat Path)
**Outcome:** Budget enforcement applied to the primary WebUI chat completion flow (stream + non-stream).

**Deliverables**
- `request_id` creation + propagation for each chat completion request
- Pre-provider reservation + 429 error contract on failure
- Finalize on success, release/finalize-canceled on failure/cancel

### 3.1 Where enforcement happens
Hook in the WebUI chat completion flow before any provider call:
- `open-webui/backend/open_webui/utils/chat.py`

Implementation idea:
- At the start of the function that dispatches to providers (or just before calling provider router helper):
  1) create `request_id` (uuid)
  2) call `TokenBudgetService.reserve(...)`
  3) if reserve fails -> raise HTTPException(429, payload)
  4) proceed with provider call
  5) on completion (stream done or non-stream response) call `finalize`
  6) on exception -> call `release`

### 3.2 Streaming specifics
Streaming is trickier because "final usage" arrives only at the end.
Implementation options:
- Wrap the streaming generator so that when `[DONE]` / done chunk arrives:
  - extract `usage` from the final message
  - call `finalize`
- If stream fails mid-way:
  - call `release` (or finalize with estimate only and `status=canceled`)

Keep consistent with existing behavior:
- `open_webui/utils/middleware.py` already sees `usage` during streaming; reuse that point to finalize once `done` is true.

---

## Phase 4 - Admin APIs (MVP)
**Outcome:** Admin-only endpoints to set budgets and view budget status.

**Deliverables**
- Admin-only router endpoints (Depends on `get_admin_user`)
- Validation + stable response shapes for UI integration
- A “status” endpoint returning limit/used/reserved/remaining + reset time

### 4.1 Route placement
Add a new admin router or extend an existing admin/config router:
- Option A: `open-webui/backend/open_webui/routers/admin_token_budgets.py`
- Option B: add to `open-webui/backend/open_webui/routers/users.py` under admin-only endpoints

MVP endpoints (admin-only; Depends(get_admin_user)):
1) Set budget
- `PUT /api/v1/admin/token-budgets/users/{user_id}`
- Body: `{ limit_tokens: int, enabled: bool, timezone?: string }`
- Returns: budget object

2) Get budget status
- `GET /api/v1/admin/token-budgets/users/{user_id}/status`
- Returns:
  - `limit_tokens`, `enabled`, `window_type`
  - `used_tokens`, `reserved_tokens`, `remaining_tokens`
  - `window_start`, `reset_at`

3) List budgets (optional MVP)
- `GET /api/v1/admin/token-budgets?query=&page=&limit=`

### 4.2 Validation rules
- `limit_tokens >= 0`
- If `enabled=false`, enforcement bypasses but usage still records (optional; pick one and document it)

---

## Phase 5 - UI (Admin) (MVP)
**Outcome:** Minimal Admin UI to configure limits and inspect remaining budget.

**Deliverables**
- Admin screen section/component for per-user token budget configuration
- Status display (Used / Remaining / Reset date)
- Friendly “limit exceeded” UX handling for end users

Implement a minimal Admin screen:
- User search/select (reuse existing user list/search patterns)
- Form:
  - Monthly token limit (number input)
  - Enabled toggle
- Display:
  - Used / Remaining
  - Reset date/time

If UI is out of scope for now, still build APIs so UI can follow.

---

## 6) Error Contract + UX
### 6.1 API error payload (stable)
HTTP `429`:
```json
{
  "code": "TOKEN_BUDGET_EXCEEDED",
  "message": "Monthly token limit exceeded.",
  "limit": 100000,
  "used": 100000,
  "remaining": 0,
  "window": "monthly",
  "reset_at": 1738368000
}
```

### 6.2 UI handling
- Show a clear banner/toast:
  - "Token limit reached. Resets on <date>."
- Optionally show "Ask admin to increase limit."

---

## 7) Tests (Recommended for MVP)
Add backend tests similar to existing router tests:
- Create new test module, example:
  - `open-webui/backend/open_webui/test/apps/webui/routers/test_admin_token_budgets.py`

Test cases:
1) Admin can set a budget; non-admin cannot.
2) Reserve succeeds when remaining is enough.
3) Reserve fails with 429 when remaining is 0.
4) Concurrency: two reserves cannot exceed limit (simulate with sequential calls and reservation accounting).
5) Finalize updates aggregate + event correctly.

---

## 8) Rollout Plan (Safe Release)
### 8.1 Feature flag (recommended)
Add a config flag:
- `ENABLE_TOKEN_BUDGETS` (default false)

When off:
- No enforcement (but can still allow Admin to configure budgets).

### 8.2 Migration + deploy steps
1) Deploy migration
2) Enable flag in staging
3) Create budgets for test users
4) Verify:
   - enforced blocks
   - aggregates correct
   - streaming finalize works

---

## 9) Implementation Checklist (DoD)
- DB tables + indexes + migrations added
- TokenBudgetService implemented and used in chat completion flow
- Usage events written with idempotent `request_id`
- Aggregate reservation is atomic and strict
- Admin APIs implemented + permissioned
- UI added (or explicitly deferred)
- Tests pass
- Docs updated (this file + MVP file)

---

## Open Questions (Answer Before Coding)
1) `request_id` exists in `generate_direct_chat_completion` today; do we standardize on a single `request_id` for all chat completion paths (direct + non-direct) and pass it through to finalize?
2) For providers that do not return `usage`, do we finalize with the reservation estimate (recommended for strict enforcement) or attempt to compute?
3) When `enabled=false`, do we still record usage events? (recommended: yes, but skip enforcement)
