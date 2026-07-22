# STEM Concept Card Generation

Return **only** a valid JSON object, no markdown, no comments. The *input* you receive will be a **concept or term** in a STEM field.

```json
{
  "card_type": "concept",
  "front": "The term or concept name, phrased as a question if natural (e.g. 'What is entropy?').",
  "back_brief": "A single concise definition, ≤2 sentences. No derivations or examples.",
  "back_detail": "A fuller explanation covering intuition, scope, and significance. May include MathJax for notation."
}
```

## Field Rules

- `front` — the concept name or a direct question form. Prefer question form for abstract concepts (e.g. *"What is a Fourier transform?"*), noun form for concrete objects (e.g. *"Eigenvalue"*).
- `back_brief` — a minimal, precise definition a student could recall in one breath. No examples, no derivations. MathJax allowed for essential notation only.
- `back_detail` — deepen the brief: add intuition, analogies, common misconceptions, and domain context. Use MathJax for any mathematical notation. Write in the same language as the input topic.
