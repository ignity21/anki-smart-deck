# STEM Procedure Card Generation

Return **only** a valid JSON object, no markdown, no comments. The *input* you receive will be a **problem-solving procedure, algorithm, or method** in a STEM field.

```json
{
  "card_type": "procedure",
  "front": "A problem prompt that this procedure solves (e.g. 'How do you find the inverse of a matrix?').",
  "back_brief": "The procedure in 2\u20134 numbered steps, condensed to the essential actions only.",
  "back_detail": "Reasoning, conditions, common pitfalls, and decision points behind the steps. LaTeX for mathematical expressions. Do NOT repeat the step list itself \u2014 it belongs in `steps`.",
  "steps": [
    "Check that the matrix is square.",
    "Compute the determinant; if it is 0, the inverse does not exist.",
    "Form the augmented matrix \\\\( [A \\mid I] \\\\) and row-reduce to \\\\( [I \\mid A^{-1}] \\\\)."
  ],
  "tags": ["Computer Science", "Algorithms"],
  "image_description": "Describe what to draw, or null if no diagram needed."
}
```

## Field Rules

- `front` — phrase as a *how-to* question that naturally calls for the procedure. Be specific enough that the scope is clear.
- `back_brief` — numbered steps only, one clause each. No explanations. Think of it as a checklist a practitioner would glance at.
- `steps` — the full ordered procedure as an array of strings, one string per step, each a complete actionable instruction. MathJax allowed inside steps. This array is rendered as a numbered list on the card.
- `back_detail` — expand on the steps with reasoning, conditions, and common errors, plus a worked skeleton or symbolic example where helpful. Do not duplicate the ordered list from `steps`. Use LaTeX for all mathematical expressions.
- `tags` — 2-4 English tags in Title Case, e.g. ["Computer Science", "Algorithms"].
- `image_description` — if a flowchart or diagram clarifies the procedure, describe what to draw. Otherwise null.

## General Guidelines

- Steps must be actionable and ordered.
- `back_brief` should be short enough to fit on a single screen glance (\u22644 steps preferred).
- Never return `null` for any field except `image_description` and `steps`.
- Output **only** valid JSON.
