# Development Plan: Admin Payment Dashboard (UI)

## Objective
Implement the admin-only payment dashboard UI described in `explore-architecture/PlanningPaymentDashboard.md`, with mock data and no backend/API changes.

## Phase 1: Admin Navigation + Route Skeleton
### Scope
Wire the admin navigation entry and route to a new Payments page component.

### Work Items
- Add a new tab link in `src/routes/(app)/admin/+layout.svelte` for `/admin/payments`.
- Create `src/routes/(app)/admin/payments/+page.svelte` to render `src/lib/components/admin/Payments.svelte`.
- Create the `Payments.svelte` component shell with a layout container and basic sections.

### Deliverables
- Admin navigation shows Payments.
- Payments route renders a placeholder dashboard layout.

## Phase 2: Core Layout + KPI Section
### Scope
Build the top-level layout and KPI cards with pricing-aligned accents.

### Work Items
- Add page header (title, description, date range selector, primary CTA).
- Implement KPI cards (MRR, ARR, active subscriptions, churn, ARPU).
- Add chart placeholders (revenue trend + plan mix) with empty-state messaging.
- Define local UI tokens (accent color, surface, borders) consistent with the pricing overlay.

### Deliverables
- Header + KPI row + chart placeholders visually aligned with admin panel styling.

## Phase 3: Tables + Mock Data
### Scope
Populate dashboard sections with local mock data and table layouts.

### Work Items
- Plans table with price, active subs, and monthly revenue (reuse pricing copy where helpful).
- Recent invoices list with status pills (`active`, `trialing`, `past_due`, `canceled`).
- Customer table using user model fields (name, email, role, created_at, last_active_at).
- Settings panel with static values (provider status, currency, tax, trial length).
- Use `i18n.t` for all visible strings.

### Deliverables
- Full dashboard UI renders with mock data and consistent typography.

## Phase 4: Responsive + Polish
### Scope
Ensure the dashboard works on mobile and desktop, with visual polish.

### Work Items
- Responsive grids for KPI cards (2-up then 1-up).
- Horizontal scroll for tables on small screens.
- Add subtle gradient strips and borders for section separation.
- Verify dark-mode legibility and CTA contrast.

### Deliverables
- Responsive, polished dashboard with consistent visual language.

## Acceptance Criteria
- Payments navigation and route work for admin users.
- All dashboard sections render with mock data (no backend/API usage).
- Layout remains readable and usable on mobile and desktop.
