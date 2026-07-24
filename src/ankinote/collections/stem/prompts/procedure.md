# STEM Procedure Card Generation

Return **only** a valid JSON object, no markdown, no comments. The *input* you receive will be a **problem-solving procedure, algorithm, or method** in a STEM field.

```json
{
  "card_type": "procedure",
  "front": "A problem prompt that this procedure solves (e.g. 'How do you find the inverse of a matrix?').",
  "back_brief": "The procedure in 2\u20134 numbered steps, condensed to the essential actions only.",
  "back_detail": "The full procedure with each step explained, including when to apply it, common pitfalls, and any decision points. LaTeX for mathematical expressions.",
  "tags": ["Computer Science", "Algorithms"],
  "image_description": "Describe what to draw, or null if no diagram needed."
}
```

## Field Rules

- `front` — phrase as a *how-to* question that naturally calls for the procedure. Be specific enough that the scope is clear.
- `back_brief` — numbered steps only, one clause each. No explanations. Think of it as a checklist a practitioner would glance at.
- `back_detail` — expand each step with reasoning, conditions, and common errors. Include a worked skeleton or symbolic example where helpful. Use LaTeX for all mathematical expressions.
- `tags` — 2-4 English tags in Title Case, e.g. ["Computer Science", "Algorithms"].
- `image_description` — if a flowchart or diagram clarifies the procedure, describe what to draw. Otherwise null.

## General Guidelines

- Steps must be actionable and ordered.
- `back_brief` should be short enough to fit on a single screen glance (\u22644 steps preferred).
- Never return `null` for any field except `image_description`.
- Output **only** valid JSON.
