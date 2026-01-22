# Development Plan: bKash Payment Gateway (Sandbox)

## Objective
Implement the full backend integration for bKash sandbox payments, including configuration, core payment flow, callback verification, and testing/observability hardening.

## Phase 1: Configuration + Client Foundation
### Scope
Introduce bKash sandbox configuration and a reusable client with token caching.

### Work Items
- Add env/config keys:
  - `BKASH_BASE_URL`
  - `BKASH_APP_KEY`, `BKASH_APP_SECRET`
  - `BKASH_USERNAME`, `BKASH_PASSWORD`
  - `BKASH_CALLBACK_URL`
  - `BKASH_WEBHOOK_SECRET` (if needed)
  - `BKASH_TIMEOUT_SECONDS`
- Expose config in `app.state.config` and admin config endpoints if required.
- Implement `bkash_client.py`:
  - Token grant and cache by expiry.
  - Standard headers (authorization, app key).
  - Timeouts, retry policy for safe calls only.
  - Structured error mapping.

### Deliverables
- Config available at runtime.
- bKash client with token caching and error handling.

## Phase 2: Payment Flow Endpoints
### Scope
Create APIs and storage for create/execute/query payment flows.

### Work Items
- Add `backend/open_webui/models/payments.py` with `PaymentTransaction` schema.
- Add router `backend/open_webui/routers/payments.py`.
- Endpoints (example path under `/api/v1/payments/bkash`):
  - `POST /create` to create payment and return `bkashURL`.
  - `POST /execute` to execute payment and update status.
  - `GET /query` to query payment status and sync locally.
- Persist `merchantInvoiceNumber` to enforce idempotency.
- Validate user identity and plan/amount mapping rules.

### Deliverables
- bKash create/execute/query endpoints.
- Payment transaction storage with status transitions.

## Phase 3: Callback/Webhook + Reconciliation
### Scope
Handle bKash callbacks and verify payments before marking success.

### Work Items
- Add callback route (`POST /callback` or `GET /callback` depending on bKash spec).
- Verify callback payloads and call query/execute before finalizing.
- Optional: create `PaymentEvent` for raw webhook payload logging.
- Normalize statuses: `pending` -> `executed` -> `confirmed` or `failed`.

### Deliverables
- Callback handling and verification logic.
- Status normalization and audit trail.

## Phase 4: Security, Observability, Tests
### Scope
Protect sensitive data, improve traceability, and validate the sandbox flow with unit + integration tests.

### Work Items
- Security:
  - Mask credentials and tokens in logs.
  - Validate callback signatures (or shared secret) and reject unsigned requests.
  - Add idempotency checks on execute/query to prevent double processing.
- Observability:
  - Add request IDs for bKash outbound calls and include in responses.
  - Log minimal fields: payment_id, trx_id, status, latency, error code.
- Tests:
  - Unit tests for token caching, refresh on expiry, and error handling.
  - Unit tests for idempotency (repeated execute/query).
  - Integration tests against sandbox (opt-in via env flag).
- Documentation:
  - Add sandbox setup steps to `backend/README.md`.
  - Document required env vars and callback behavior.

### Deliverables
- Hardened endpoints with masked logs and idempotency.
- Structured logs and trace IDs for payment lifecycle.
- Test suite covering token and payment flows (unit + opt-in sandbox).
- Documentation for sandbox configuration and troubleshooting.

## Phase 5: Frontend Integration (AccountPending Overlay)
### Scope
Wire the sandbox payment flow into the pricing overlay in `src/lib/components/layout/Overlay/AccountPending.svelte`.

### Work Items
- Frontend API helper:
  - Add `src/lib/apis/payments/bkash.ts` for `create`, `execute`, and `query`.
  - Return normalized responses for UI (status, message, redirect URL).
- UI integration:
  - Add a "Get Plus" / "Get Pro" CTA handler that calls `POST /api/v1/payments/bkash/create`.
  - Redirect the browser to `bkashURL` when returned.
  - On redirect back, read `paymentID`/`status` from query params and call `execute` or `query`.
  - Render success/failure states inline in AccountPending.
- State + UX:
  - Disable CTAs while payment is in progress.
  - Surface errors with a toast and a retry action.
  - Keep UI-only Free plan button unchanged.

### Deliverables
- AccountPending overlay launches bKash sandbox checkout.
- Payment status is verified and surfaced to the user.

## Acceptance Criteria
- Sandbox config loads correctly and token grant succeeds.
- Create payment returns a redirect URL and stores a pending transaction.
- Execute and query update local status reliably.
- Callback verifies payment before marking success.
- No secrets or tokens appear in logs.
