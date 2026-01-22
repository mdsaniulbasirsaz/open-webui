# Planning: bKash Payment Gateway (Sandbox) Backend Integration

## Objective
Provide a backend-only integration with the bKash sandbox to support payment creation, execution, and status tracking for the admin payment dashboard and future billing flows.

## Scope
- Backend APIs and data storage only (no frontend UI in this plan).
- Sandbox environment only.
- Core checkout flow: token grant -> create payment -> execute payment -> query status.

## Non-Goals
- Production credentials and live transactions.
- Subscription billing automation or invoices generation logic.
- Full reconciliation against external accounting systems.

## Phase 1: Configuration + Client Foundation
### Scope
Add bKash sandbox config and a reusable API client with token management.

### Work Items
- Add env/config entries (example keys):
  - `BKASH_BASE_URL` (sandbox base)
  - `BKASH_APP_KEY`, `BKASH_APP_SECRET`
  - `BKASH_USERNAME`, `BKASH_PASSWORD`
  - `BKASH_CALLBACK_URL`
  - `BKASH_WEBHOOK_SECRET` (if applicable)
  - `BKASH_TIMEOUT_SECONDS`
- Wire config into `app.state.config` and admin config endpoints if needed.
- Implement `bkash_client.py`:
  - Grant token and cache by expiry.
  - Standard headers (authorization, app key).
  - Timeouts, retry policy (safe GET/POST only), and structured logging.

### Deliverables
- Config entries available at runtime.
- bKash client module with token caching.

## Phase 2: Payment Flow Endpoints
### Scope
Create backend endpoints for the core sandbox checkout flow.

### Work Items
- Create router `backend/open_webui/routers/payments.py`.
- Add models `backend/open_webui/models/payments.py`:
  - `PaymentTransaction` (user_id, plan_id, amount, currency, status, payment_id, trx_id, raw_response, created_at, updated_at).
- Create endpoints (names can vary, but keep consistent under `/api/v1/payments/bkash`):
  - `POST /create` -> call bKash create payment, store pending txn, return `bkashURL`.
  - `POST /execute` -> execute payment with `paymentID`, update txn status.
  - `GET /query` -> query payment status by `paymentID` and sync local state.
- Enforce idempotency with `merchantInvoiceNumber` (generate and store).
- Validate user identity and plan mapping (admin or user permissions as needed).

### Deliverables
- bKash create/execute/query endpoints.
- Payment transaction table and persistence.

## Phase 3: Callback/Webhook + Reconciliation
### Scope
Handle redirect callbacks and finalize payment verification.

### Work Items
- Add callback route `POST /callback` (or `GET /callback` if bKash uses query params).
- Verify payment by calling query/execute before marking success.
- Store webhook payloads in `PaymentEvent` (optional) for debugging.
- Add status transitions: `pending` -> `executed` -> `confirmed` or `failed`.

### Deliverables
- Callback handling and verification.
- Payment status normalization and history.

## Phase 4: Security, Observability, Tests
### Scope
Harden the integration and validate with sandbox flows.

### Work Items
- Sanitize and log only non-sensitive fields.
- Add request/response tracing IDs for payment calls.
- Unit tests for token caching and idempotency.
- Integration tests using sandbox credentials (opt-in).
- Document sandbox setup in `backend/README.md`.

### Deliverables
- Tests covering token, create/execute, and query flows.
- Documentation for sandbox setup and troubleshooting.

## Acceptance Criteria
- Sandbox config loads correctly and token grant succeeds.
- Create payment returns a redirect URL and stores a pending transaction.
- Execute and query update local status reliably.
- Callback verifies payment before marking success.

## Open Questions
- Which plan IDs map to Free/Plus/Pro in the backend?
- Do we need to expose payment APIs to non-admin users?
- Should callbacks be signed or IP allow-listed for the sandbox?
