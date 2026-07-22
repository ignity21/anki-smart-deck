# STEM Formula Card Generation

Return **only** a valid JSON object, no markdown, no comments. The *input* you receive will be a **formula, theorem, or law** in a STEM field.

```json
{
  "card_type": "formula",
  "front": "The name of the formula or theorem, phrased as a prompt (e.g. 'State Newton's second law.' or 'Quadratic formula').",
  "back_brief": "The formula itself in LaTeX, plus a one-line statement of what it expresses.",
  "back_detail": "Definition of each variable, assumptions and conditions of validity, and a note on physical or mathematical meaning. LaTeX throughout."
}
```

## Field Rules

- `front` — use the conventional name. Prefer imperative phrasing for theorems (*"State Bayes' theorem."*), noun phrasing for formulas (*"Euler's identity"*).
- `back_brief` — lead with the formula in LaTeX (e.g. `$F = ma$`), followed by one sentence describing what it relates. No variable definitions here.
- `back_detail` — define every symbol, state the domain of validity (e.g. units, assumptions, edge cases), and give the key insight or physical meaning. If the formula has a common special case or limit, include it.

## General Guidelines

- LaTeX is mandatory for all mathematical expressions — never write formulas in plain text.
- Keep `back_brief` self-contained enough to be useful at a glance.
- Never return `null` for any field.
- Output **only** valid JSON — no markdown, no comments, no extra keys or text.
