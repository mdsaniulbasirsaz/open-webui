# Development Plan: User Payment Details Showing Page (Phase 1-4)

## Phase 1 - Requirements + IA Lock (Completed)
### Scope
- Location: User Dashboard > Billing & Subscription > Payment Details.
- Purpose: Show purchased plan details and payment info with voucher download.
- UI-only for Phase 1 (mock data, no backend wiring yet).

### Finalized Sections
1) Header
   - Title: "Payment Details"
   - Description: "View your plan and payment history."
2) Current Plan Card
   - Plan name, tier, status badge (Active/Expired/Cancelled)
   - Billing cycle (Monthly/Yearly)
   - Start date, renewal/expiry date
   - Optional CTA: "Manage Plan"
3) Payment Summary
   - Amount, Tax, Discount, Total
   - Currency + payment status (Paid/Failed/Pending)
4) Transaction Details
   - Payment method (e.g., BKash)
   - Transaction ID, Invoice/Voucher ID
   - Paid date
5) Actions
   - Primary: "Download Voucher (PDF)"
   - Secondary: "Download Invoice" (optional)
6) Payment History (Optional)
   - Recent payments list/table (date, amount, status, invoice link)
7) Empty State
   - Message: "No plan purchased yet."
   - CTA: "Explore Plans"

### UI Data Shape (Mock)
- subscription:
  - plan_name, tier, billing_cycle, status
  - start_date, renewal_date, expiry_date
- payment_summary:
  - amount, tax, discount, total
  - currency (BDT), payment_status
- transaction:
  - payment_method, transaction_id, invoice_id, paid_date
- downloads:
  - voucher_url, invoice_url (optional)
- history (optional):
  - items[]: paid_date, amount, currency, status, invoice_url

### Copy Decisions
- Page title: "Payment Details"
- Description: "View your plan and payment history."
- Primary action: "Download Voucher (PDF)"
- Empty state: "No plan purchased yet."
- Empty state CTA: "Explore Plans"

## Phase 2 - UI Wireframe + Layout (Completed)
### Wireframe Structure (Desktop)
1) Page Header
   - Title and short description stacked.
2) Current Plan Card
   - Left: plan name + tier.
   - Right: status badge.
   - Two-column key-value grid for dates and billing cycle.
3) Payment Summary
   - Status badge aligned to the right of the section title.
   - 4-card summary grid (Amount, Tax, Discount, Total).
   - Currency note below the grid.
4) Transaction Details
   - Two-column key-value grid (method, paid date, transaction ID, invoice ID).
5) Actions
   - Primary filled button + secondary outlined button.
6) Payment History (Optional)
   - Vertical list with amount, invoice ID, date, status badge.
7) Empty State
   - Centered message, supporting text, CTA button.

### Wireframe Structure (Mobile)
- All sections stacked with full-width cards.
- Summary grid collapses to 2 columns (or 1 column on narrow screens).
- Action buttons wrap to two rows if needed.
- History list remains vertical with left-aligned details.

### Layout Blocks (Implemented)
- Header block: title + description.
- Card blocks: plan, summary, transaction, actions, history.
- Key-value grids: `grid` with 2-column split on `sm+`.
- Button group: inline on desktop, wraps on mobile.
- Empty state: dashed border card with CTA.

### Reusable UI Elements
- Status badge (rounded, tone-based).
- Key-value list (label + value pairs).
- Summary stat card (label + value).
- Button group (primary/secondary).

## Phase 3 - Visual Design + States (Completed)
### Visual Styling
- Use card surfaces with rounded corners, soft borders, and subtle shadows.
- Section titles in medium weight with muted helper text.
- Summary grid uses compact stat cards with consistent padding.
- Status badges use rounded pills with tone-based backgrounds.

### State Variations
- Plan status: Active / Expired / Cancelled.
- Payment status: Paid / Failed / Pending.
- Empty state: dashed border card with CTA.

### Loading Skeletons (Spec)
- Header: two lines (title + subtitle).
- Current plan: title line + badge + 4 key-value rows.
- Summary: 4 skeleton cards.
- Transaction: 4 key-value rows.
- Actions: 2 button skeletons.
- History: 3 list row skeletons.

### Formatting Rules
- Date format: `DD MMM YYYY` (e.g., `12 Mar 2025`).
- Currency: `BDT` prefix with thousands separators (e.g., `BDT 8,900`).

## Phase 4 - Final UI Spec + Handoff
- Prepare final UI spec with measurements and responsive behavior.
- Add example data for QA verification.
- Confirm download button placement and interaction notes.
- Review acceptance criteria from planning and finalize sign-off.
