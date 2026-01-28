# Development Plan — Token Uses (User Settings) — Pages 1–4

## Phase 1 Complete — Setup & Navigation
Status: **Completed (frontend-only plan)**
- Route defined: `/settings/token-usage`
- Sidebar placement: below **Payment Details** as **Uses Token**
- Settings layout reuse noted (cards, spacing, dark mode)
- i18n requirement captured
- No backend integration; local mock data only

## Page 1 — Setup & Navigation (Frontend-only)
- Create a new settings route: `/settings/token-usage`.
- Add sidebar entry under **User Settings** below **Payment Details** labeled **Uses Token**.
- Use existing settings layout wrappers for consistent spacing, dark mode, and cards.
- Ensure all text uses `i18n.t(...)`.
- No backend integration; prepare local mock data in the page module.

## Page 2 — Header + Summary Cards
- Header:
  - Title: `Uses Token`
  - Subtitle: `Track your token usage across models and time.`
- Summary cards (6 tiles):
  - Used (%)
  - Window start (UTC)
  - Used (tokens)
  - Limit (tokens)
  - Remaining (tokens)
  - Reserved (tokens)
- Use existing card styles and number formatting (e.g., `12,340`).

## Page 3 — Usage Chart
- Add a chart card for tokens over time (line/area).
- Tooltip shows: date + tokens + top model for that day.
- Wire chart to local mock series data.
- Add loading skeleton state for the chart.

## Page 4 — Breakdown + Recent Activity
- **Breakdown by Model** table:
  - Columns: model name, tokens, % share.
  - Use table styles consistent with admin/settings tables.
- **Recent Activity** table:
  - Columns: time (UTC/local toggle), model, type, input tokens, output tokens, total, details link.
  - Row click opens a right-side drawer with breakdown (frontend-only).
- Add empty and error states for both tables.

## Phase 4 — API Contracts & Data Model
- Define API endpoints for token usage summary, time series, model breakdown, and recent activity.
- Document request params (date range, timezone, pagination, filters).
- Define response types and error shapes.
- Add TypeScript interfaces in the frontend for all payloads.

## Phase 5 — API Client Integration
- Add client functions in `$lib/apis` for token usage endpoints.
- Include auth token, error handling, and retry strategy.
- Add loading/error state handling in the UI.

## Phase 6 — Wire Summary + Chart to Live Data
- Replace mock summary cards with API response.
- Replace chart series with API time series.
- Add date range selector (month/week/custom) and refresh on change.

## Phase 7 — Wire Tables + Pagination
- Replace model breakdown table with API data.
- Replace recent activity table with API data.
- Add pagination and page size controls.
- Add filters: model, type, time range.

## Phase 8 — Drawer Details & Deep Links
- Add activity row click handler to open details drawer.
- Fetch full activity detail by ID.
- Support deep links to open a specific activity.

## Phase 9 — Observability & QA
- Add logging for API failures.
- Add unit tests for API client.
- Add UI tests for loading, empty, and error states.

## Phase 10 — Security Concerns
- Validate auth/permissions for user-scoped token usage endpoints.
- Enforce rate limits and pagination bounds.
- Avoid leaking sensitive IDs; use opaque identifiers for activity rows.
- Sanitize and validate all query params (date range, filters).
- Ensure PII-safe logging and redact tokens in client logs.
