# Development File Overview (Feature Integration Map)

This document is a full mapping of where your added features are integrated across **files / routes / models / APIs** (both backend and frontend).

> Repo root (context for this document): `open-webui/`

---

## 0) High-level Router Registration (Backend Entry)

Backend API routers are registered from `backend/open_webui/main.py`:

- `backend/open_webui/main.py`
  - `app.include_router(auths.router, prefix="/api/v1/auths", tags=["auths"])`
  - `app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])`
  - `app.include_router(token_budgets.router, prefix="/api/v1", tags=["token-budgets"])`
  - `app.include_router(token_usage.router, prefix="/api/v1", tags=["token-usage"])`

The frontend calls the backend using `WEBUI_API_BASE_URL` (Svelte/TS):

- `src/lib/constants.ts` (base URL definition)
- API clients:
  - `src/lib/apis/auths/index.ts`
  - `src/lib/apis/payments/index.ts`
  - `src/lib/apis/token_budgets/index.ts`
  - `src/lib/apis/token_usage/index.ts`

---

## 1) Feature: New User Signup → Email Verification (OTP + Link)

### 1.1 Backend (Routes + Logic)

Main signup + verification flow is implemented here:

- `backend/open_webui/routers/auths.py`
  - `POST /api/v1/auths/signup`
    - When `REQUIRE_EMAIL_VERIFICATION=True`, the user is created with `role="pending"`.
    - Then `_issue_email_verification(...)` sends the OTP + (optional) verification link email.
    - response shape: `{"requires_email_verification": true, "email": "...", "resend_available_in": ...}`
  - `POST /api/v1/auths/signup/verify`
    - body: `{ email, otp }`
    - If the OTP matches:
      - `Users.update_user_role_by_id(... intended_role ...)`
      - `EmailVerifications.delete_by_email(email)`
      - Sets the auth cookie token and returns `SessionUserResponse`.
  - `GET /api/v1/auths/signup/verify/link?token=...&email=...`
    - email link verification (one-time token)
  - `GET /api/v1/auths/verify-email/link?token=...&email=...`
    - same handler (alias route)
  - `POST /api/v1/auths/signup/resend`
    - Enforces resend cooldown and sends a new OTP/link.
  - `POST /api/v1/auths/signin`
    - If the user has `role=="pending"` and a verification record exists, it returns `403`:
      - payload: `{ message, requires_email_verification: true, email }`

### 1.2 Backend (Models + DB)

- `backend/open_webui/models/email_verifications.py`
  - SQLAlchemy table: `email_verification`
  - key fields:
    - `email`, `user_id`, `code_hash` (OTP hash)
    - `verification_token_hash`, `verification_token_expires_at`, `verification_token_used_at` (link verify)
    - `attempts_remaining`, `expires_at`, `last_sent_at`
    - `intended_role`, `disable_signup_after_verify`
  - helper accessors: `EmailVerifications.get_by_email(...)`, `upsert_for_user(...)`, `decrement_attempts(...)`, `get_by_token_hash(...)`

### 1.3 Backend (Helpers + Templates)

- `backend/open_webui/utils/email_verification.py`
  - `generate_otp()`, `hash_otp()`, `verify_otp()`
  - link flow: `generate_verification_token()`, `hash_verification_token()`
- `backend/open_webui/utils/email.py`
  - `build_signup_verification_email(...)` → builds HTML + Text
  - `send_email(...)` (SMTP)
- Email templates:
  - `backend/open_webui/templates/email/verify_signup.html`

### 1.4 Backend (Config / Env)

- `backend/open_webui/env.py`
  - `REQUIRE_EMAIL_VERIFICATION`
  - `EMAIL_VERIFICATION_OTP_TTL`, `EMAIL_VERIFICATION_OTP_LENGTH`
  - `EMAIL_VERIFICATION_MAX_ATTEMPTS`
  - `EMAIL_VERIFICATION_RESEND_COOLDOWN`
  - Link verify flags:
    - `ENABLE_EMAIL_VERIFICATION_LINK`
    - `EMAIL_VERIFICATION_LINK_TTL`
    - `EMAIL_VERIFICATION_LINK_BASE_URL`

### 1.5 Backend (Migrations / Tests)

Alembic migrations (SQLAlchemy):
- `backend/open_webui/migrations/versions/7f2b1a4c9f4d_add_email_verification.py`
- `backend/open_webui/migrations/versions/c9f0c2b1d5a7_add_email_verification_link_token.py`

Test coverage:
- `backend/open_webui/test/apps/webui/routers/test_auths.py` (OTP verify + link verify + resend behaviours)

### 1.6 Frontend (Pages + API clients)

- `src/routes/auth/+page.svelte`
  - New flow in the signup/signin UI:
    - When the backend returns `requires_email_verification`, switch to `mode='verify-email'`.
    - OTP verify: `verifySignupEmail(email, otp)`
    - Link verification: reads `token` + `email` from URL query params and calls `verifySignupEmailLink(token, email)`.
    - resend: `resendSignupEmailVerification(email)`
- `src/lib/apis/auths/index.ts`
  - `verifySignupEmail(email, otp)` → `POST /auths/signup/verify`
  - `verifySignupEmailLink(token, email?)` → `GET /auths/signup/verify/link`
  - `resendSignupEmailVerification(email)` → `POST /auths/signup/resend`

---

## 2) Feature: Forgot Password / Reset Password

### 2.1 Backend (Routes)

- `backend/open_webui/routers/auths.py`
  - `POST /api/v1/auths/password-reset/request`
    - body: `{ email }`
    - Anti-enumeration: returns the same message even if the email does not exist.
    - rate limit: email + ip limiter
    - Calls `_issue_password_reset_email(...)` to send the reset link.
  - `GET /api/v1/auths/password-reset/validate?token=...&email=...`
    - Validates the token and returns `{ valid: true, expires_at }`.
  - `POST /api/v1/auths/password-reset/confirm`
    - body: `{ token, password, email? }`
    - Validates token → updates password → marks link used → sends confirmation email.

### 2.2 Backend (Model + Token Rules)

- `backend/open_webui/models/password_reset.py`
  - table: `password_reset_request`
  - fields:
    - `token_hash`, `expires_at`, `used_at`, `revoked_at`
    - `email`, `user_id`
  - helpers:
    - `PasswordResetRequests.upsert_for_user(...)`
    - `PasswordResetRequests.get_by_token_hash(...)`
    - `PasswordResetRequests.mark_as_used(...)`

Reset token logic:
- `backend/open_webui/routers/auths.py`
  - The reset token is a JWT (`create_token`) with payload:
    - `{ id: user_id, email, purpose: "password_reset" }`
  - The DB stores `hash_verification_token(token)` (hashed token), not the plain token.

### 2.3 Backend (Email Templates + Env)

- `backend/open_webui/utils/email.py`
  - `build_password_reset_email(...)`
  - `build_password_reset_confirmation_email(...)`
- Template:
  - `backend/open_webui/templates/email/reset_password.html`
- Env:
  - `backend/open_webui/env.py`
    - `PASSWORD_RESET_TOKEN_TTL`
    - `PASSWORD_RESET_LINK_BASE_URL`

### 2.4 Backend (Migration)

Peewee migration added to create this table:
- `backend/open_webui/internal/migrations/020_add_password_reset_request.py`

> Note: There is no dedicated Alembic migration for `password_reset_request` under `backend/open_webui/migrations/versions/`. Make sure your runtime migration runner (peewee vs alembic) matches your deployment environment.

### 2.5 Frontend (Pages + API)

Pages:
- `src/routes/auth/forgot-password/+page.svelte`
  - user email input → `requestPasswordResetEmail(email)`
- `src/routes/auth/reset-password/+page.svelte`
  - query params: `token`, `email`
  - submit → `resetPasswordWithToken(token, newPassword, email?)`

API client:
- `src/lib/apis/auths/index.ts`
  - `requestPasswordResetEmail(email)` → `POST /auths/password-reset/request`
  - `resetPasswordWithToken(token, password, email?)` → `POST /auths/password-reset/confirm`

---

## 3) Feature: Payment Integration (bKash) + Transactions + Invoice PDF

### 3.1 Backend (Routes)

All payment APIs:
- `backend/open_webui/routers/payments.py` (prefix `/api/v1/payments`)

User / public:
- `GET /api/v1/payments/plans`
  - Public API used to serve pricing plans to the UI.
- `POST /api/v1/payments/bkash/create`
  - body (frontend): `{ plan_id?, amount, currency?, payer_reference?, merchant_invoice_number?, intent?, mode? }`
- `POST /api/v1/payments/bkash/execute`
  - body: `{ payment_id }`
- `GET /api/v1/payments/bkash/query?payment_id=...`
  - transaction status fetch
- `GET|POST /api/v1/payments/bkash/callback`
  - gateway return/callback handle
  - DB transaction update + event log
  - When status is “completed”, the token budget is updated (see below).
- `GET /api/v1/payments/me/subscription`
- `POST /api/v1/payments/me/subscription/pause`
- `POST /api/v1/payments/me/subscription/cancel`
- `GET /api/v1/payments/transactions`
  - user payment history (pagination/filter)
- `GET /api/v1/payments/invoices/{transaction_id}.pdf`
  - PDF invoice stream (FPDF generate)

Admin dashboard APIs:
- `GET /api/v1/payments/admin/payments/transactions`
- `GET /api/v1/payments/admin/payments/metrics`
- `GET /api/v1/payments/admin/payments/kpis`
- `GET /api/v1/payments/admin/payments/users/summary`
- `GET /api/v1/payments/admin/payments/plans/summary`
- `GET /api/v1/payments/admin/transactions/plans?plan_id=...`
- `GET /api/v1/payments/admin/payments/transactions/export` (CSV)

### 3.2 Backend (Models + DB)

- `backend/open_webui/models/payments.py`
  - tables:
    - `payment_transaction`
    - `payment_event`
  - `PaymentTransactions` helper:
    - create/update/get by `payment_id`
  - `PaymentEvents` helper: event log

Migrations (Alembic):
- `backend/open_webui/migrations/versions/5b4f2c7a9d11_add_payment_transactions.py`
- `backend/open_webui/migrations/versions/8f0b9d7c2a1a_add_payment_events.py`

### 3.3 Backend (bKash client + Config)

- `backend/open_webui/utils/bkash_client.py`
  - `create_payment(...)`, `execute_payment(...)`, `query_payment(...)`, etc.
- Env (runtime):
  - `backend/open_webui/env.py`
    - `BKASH_BASE_URL`, `BKASH_APP_KEY`, `BKASH_APP_SECRET`
    - `BKASH_USERNAME`, `BKASH_PASSWORD`
    - `BKASH_CALLBACK_URL`
    - `BKASH_PAYER_REFERENCE`
    - `BKASH_WEBHOOK_SECRET`
    - `BKASH_TIMEOUT_SECONDS`
    - checkout credentials: `BKASH_CHECKOUT_URL_*`
- PersistentConfig mapping:
  - `backend/open_webui/config.py` → `payments.bkash.*` keys

### 3.4 Backend (Invoice PDF)

- `backend/open_webui/routers/payments.py`
  - `_build_invoice_pdf_bytes(...)` (FPDF)
  - Logo path usage: `backend/open_webui/static/logo.png` (if exists)

Tests:
- `backend/open_webui/test/apps/webui/routers/test_payments_invoice.py`
- `backend/open_webui/test/util/test_bkash_client.py`

### 3.5 Payment → Token Budget Auto Update (Cross-feature Integration)

When payment is “completed”:
- `backend/open_webui/routers/payments.py`
  - `_maybe_update_token_budget_for_completed_payment(...)`
    - `TokenWindowAggregates.reset_user_usage(user_id=...)`
    - `TokenBudgets.apply_plan_budget(user_id, plan_id, created_by)`

Related models:
- `backend/open_webui/models/token_budgets.py`
- `backend/open_webui/models/token_usage.py`

### 3.6 Frontend (Pages + Components + API)

API client:
- `src/lib/apis/payments/index.ts`
  - `createBkashPayment(token, body)` → `POST /payments/bkash/create`
  - `executeBkashPayment(token, body)` → `POST /payments/bkash/execute`
  - `queryBkashPayment(token, payment_id)` → `GET /payments/bkash/query`
  - User:
    - `getMySubscriptionDetails(token)` → `GET /payments/me/subscription`
    - `pauseMySubscription(token)` → `POST /payments/me/subscription/pause`
    - `cancelMySubscription(token)` → `POST /payments/me/subscription/cancel`
    - `listMyPaymentTransactions(token, params)` → `GET /payments/transactions`
    - `downloadMyInvoicePdf(token, transaction_id)` → `GET /payments/invoices/{id}.pdf`
  - Admin:
    - `adminListPaymentTransactions(...)` → `/payments/admin/payments/transactions`
    - `adminPaymentMetrics(...)` → `/payments/admin/payments/metrics`
    - `adminPaymentKpis(...)` → `/payments/admin/payments/kpis`
    - `adminPaymentPlansSummary(...)` → `/payments/admin/payments/plans/summary`
    - `adminPaymentUsersSummary(...)` → `/payments/admin/payments/users/summary`
    - `adminPlanTotalAmount(...)` → `/payments/admin/transactions/plans`
    - `adminExportPaymentTransactions(...)` → `/payments/admin/payments/transactions/export`

Payment UX pages:
- `src/routes/pricing/+page.svelte`
  - plan selection + payment initiation (bKash API calls)
  - overlay: `AccountPending` component render
- `src/routes/success/+page.svelte` (gateway success landing)
- `src/routes/cancel/+page.svelte` (gateway cancel landing)
- `src/routes/failed/+page.svelte` (gateway failure landing)

Payment status overlay:
- `src/lib/components/layout/Overlay/AccountPending.svelte`
  - Reads return URL query params (status/paymentID).
  - Confirms status server-side via `queryBkashPayment(...)` and updates the UI.

Shared plan data (UI-side plan labels/prices):
- `src/lib/data/pricing.ts`

---

## 4) Feature: User Dashboard → (i) Payment Details (ii) Uses Token

> In your UI these are integrated as “User Settings” modal/tabs.

### 4.1 Payment Details (User)

Where it is mounted:
- `src/lib/components/chat/SettingsModal.svelte`
  - tabs: `payment_details` (title: “Payment Details”)
  - component mount: `<PaymentDetails />`

UI component:
- `src/lib/components/chat/Settings/PaymentDetails.svelte`
  - calls:
    - `getMySubscriptionDetails(localStorage.token)`
    - `listMyPaymentTransactions(localStorage.token, { page, page_size, ... })`
    - `downloadMyInvoicePdf(localStorage.token, transaction_id)`
    - `pauseMySubscription(...)`, `cancelMySubscription(...)`
    - `listPricingPlans()` (backend `/payments/plans`) + fallback UI plan map (`src/lib/data/pricing.ts`)

Backend endpoints used:
- `GET /api/v1/payments/me/subscription`
- `POST /api/v1/payments/me/subscription/pause`
- `POST /api/v1/payments/me/subscription/cancel`
- `GET /api/v1/payments/transactions`
- `GET /api/v1/payments/invoices/{transaction_id}.pdf`
- `GET /api/v1/payments/plans`

### 4.2 Uses Token (User Token Usage)

Where it is mounted:
- `src/lib/components/chat/SettingsModal.svelte`
  - tabs: `token_usage` (title: “Uses Token”)

UI component:
- `src/lib/components/chat/Settings/TokenUsage.svelte`
  - calls (token required):
    - `getTokenUsageSummary(token, params?)`
    - `getTokenUsageSeries(token, params?)`
    - `getTokenUsageByModel(token, params?)`
    - `getTokenUsageActivity(token, params?)`
    - `getTokenUsageActivityDetail(token, activity_id)`

API client:
- `src/lib/apis/token_usage/index.ts`

Backend endpoints used (all prefix `/api/v1`):
- `GET /token-usage/summary`
- `GET /token-usage/series`
- `GET /token-usage/models`
- `GET /token-usage/activity`
- `GET /token-usage/activity/{activity_id}`

---

## 5) Feature: Admin Dashboard → Payments Page + Token Budgets Page

### 5.1 Admin Payments Page

Routes/UI:
- `src/routes/(app)/admin/payments/+page.svelte`
  - mount: `src/lib/components/admin/Payments.svelte`
- `src/routes/(app)/admin/+layout.svelte`
  - Adds the `/admin/payments` link in the sidebar/nav.

Component:
- `src/lib/components/admin/Payments.svelte`
  - uses `src/lib/apis/payments/index.ts` admin functions
  - user list/lookup:
    - `src/lib/apis/users` (e.g. `getUsers(...)`)

Backend used:
- `backend/open_webui/routers/payments.py` admin endpoints (section 3.1)

### 5.2 Admin Token Budgets (User-wise monthly limit)

UI integration:
- `src/lib/components/admin/Users.svelte`
  - mount: `src/lib/components/admin/Users/TokenBudgets.svelte`

Component:
- `src/lib/components/admin/Users/TokenBudgets.svelte`
  - search user:
    - `searchUsers(localStorage.token, query, ...)` from `src/lib/apis/users`
  - read status:
    - `getUserTokenBudgetStatus(token, user_id)`
  - save budget:
    - `upsertUserTokenBudget(token, user_id, { limit_tokens, enabled, timezone })`

API client:
- `src/lib/apis/token_budgets/index.ts`

Backend:
- `backend/open_webui/routers/token_budgets.py`
  - `PUT /api/v1/admin/token-budgets/users/{user_id}`
  - `GET /api/v1/admin/token-budgets/users/{user_id}/status`
  - `GET /api/v1/admin/token-budgets`

Model/DB:
- `backend/open_webui/models/token_budgets.py` (`token_budget` table)

Test coverage:
- `backend/open_webui/test/apps/webui/routers/test_admin_token_budgets.py`

---

## 6) Feature: Token Budget Enforcement + Token Usage Tracking (Chat Pipeline Integration)

This is a “cross-cutting” feature: enforce token budgets on chat requests and maintain usage events/aggregates.

### 6.1 Budget Service

- `backend/open_webui/utils/token_budget.py`
  - `TokenBudgetService.get_status(user_id, ...)`
  - `TokenBudgetService.reserve(request_id, estimate_tokens, ...)`
  - `TokenBudgetService.finalize(request_id, total_tokens, ...)`
  - `TokenBudgetService.release(request_id, status="error", ...)`

### 6.2 Token usage tables

- `backend/open_webui/models/token_usage.py`
  - `token_usage_event` (per request event)
  - `token_window_aggregate` (monthly aggregate per user)
- Alembic migration:
  - `backend/open_webui/migrations/versions/1c2a4e7b9d0f_add_token_budgets_and_usage.py`

### 6.3 Chat pipeline hook

- `backend/open_webui/utils/chat.py`
  - Calls `TokenBudgetService.reserve(...)` before the provider call.
  - On stream/non-stream completion it calls `finalize(...)`; on error it calls `release(...)`.
  - request-scoped state:
    - `request.state.token_budget_request_id`
    - `request.state.token_budget_active`

Tests:
- `backend/open_webui/test/apps/webui/utils/test_token_budget_direct.py`
- `backend/open_webui/test/models/test_default_signup_token_budget.py`

---

## 7) Feature: Home Page, Pricing Page, About Page

### 7.1 Routes

- Home:
  - `src/routes/auth/home/+page.svelte`
- About:
  - `src/routes/auth/about/+page.svelte`
- Pricing:
  - `src/routes/pricing/+page.svelte`

Common layout / navigation:
- `src/routes/+layout.svelte`
- `src/routes/+layout.js` (about page trailing slash config comment)

### 7.2 Backend API integration (for these pages)

- Pricing page → payment flow:
  - `src/routes/pricing/+page.svelte` → `src/lib/apis/payments/index.ts` → backend `/api/v1/payments/bkash/*`
- “Pricing plans list” backend API:
  - `GET /api/v1/payments/plans` (used by the `PaymentDetails` UI component)
  - The Pricing page itself primarily uses client-side plan data:
    - `src/lib/data/pricing.ts` and/or local arrays in the pricing route

---

## 8) Quick API Checklist (UI ↔ Backend)

Auth:
- `POST /api/v1/auths/signup`
- `POST /api/v1/auths/signup/verify`
- `GET /api/v1/auths/signup/verify/link`
- `POST /api/v1/auths/signup/resend`
- `POST /api/v1/auths/password-reset/request`
- `GET /api/v1/auths/password-reset/validate`
- `POST /api/v1/auths/password-reset/confirm`

Payments:
- `GET /api/v1/payments/plans`
- `POST /api/v1/payments/bkash/create`
- `POST /api/v1/payments/bkash/execute`
- `GET /api/v1/payments/bkash/query`
- `GET|POST /api/v1/payments/bkash/callback`
- `GET /api/v1/payments/me/subscription`
- `POST /api/v1/payments/me/subscription/pause`
- `POST /api/v1/payments/me/subscription/cancel`
- `GET /api/v1/payments/transactions`
- `GET /api/v1/payments/invoices/{transaction_id}.pdf`
- Admin:
  - `GET /api/v1/payments/admin/payments/transactions`
  - `GET /api/v1/payments/admin/payments/metrics`
  - `GET /api/v1/payments/admin/payments/kpis`
  - `GET /api/v1/payments/admin/payments/users/summary`
  - `GET /api/v1/payments/admin/payments/plans/summary`
  - `GET /api/v1/payments/admin/transactions/plans`
  - `GET /api/v1/payments/admin/payments/transactions/export`

Token usage (User):
- `GET /api/v1/token-usage/summary`
- `GET /api/v1/token-usage/series`
- `GET /api/v1/token-usage/models`
- `GET /api/v1/token-usage/activity`
- `GET /api/v1/token-usage/activity/{activity_id}`

Token budgets (Admin):
- `PUT /api/v1/admin/token-budgets/users/{user_id}`
- `GET /api/v1/admin/token-budgets/users/{user_id}/status`
- `GET /api/v1/admin/token-budgets`

---

## 9) Folder Tree (Feature Files)

```text
open-webui/
|-- explore-architecture/
|   `-- Developent File Overview.md                    # This document (integration map)
|-- backend/
|   `-- open_webui/
|       |-- main.py                                    # FastAPI router registration (include_router)
|       |-- env.py                                     # Env flags (email verification, reset, bkash)
|       |-- config.py                                  # PersistentConfig keys (payments.bkash.*)
|       |-- routers/
|       |   |-- auths.py                               # Signup verify (OTP/link) + forgot/reset password APIs
|       |   |-- payments.py                            # bKash integration + invoices + admin payment dashboards
|       |   |-- token_budgets.py                       # Admin token budget APIs
|       |   `-- token_usage.py                         # User token usage APIs
|       |-- models/
|       |   |-- auths.py                               # User creation hook: default token budget
|       |   |-- email_verifications.py                 # email_verification table (OTP + link token)
|       |   |-- password_reset.py                      # password_reset_request table
|       |   |-- payments.py                            # payment_transaction + payment_event tables
|       |   |-- token_budgets.py                       # token_budget table + plan budget mapping
|       |   `-- token_usage.py                         # token_usage_event + token_window_aggregate tables
|       |-- utils/
|       |   |-- bkash_client.py                        # bKash HTTP client
|       |   |-- chat.py                                # TokenBudgetService hooks around chat calls
|       |   |-- email.py                               # Email builders + SMTP send
|       |   |-- email_verification.py                  # OTP/token generation + hashing helpers
|       |   `-- token_budget.py                        # Budget reserve/finalize/release service
|       |-- templates/
|       |   `-- email/
|       |       |-- reset_password.html                # Password reset email template
|       |       `-- verify_signup.html                 # Signup verification email template
|       |-- static/
|       |   `-- logo.png                               # Invoice PDF logo (optional)
|       |-- migrations/
|       |   `-- versions/
|       |       |-- 1c2a4e7b9d0f_add_token_budgets_and_usage.py              # Alembic: token budget/usage tables
|       |       |-- 5b4f2c7a9d11_add_payment_transactions.py                 # Alembic: payment_transaction
|       |       |-- 7f2b1a4c9f4d_add_email_verification.py                   # Alembic: email_verification
|       |       |-- 8f0b9d7c2a1a_add_payment_events.py                       # Alembic: payment_event
|       |       `-- c9f0c2b1d5a7_add_email_verification_link_token.py        # Alembic: link token fields
|       |-- internal/
|       |   `-- migrations/
|       |       |-- 019_add_email_verification.py         # Peewee placeholder (sequence alignment)
|       |       `-- 020_add_password_reset_request.py     # Peewee: password_reset_request table
|       `-- test/
|           |-- apps/webui/routers/
|           |   |-- test_admin_token_budgets.py          # Tests: admin token budget APIs
|           |   |-- test_auths.py                        # Tests: signup verify (OTP/link) flows
|           |   `-- test_payments_invoice.py             # Tests: invoice PDF endpoint
|           |-- apps/webui/utils/
|           |   `-- test_token_budget_direct.py          # Tests: token budget enforcement
|           |-- models/
|           |   `-- test_default_signup_token_budget.py  # Tests: signup creates default token budget
|           `-- util/
|               `-- test_bkash_client.py                 # Tests: bKash client
`-- src/
    |-- lib/
    |   |-- constants.ts                                 # WEBUI_API_BASE_URL
    |   |-- data/
    |   |   `-- pricing.ts                               # UI plan metadata (fallback/map)
    |   |-- apis/
    |   |   |-- auths/index.ts                           # Frontend auth API client (verify + reset)
    |   |   |-- payments/index.ts                        # Frontend payments API client (user + admin)
    |   |   |-- token_budgets/index.ts                   # Frontend admin token budgets API client
    |   |   `-- token_usage/index.ts                     # Frontend token usage API client
    |   `-- components/
    |       |-- admin/
    |       |   |-- Payments.svelte                      # Admin Payments dashboard UI
    |       |   `-- Users/
    |       |       `-- TokenBudgets.svelte              # Admin Token Budgets UI
    |       |-- chat/
    |       |   |-- SettingsModal.svelte                 # Tabs: Payment Details + Uses Token
    |       |   `-- Settings/
    |       |       |-- PaymentDetails.svelte            # User Payment Details UI
    |       |       `-- TokenUsage.svelte                # User Token Usage UI
    |       `-- layout/
    |           `-- Overlay/
    |               `-- AccountPending.svelte            # Pricing/payment status overlay (bKash return)
    `-- routes/
        |-- +layout.js                                   # Global layout config
        |-- +layout.svelte                               # Global layout shell
        |-- pricing/+page.svelte                         # Pricing page + payment init
        |-- success/+page.svelte                         # Payment success landing
        |-- cancel/+page.svelte                          # Payment cancel landing
        |-- failed/+page.svelte                          # Payment failed landing
        |-- auth/
        |   |-- +page.svelte                             # Signin/Signup + email verification UI
        |   |-- forgot-password/+page.svelte             # Forgot password UI
        |   |-- reset-password/+page.svelte              # Reset password UI
        |   |-- home/+page.svelte                        # Home page
        |   `-- about/+page.svelte                       # About page
        `-- (app)/
            `-- admin/
                |-- +layout.svelte                       # Admin layout + nav link to payments
                `-- payments/+page.svelte                # Admin Payments route (mounts component)
```
