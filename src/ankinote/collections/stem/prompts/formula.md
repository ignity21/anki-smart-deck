# STEM Formula Card Generation

Return **only** a valid JSON object, no markdown, no comments. The *input* you receive will be a **formula, theorem, or law** in a STEM field.

```json
{
  "card_type": "formula",
  "front": "The name of the formula or theorem, phrased as a prompt (e.g. 'State Newton\u2019s second law.' or 'Quadratic formula').",
  "back_brief": "The formula itself in LaTeX, plus a one-line statement of what it expresses.",
  "back_detail": "Assumptions and conditions of validity, and a note on physical or mathematical meaning. LaTeX throughout. Do NOT repeat the variable definitions here — they belong in `variables`.",
  "latex": "F = m \\cdot a",
  "variables": [
    {"symbol": "F", "description": "Net force acting on the object (N)"},
    {"symbol": "m", "description": "Mass of the object (kg)"},
    {"symbol": "a", "description": "Acceleration (m/s²)"}
  ],
  "tags": ["Math", "Physics"],
  "image_description": "Describe what to draw, or null if no diagram needed."
}
```

## Field Rules

- `front` — use the conventional name. Prefer imperative phrasing for theorems (*"State Bayes' theorem."*), noun phrasing for formulas (*"Euler's identity"*).
- `back_brief` — lead with the formula in LaTeX (e.g. `$F = ma$`), followed by one sentence describing what it relates. No variable definitions here.
- `latex` — the core expression only, bare LaTeX with **no** `\(...\)` or `\[...\]` delimiters and no surrounding prose (e.g. `x = \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}`). It is rendered as a centered display block. Omit or set to null for purely verbal statements (e.g. some laws expressed in words).
- `variables` — one entry per symbol, each with `symbol` (bare LaTeX, no delimiters) and `description` including units. Omit or set to null when there is nothing meaningful to tabulate.
- `back_detail` — state the domain of validity (e.g. units, assumptions, edge cases), and give the key insight or physical meaning. If the formula has a common special case or limit, include it. Do not duplicate the `variables` table.
- `tags` — 2-4 English tags in Title Case, e.g. ["Math", "Calculus"].
- `image_description` — if a geometric or graphical interpretation helps, describe what to draw. Otherwise null.

## General Guidelines

- LaTeX is mandatory for all mathematical expressions.
- Keep `back_brief` self-contained enough to be useful at a glance.
- Never return `null` for any field except `image_description`, `latex`, and `variables`.
- Output **only** valid JSON.
