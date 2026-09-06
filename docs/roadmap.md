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

### Worked-example card type (shipped)

The highest-value gap. Worked examples train *production* (solve this problem)
rather than *recognition*, and are general to STEM problem-solving, not
math-specific. The old `math` collection modelled 1–3 examples as a sub-list on
a single note, which cannot be reviewed or scheduled independently — the
replacement is one card per problem.

`CardType.EXAMPLE` is added: `front` is the problem statement, `back_brief` is
the final answer only, `back_detail` is the reasoning that doesn't fit a step,
and the solution steps reuse the existing `steps` field and numbered-list
rendering — no new model fields or template branches were needed since
`front.html`/`back.html` already key off `card_type` generically. Guidance
lives in `_system.md` rather than a new `prompts/example.md`: the per-type
prompt files (`concept.md`, `formula.md`, `procedure.md`) turned out to never
be loaded by `generator.py` (dead code, now removed along with the unused
files) — all card types are actually driven by the single `_system.md`
prompt, so `example` guidance was added there instead of introducing another
unused file. Badge token pair `--badge-example-*` added.

Also added, beyond the original scope: optional reference-image input.
`StemGenerator.generate` / `StemCollection.generate_model` /
`generate_and_add_note` now accept `reference_image: bytes | None` (source
material such as a photographed problem, sent as a vision content part —
requires a vision-capable text model), exposed via `stem add --image PATH` in
the CLI and an upload control on the STEM GUI page. `TextMessage` in
`services/ai.py` was widened to allow list-of-parts content for this.

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
sized for one focused session. Worked-example shipped first (see above).
Progressive disclosure is independent of both. The misconception callout
folds into whichever session touches the templates last.

## Thinking control (shipped; follow-ups)

`TextGenerationService.generate_text` now takes `reasoning_effort`. The language
generators (`word`, `phrase`, `sentence`) pass `DISABLE_REASONING`, which the
service turns into DeepSeek's OpenAI-format `extra_body={"thinking": {"type":
"disabled"}}` (DeepSeek enables thinking by default and its LiteLLM routing
discards a plain `reasoning_effort`). `stem` keeps thinking on.

All CLI commands now take `--thinking [off|low|medium|high|default]` to override
the per-collection default for a single run. `services.ai.resolve_thinking`
(with `THINKING_CHOICES`) maps the choice to a `reasoning_effort` value; it is
shared by the CLI (`cli/factory` re-exports it) and the STEM generation page in
the GUI, which exposes the same five levels as a dropdown.

Open items:

- DeepSeek ignores `temperature` while thinking is on, so `stem`'s
  `temperature=0.3` is currently a no-op. Decide whether `stem` should also
  disable thinking (regaining temperature control) or drop the unused argument.
- The `extra_body` thinking field is DeepSeek-specific. If another text
  provider is adopted, translate `DISABLE_REASONING` per provider instead.
- Disabling thinking made the model less consistent about the output contract
  (`word` occasionally returns a bare record instead of a JSON array; now
  tolerated in `generate_word_data`). Watch for similar contract slips in the
  other language generators and tighten prompts or parsing as needed.

Status: minor follow-ups; not scheduled.

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
