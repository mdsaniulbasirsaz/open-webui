# Token Uses (User Settings) — Frontend-Only UI Plan

## Goal
We **first observed token limits, budgets, and models from the database** to understand the data shape.  
Now we are **replanning this as a frontend-only UI**, with **no backend integration** and **local mock data** only.

The page should show:
- Monthly token usage
- Usage by model/app
- Budget status and remaining estimate (frontend-only display)

## Placement & Navigation
- **Location:** `User Settings` → **below** `Payment Details` → **Uses Token`
- **Route (suggested):** `/settings/token-usage`
- **Sidebar label:** `Uses Token` (or `Token Usage`)
- **Header:** `Settings / Uses Token`

## UI Sections (Desktop + Mobile)
Use the existing settings card styles (rounded panels, subtle borders, dark mode).

1) **Header**
   - Title: `Uses Token`
   - Subtitle: `Track your token usage across models and time.`

2) **Summary Row (Cards)**
   - Used (percentage)
   - Window start (UTC)
   - Used (tokens)
   - Limit (tokens)
   - Remaining (tokens)
   - Reserved (tokens)

3) **Usage Chart**
   - Line/area chart: tokens over time
   - Tooltip: date + tokens + top model for that day

4) **Breakdown Table**
   - **By Model**
     - Model name, tokens, % share

5) **Recent Activity Table**
   - Columns:
     - Time (UTC/local toggle)
     - Model
     - Type (chat / tool / file / etc.)
     - Input tokens / Output tokens / Total
     - Conversation ID (link) or “Details”
   - Row click opens a side drawer with a breakdown (front-end only).

## States
- **Loading:** skeleton cards + table placeholders
- **Empty:** “No usage in this time range.” with “Reset filters”
- **Error:** inline callout with “Retry” and hidden “Details” text

## Accessibility & UX
- Keyboard accessible controls
- Screen-reader labels on tables
- Dark mode contrast compliant

## Frontend-Only Implementation Notes
- No backend calls or API integrations.
- Use **local mock data** (static JSON or inline arrays).
- All text behind `i18n.t(...)`.
- Reuse existing settings layout and card/table components.
