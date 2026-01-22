# Payment Dashboard Plan (Admin Panel UI)

## Observations
- Pricing UI lives in `src/routes/pricing/+page.svelte` and renders `src/lib/components/layout/Overlay/AccountPending.svelte` with the purple accent color `rgba(146, 39, 143)` and plan cards.
- User model fields available for UI mapping include `id`, `email`, `username`, `role`, `name`, `profile_image_url`, `created_at`, `updated_at`, `last_active_at`, and `settings` from `backend/open_webui/models/users.py`.

## Goals
- Add an admin-only payment dashboard UI (frontend only, no API wiring).
- Align with existing admin panel layout while reusing the pricing visual language where appropriate.

## Route + Entry
- Add a new admin nav item in `src/routes/(app)/admin/+layout.svelte` linking to `/admin/payments` (label "Payments" or "Billing").
- Add route `src/routes/(app)/admin/payments/+page.svelte` that renders a new component `src/lib/components/admin/Payments.svelte`.

## UI Structure
1. Header: title, short description, date range selector, primary action (e.g., "Create invoice").
2. KPI cards row: MRR, ARR, active subscriptions, churn, ARPU.
3. Revenue trend chart placeholder and plan mix donut placeholder.
4. Plans table: Free,Plus,Pro with price, active subs, and monthly revenue. Reuse pricing copy where helpful.
5. Recent invoices list: invoice id, customer, amount, status, issued date.
6. Customer table: name, email, role, plan, status, created_at, last_active_at (map to user model fields).
7. Settings section: payment provider status, currency, tax, trial length (static placeholders).

## Data + State (UI-only)
- Use local mock arrays for plans, invoices, and customers.
- Add placeholder statuses: `active`, `trialing`, `past_due`, `canceled`.
- Use `i18n.t` for visible strings.

## Styling Notes
- Keep admin panel spacing and typography conventions.
- Reuse the pricing accent color for highlights and CTAs.
- Provide card surfaces, subtle gradient strips, and dark-mode safe colors.

## Responsive
- Collapse KPI cards to 2-per-row and then 1-per-row on small screens.
- Make tables horizontally scrollable on narrow viewports.

## Acceptance Criteria
- Admin navigation includes the new Payments entry and routes correctly.
- Payment dashboard renders with mock data and responsive layout.
- No backend or API changes are required for this phase.
