# User Payment Details Showing Page UI Design for Frontend Plan

## Goal For Only UI design in the forntend
In the User Dashboard page, add a section where a user can view the plan they purchased, full payment details, and download a voucher.

## Primary Users
- Signed-in users with active or past subscriptions.
- Users who need a receipt/voucher for records.

## Core Requirements
- Show current plan name, tier, billing cycle, status, start date, and renewal/expiry date.
- Show payment summary (amount, currency(BDT), tax, discount, total).
- Show transaction details (payment method (BKash), transaction ID, invoice ID, paid date).
- Provide a "Download Voucher" button (PDF/receipt).
- Handle empty state (no plan purchased yet).

## Information Architecture
- User Dashboard
  - Billing & Subscription
    - Payment Details (this page)

## Sections
1) 
   - title: "Payment Details"
   - Short description: "View your plan and payment history."

2) Current Plan Card
   - Plan name and badge (Active / Expired / Cancelled)
   - Billing cycle (Monthly/Yearly)
   - Start date + next renewal/expiry date
   - CTA: "Manage Plan" (optional, if already exists)

3) Payment Summary
   - Amount, Tax, Discount, Total
   - Currency and payment status (Paid/Failed/Pending)

4) Transaction Details
   - Payment method (card type/last 4, or gateway)
   - Transaction ID
   - Invoice/Voucher ID
   - Paid date

5) Actions
   - Primary button: "Download Voucher"
   - Secondary: "Download Invoice" (optional)

6) Payment History (Optional)
   - Table with recent payments (date, amount, status, invoice link)

7) Empty State
   - Message: "No plan purchased yet."
   - CTA: "Explore Plans"

## Data Requirements
- User subscription info:
  - plan_name, tier, billing_cycle, status
  - start_date, renewal_date, expiry_date
- Payment summary:
  - amount, tax, discount, total, currency
  - payment_status
- Transaction details:
  - payment_method, transaction_id, invoice_id, paid_date
- Voucher/receipt file path or URL for download.

## UX Notes
- Show status with color-coded badge.
- Use clear date formats (e.g., 12 Mar 2025).
- If payment failed, show warning and retry action (if supported).
- Download button should indicate file type (e.g., "Download Voucher (PDF)").

## Acceptance Criteria
- User can view their current plan and payment details from the dashboard.
- Voucher download works and is scoped to the logged-in user.
- Empty state appears when no subscription exists.
- Page loads gracefully with slow or missing data.
