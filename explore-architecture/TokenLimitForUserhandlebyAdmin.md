# Token Limit for User (Admin-managed) - MVP Plan (Open WebUI)

## Goal (MVP)
Give Admin a simple, reliable way to set a per-user token budget and enforce it for chat usage, with clear UI errors when a user is out of budget.

This plan is aligned with Open WebUI's current flow:
- Auth/roles via `open_webui/utils/auth.py` (`get_admin_user`, `get_verified_user`)
- Chat requests via `open_webui/utils/middleware.py` -> `open_webui/utils/chat.py`
- Token usage already appears in responses (`usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`)

---

## MVP Scope (What we will build now)
### Included
1. Admin sets a **monthly** token limit per user (global across all models).
2. System enforces the limit for **WebUI chat completions** (the main product path).
3. Usage is recorded in DB so Admin can see: limit, used, remaining, reset date.
4. Deterministic, concurrency-safe enforcement (no accidental overspend on parallel requests).

### Not included (Later)
- Per-model limits
- Per-group/workspace limits
- Auto model fallback when low
- Billing / paid add-ons
- Enforcement for `/openai/*` and `/ollama/*` proxy routes (optional after MVP)

---

## MVP Decisions (Locked for Implementation)
- Window: `monthly`
- Counting: `total_tokens = prompt_tokens + completion_tokens`
- Enforcement behavior: **hard block** when remaining <= 0
- HTTP error: `429` with stable JSON contract
- Scope: per-user global budget (all models combined)

---

## Data Design (Minimal + Correct)
### Tables
1) `token_budget`
- `id`
- `user_id` (unique; 1 row per user for MVP)
- `window_type` = `monthly`
- `timezone` (nullable; fallback to system UTC)
- `limit_tokens` (int)
- `enabled` (bool)
- `created_by`, `created_at`, `updated_at`

2) `token_usage_event` (append-only ledger; idempotent)
- `id`
- `request_id` (unique)
- `user_id`
- `model_id` (string, nullable if unknown)
- `provider` (string: `openai|ollama|pipeline|unknown`)
- `route` (string)
- `prompt_tokens`, `completion_tokens`, `total_tokens`
- `status` (`success|error|canceled`)
- `created_at`
- `metadata` JSON (chat_id, message_id, session_id)

3) `token_window_aggregate` (enforcement + concurrency)
- `(user_id, window_start)` unique
- `limit_tokens_snapshot`
- `used_tokens`
- `reserved_tokens`
- `updated_at`

Why both `event` and `aggregate`?
- `token_usage_event` = audit + reporting source of truth
- `token_window_aggregate` = fast and safe enforcement under concurrency

---

## Enforcement Design (MVP)
### Core service
Create a single service (example name): `TokenBudgetService`:
- `get_budget(user_id) -> budget|None`
- `get_window_start(now, timezone) -> epoch/window key`
- `reserve(user_id, window_start, estimate_tokens, request_id)`
- `finalize(request_id, actual_tokens, status, metadata)`
- `release(request_id)` (if fail before provider returns)

### Where to hook (MVP)
Enforce in the WebUI chat path:
- Before the provider call in `open_webui/utils/chat.py` (shared helper used by chat flows).

### Concurrency rule
Reserve before sending to provider:
- Atomic: only allow `used_tokens + reserved_tokens + estimate_tokens <= limit_tokens_snapshot`
- On completion: convert reservation into actual usage (adjust delta), write usage event.

### Token estimate (MVP-safe)
Use a conservative estimate so we don't exceed budget:
- If request includes `max_tokens` (or equivalent), use that as completion estimate.
- Add a small prompt estimate (or 0 if unknown), then finalize with actual.
If actual tokens cannot be computed for a provider, default to using the reservation as final usage (and record `status=success`).

---

## API + UI (MVP)
### Admin APIs (admin-only)
1. Set/update a user's monthly limit
2. Get a user's budget status:
- `limit_tokens`, `used_tokens`, `remaining_tokens`, `reset_at`, `enabled`

### UI (Admin)
Admin page section:
- Search user
- Set "Monthly token limit"
- Display "Used / Remaining" and "Resets on"

### User-visible error contract
HTTP `429` body:
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

---

## MVP Milestones (Implementation Order)
### Step 1 - DB + models
- Add the three tables/models and migrations
- Add a query to compute `reset_at` for the current month window

### Step 2 - Usage event write path
- Ensure we can persist `token_usage_event` from the chat completion flow (stream and non-stream)
- Ensure idempotency by `request_id`

### Step 3 - Enforce + reserve/finalize
- Add `TokenBudgetService`
- Hook into `open_webui/utils/chat.py` before provider call
- Reserve -> call provider -> finalize (or release on error)

### Step 4 - Admin UI + routes
- Admin-only endpoints + UI controls
- Show user budget status and a simple list view

### Step 5 - QA + edge cases
- Parallel requests
- Streaming completion (final usage on done)
- Provider error/cancel paths (release or finalize)

---

## After MVP (Next Upgrade Path)
1. Enforce on `/openai/*` and `/ollama/*` proxy routes
2. Add per-model overrides
3. Reporting dashboard + audit log
4. Billing integration (entitlements + metering)
