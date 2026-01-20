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
