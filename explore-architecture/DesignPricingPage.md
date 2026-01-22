# Pricing Page Plan

## Goals
- Build a pricing overlay UI in `src/lib/components/layout/Overlay/AccountPending.svelte`.
- Apply the accent color `rgba(146, 39, 143)` in highlights, borders, and glow.
- Include all provided pricing copy and the full compare-features matrix.
- Add a short "token usage" explainer for how usage works after purchase.

## Layout Outline
1. Hero: title + subtitle with a short lead-in.
2. Individual plans: Free, Go, Plus, Pro (grid of cards).
3. Business + Enterprise: two-card row with the long Business copy.
4. Token usage section: compact bullets.
5. Comparison table: grouped rows for Essentials, Models, Features.

## Visual Direction
- Deep gradient backdrop with subtle orbs/patterns; avoid flat white.
- CSS variables for color, surfaces, and typography.
- Staggered card reveal on load; respect reduced-motion.

## Responsive Notes
- Stack cards on mobile; maintain readable spacing.
- Make the comparison table horizontally scrollable on small screens.
# Pricing Page Plan

## Intent
- Add a pricing section to the pending account overlay so users can review plan options while waiting for activation.
- Use the accent color `rgba(146, 39, 143, 1)` for key UI elements (CTAs, borders, highlights).
- Include a short token-usage explanation related to plan purchases.

## Layout
- Keep the current pending-account messaging at the top.
- Add a pricing header (title + subtitle) and a token-usage callout.
- Add a responsive grid of plan cards (Free, Go, Plus, Pro, Business).
- Add a compare section with a CTA strip and a horizontal comparison table covering all listed features.

## Implementation Notes
- Use data arrays in the Svelte component to keep markup concise and avoid repeated blocks.
- Add component-scoped CSS variables for the accent color and background gradient.
- Ensure the pricing area scrolls on smaller screens without hiding the existing actions.
