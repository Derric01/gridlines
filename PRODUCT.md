# Product

## Register

product

## Users

UK electricity procurement analysts reviewing national wind forecasts before making day-ahead market purchasing decisions. They need to know which forecast was available at decision time and how similar forecasts performed against later wind generation actuals.

## Product Purpose

Gridline is a decision workspace for replaying January 2026 day-ahead wind forecast vintages from Elexon and comparing them with national wind generation actuals. It uses only the Elexon `WINDFOR` and `FUELHH` datasets, filtered to `fuelType=WIND` for actuals. Success means a buyer can identify the latest forecast published before a documented decision cutoff, inspect forecast error, and understand source coverage and limitations without confusing a historical replay with a live forecast.

## Brand Personality

Clear, measured, evidence-led. The interface should feel calm and familiar, with the clarity of ChatGPT's product UI and the precision of an energy-market instrument. Copy is direct and describes the data and action plainly.

## Anti-references

- Do not make the product a chatbot or place a prompt box ahead of the forecast analysis.
- Avoid trading-terminal clutter, decorative gradients, fabricated live metrics, and buy/sell recommendations unsupported by wind data alone.
- Do not present missing or revised source records as complete or point-in-time accurate.

## Design Principles

- Put the decision-time forecast and its evaluation evidence in the same view.
- Make the decision cutoff, selected forecast vintage, source coverage, and limitations easy to inspect.
- Keep the analysis within the assignment's two-dataset boundary: national wind forecasts and wind actuals from Elexon.
- Use familiar controls and restrained color; reserve semantic colors for data states.
- Start in light mode, offer dark mode, and keep the same chart and analysis structure in both themes. Use graphite neutrals, deep green for primary actions and forecast identity, and amber/red only for semantic states.
- Keep charts legible and pair them with accessible tabular data.
- Treat loading, unavailable data, and partial coverage as first-class states.

## Accessibility & Inclusion

Target WCAG 2.2 AA. Support keyboard navigation, visible focus, screen-reader labels and announcements, non-color status cues, responsive layouts, and reduced motion.
