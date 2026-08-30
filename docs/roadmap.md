# Roadmap

Unscheduled product directions. Nothing here is a commitment to a date, a
framework, or an API. Detailed design is intentionally deferred to the session
that picks the item up.

## STEM card expansion

The STEM collection (`src/ankinote/collections/stem/`) now covers three card
types — `concept`, `formula`, `procedure` — with structured schema fields
(`latex`, `variables`, `steps`) rendered into the stored `back_detail` HTML.
The legacy `math` collection was removed once STEM superseded it: `concept` and
`formula` cards cover explanatory and formula content better than the old
all-in-one `MathModel`, and its remaining extras (`key_points`,
`related_concepts`, `difficulty`, multi-image example lists) were judged to be
prose or metadata that belong in `back_detail`, in Anki tags, or on their own
cards.

### Design constraints (carried over from the completed schema work)

- `StemNoteType` stays all-string. New structured AI output is rendered to HTML
  in `_build_note_data()` before storage, so no note-type migration is needed
  and existing notes keep rendering.
- New visual elements only extend the existing token set in
  `stem/card_templates/style.css` (`--badge-<type>-*`, `--accent*`, `--paper*`).
  No new fonts, layouts, or themes; keep the paper-card / amber-accent / serif
  look.
- New prompts follow the current contract: JSON-only output, same-language
  rule, escaped LaTeX in JSON, English Title Case tags, every new key optional
  so older outputs still validate.

### Worked-example card type

The highest-value gap. Worked examples train *production* (solve this problem)
rather than *recognition*, and are general to STEM problem-solving, not
math-specific. The old `math` collection modelled 1–3 examples as a sub-list on
a single note, which cannot be reviewed or scheduled independently — the
replacement is one card per problem.

- Add `CardType.EXAMPLE`:
  - `front` = the problem statement.
  - `back_brief` = the final answer only.
  - `back_detail` = the fully worked solution; reuse the `steps` field and its
    numbered-list rendering for the solution steps.
  - `image_description` = optional figure (geometry, function graph, circuit).
- Add `prompts/example.md`: problem difficulty matched to the topic, no trivial
  restatement of a definition, one self-contained problem per card. Register
  the type in the generator's auto-detection instruction.
- Badge token pair (`--badge-example-*`) and a template branch consistent with
  the other types.
- Focused tests mirroring `test_stem_collection.py`: model validation with and
  without the new keys, `_build_note_data()` HTML, one end-to-end mocked
  generation.

### Comparison card type

Contrast pairs (L1 vs L2 regularization, bias vs variance, TCP vs UDP) — a
common study need with no current home.

- Add `CardType.COMPARISON` with structured fields: `items` (name + definition)
  and `aspects` (aspect + per-item values) so the back renders as a real
  aspect-by-aspect table that stacks vertically on narrow screens.
- Add `prompts/comparison.md`; include the type in auto-detection.
- `--badge-comparison-*` token pair following the existing badge pattern.

### Progressive disclosure and rendering polish

- Wrap the `back_detail` section of `back.html` in `<details>/<summary>` so
  recall practice sees the brief answer first, with detail one tap away. Verify
  `<details>` behaviour on Anki desktop and AnkiDroid before committing;
  fall back to always-visible detail where unsupported.
- Shared MathJax macro configuration for common notation.

### Misconception callout (optional, small)

Rather than a new type, an optional `common_mistakes: list[str]` field rendered
as a small warning-styled callout at the bottom of `back_detail`, reusing
existing `--error` / muted tones. Update `_system.md` guidance on when to
populate it.

### Rough delivery order

The worked-example and comparison types are independent of each other and each
sized for one focused session. Progressive disclosure is independent of both.
The misconception callout folds into whichever session touches the templates
last.

## Future major version: deployable web service

Explore evolving ankinote from a local CLI/NiceGUI application into a web
service that can be deployed to the public internet.

The web version must include user identity and access management as a
foundational concern, rather than an afterthought. Initial planning should
cover:

- user registration, sign-in, sign-out, and secure session management;
- account recovery and verification flows;
- authorization and strict per-user data isolation;
- secure storage and handling of user-provided AI-provider credentials, if
  supported;
- deployment, HTTPS, secrets management, observability, and abuse/rate-limit
  controls;
- how web users create and synchronize cards with Anki, without assuming a
  publicly reachable AnkiConnect instance.

Status: idea only; not scheduled and not a commitment to a specific framework
or authentication provider.
