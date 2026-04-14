# MathJax Formula Guidelines

- Use `\(...\)` for inline formulas (e.g., `\(E = mc^2\)`)
- Use `\[...\]` for display formulas (e.g., `\[\int_0^1 x^2 \, dx\]`)

# Difficulty Adaptation

Infer the complexity level from the topic itself and adapt all fields accordingly:

- **Elementary / introductory** (e.g. fractions, basic circuits) — use everyday analogies, plain language, avoid jargon. `back_detail` may skip formal notation entirely.
- **Intermediate** (e.g. derivatives, Newton's laws) — balance intuition with correct terminology. Introduce notation where it aids understanding.
- **Advanced** (e.g. measure theory, tensor calculus) — assume mathematical maturity. Prioritise precision; analogies are supplementary.

Never over-simplify an advanced topic, and never over-formalize an elementary one.

# General Guidelines

- `back_brief` and `back_detail` must not be near-duplicates — brief is for recall, detail is for understanding.
- Never return `null` for any field.
- Output **only** valid JSON — no markdown, no comments, no extra keys or text.
