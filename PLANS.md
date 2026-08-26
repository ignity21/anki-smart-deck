# Future Plans

## 0. Card-generation GUI roadmap

### Current baseline

The word-card generator is the only collection exposed through the NiceGUI
application today. The phrase and sentence collection implementations already
exist under `src/ankinote/collections/`, including prompts, text generation,
TTS, Anki note types/templates, CLI commands, batch commands, and collection
tests. The next milestone is therefore primarily an integration and
consistency effort, rather than a second implementation of those collections.

### Product and design direction

- **Audience:** language learners who capture vocabulary, reusable expressions,
  and production sentences while studying.
- **Page job:** turn one or many learner-provided items into Anki notes while
  making the item type and batch progress unambiguous.
- **Information architecture:** treat Word, Phrase & Idiom, and Sentence as
  three distinct learning lanes in the shared navigation. Each lane keeps the
  same familiar generate flow, but uses labels and examples appropriate to the
  item it accepts.
- **Visual direction:** preserve the existing app shell and settings workflow;
  add a compact card-type marker (word / expression / sentence) next to each
  page title and in results. This is the single signature device: it gives a
  batch containing similar-looking text a visible learning purpose without
  introducing decorative UI.
- **Accessibility and motion:** all controls retain visible keyboard focus;
  per-item status must be understandable without colour; loading state is
  textual and respects reduced-motion preferences.

The first design pass deliberately does **not** introduce a generic dashboard,
large hero, or a separate visual theme per card type: those would make a small,
task-focused tool harder to scan and would diverge from the established Word
flow. The distinction is carried by the learner's chosen card type, its input
copy, and the result marker instead.

### Phase 1 — Phrase and idiom collection audit and contract lock

The repository already models phrases and idioms together in `PhraseCollection`
and `PhraseModel`; retain that single collection unless a later requirement
needs materially different card behaviour for idioms.

1. Compare phrase collection behaviour against the Word collection contract:
   Anki note-type upsert, deck creation, update identity, media naming,
   language/ruby conversion, tags, prompt loading, and error propagation.
2. Confirm the learning-card contract for expressions: recognition and recall
   templates, core/supporting meanings, examples and audio, usage pattern,
   production hint, confusions, and memory associations. Make only targeted
   model/template/prompt changes where the audit finds a learner-facing gap.
3. Add or amend focused tests for every changed contract, including English and
   Japanese rendering where applicable. Keep the public CLI `phrase add` and
   `phrase batch` behaviour compatible.

**Done when:** `PhraseCollection.generate_and_add_note()` is ready to be used
by the GUI with the same lifecycle guarantees as words, and all focused phrase
tests pass.

### Phase 2 — Shared GUI batch-generation foundation

Before adding a second copy of `word_page`, extract only the page-level pieces
that are truly shared:

1. A typed page/workflow configuration for labels, examples, collection
   construction, accepted input, and optional controls (such as Word's image
   switch).
2. Common input normalization: combine the single input and one-item-per-line
   batch input, trim blank lines, preserve source order, and reject an empty
   submission with a useful message.
3. Common bounded-concurrency runner: create one shared Anki collection context
   per submission, use the selected parallelism, preserve result order while
   reporting completion as tasks finish, and isolate failures to their item.
4. A reusable, accessible result row with pending, success, and failure states;
   the final summary reports succeeded and failed counts.
5. Keep Word behaviour unchanged while migrating it onto the shared foundation;
   add unit tests around normalization and runner-result mapping so future card
   types do not fork this logic again.

**Done when:** Word generation has unchanged user-visible behaviour and its
batch workflow is reusable without knowing Word-specific details.

### Phase 3 — Phrase & Idiom GUI

1. Add a `/phrases` page and navigation entry, labelled **Phrase & Idiom Cards**.
2. Use an expression-specific single input and one-expression-per-line batch
   input. Examples should make clear that multi-word expressions are valid,
   such as `look forward to` and `once in a blue moon`.
3. Reuse the shared language selectors, provider/settings loading, parallelism
   control, cancellation-safe loading state, and per-item status rows.
4. Construct `PhraseCollection` with the current native/target languages and
   configured text model/service. Do not show Word's image-generation control:
   the existing phrase card contract generates text and audio only.
5. Verify with mocked UI/workflow tests plus a manual smoke test against a
   running AnkiConnect instance when credentials are available.

**Done when:** a learner can submit one or many phrases/idioms from the GUI,
receive independent per-item outcomes, and find generated notes in
`AINote::Phrases`.

### Phase 4 — Sentence GUI

Sentence cards use the same batch workflow, but their input contract differs:
the learner enters sentences in the **target language** and the model creates
the native-language prompt and learning notes for a production card.

1. Add `/sentences` and the corresponding navigation entry.
2. Use precise copy: “Target-language sentence” and “One target-language
   sentence per line”, with an example matching the selected/default language.
3. Build `SentenceCollection` through the same configured service path and
   reuse the shared status and batch-runner components unchanged.
4. Add coverage for sentence-specific validation and ensure the GUI consistently
   presents the input as target-language text.

**Done when:** one or many target-language sentences generate independently and
appear as production cards in `AINote::Sentences`.

### Phase 5 — Final integration and documentation

1. Run focused collection and UI tests, then the full test suite, formatting,
   linting, and static checks.
2. Update README screenshots/instructions and the GUI navigation description;
   document that expression and sentence workflows require the same AnkiConnect
   and provider configuration as Word cards.
3. Perform a manual three-lane smoke test (one Word, one Phrase/Idiom, one
   Sentence) with AnkiConnect, checking deck creation, note updates, audio,
   batch partial failure, and language direction.
4. Inspect the final diff to ensure no provider key, Anki collection data, or
   unrelated worktree change is included.

### Delivery order and dependencies

```
Phrase contract audit
        │
        ▼
Shared GUI batch foundation ──► Word regression coverage
        │
        ├────────► Phrase & Idiom GUI
        │
        └────────► Sentence GUI
                    │
                    ▼
           End-to-end verification + documentation
```

Phrase and Sentence GUI work can be implemented in close succession after the
shared foundation, but should not each copy the current Word page. A separate
“idiom collection” is intentionally not planned: phrases and idioms share the
same current generation and card contract, and a separate type would add Anki
migration and UI complexity without a stated learning benefit.

## 1. CLI reference (completed)

A reference file (`skills/ankinote-cli/SKILL.md`) documents the full `ankinote` CLI surface.
Any agent or human working in this repo can use it to understand how to operate
cards directly.

## 2. CLI Review

### Duplicated batch logic
The `batch` command in `word`, `phrase`, `sentence`, and `stem` share the same
pattern (RPM limiting, concurrency control, file reading). Extract a shared
`batch` decorator or mixin.

### Dead code
`src/ankinote/cli/math.py` and `src/ankinote/collections/math/` are no longer
registered in the CLI but still in the tree. Decide whether to keep or remove.

## 3. PyPI Release

### Prerequisites
- Dependencies: litellm, google-cloud-texttospeech, httpx, pydantic, etc.
  Install experience needs to be smooth.
- API key docs: GEMINI_API_KEY, GOOGLE_TTS_KEY, ANKI_CONNECT_URL
- AnkiConnect is an external dependency — users need to install the Anki addon
  separately.
- CLI and docs should be in English if targeting international users.

### Considerations
- Project is already structured with pyproject.toml, CLI entrypoint, version
- Public release means maintaining backward compatibility
- Consider a `--dry-run` mode that generates cards without pushing to Anki
## 4. STEM card expansion

Goal: raise STEM card quality with structured schemas, one new high-value card
type (comparison), type-aware rendering, and progressive disclosure — all while
keeping the established visual language (paper cards, amber accent, serif
typography, badge system) untouched. Existing notes must keep rendering
correctly throughout.

### Design constraints

- Anki note-type fields stay all-string (`StemNoteType` unchanged). Structured
  AI output is rendered to HTML in `_build_note_data()` before storage, so no
  note-type migration is needed and old notes remain valid.
- New visual elements only extend the existing token set in
  `stem/card_templates/style.css` (`--badge-<type>-*`, `--accent*`, `--paper*`).
  No new fonts, layouts, or themes.
- All new prompts follow the current contract: JSON-only output, same-language
  rule, escaped LaTeX in JSON, English Title Case tags.

### Phase S1 — Structured schema foundation ✅ *(completed 2026-08-26)*

1. Extend `StemModel` with optional structured fields:
   - `latex: str | None` — the core formula expression (formula cards).
   - `variables: list[Variable] | None` with `symbol` + `description`
     (formula cards).
   - `steps: list[str] | None` (procedure cards).
2. Update `prompts/formula.md` and `prompts/procedure.md` to emit the new keys;
   keep every new key optional so old outputs still validate.
3. In `_build_note_data()`, render the structured fields into the stored
   `back_detail` HTML: a centered formula block, a symbol-definition table,
   and an ordered step list — styled via new CSS classes that reuse existing
   color variables.
4. Focused tests: model validation with/without new keys,
   `_build_note_data()` HTML rendering, and an end-to-end mocked generation.

**Done when:** existing notes render unchanged, new generations emit structured
fields, and all focused tests pass.

> 2026-08-26 Done. Landed: `Variable` model + optional `latex` / `variables` /
> `steps` on `StemModel`; `_build_note_data()` renders them into stored
> `back_detail` HTML (`.formula-block`, `.symbol-table`, `.step-list` CSS
> classes reusing existing tokens); `formula.md` / `procedure.md` emit the new
> keys; `_system.md` notes that type-specific prompts may extend the base
> schema. New `tests/collections/test_stem_collection.py` (6 cases). All 84
> tests pass, ruff clean; basedpyright error count unchanged at 45 (all
> pre-existing, see section 5). Note-type fields untouched — no migration.
> Unlocks S2/S3/S4/S6.

### Phase S2 — Comparison card type *(fresh session OK, after S1)*

The highest-value missing type: contrast pairs (L1 vs L2 regularization,
bias vs variance, TCP vs UDP).

1. Add `CardType.COMPARISON` plus structured fields:
   `items: list[CompareItem]` (`name`, `definition`) and
   `aspects: list[CompareAspect]` (`aspect`, `per_item: dict[name, str]`) so
   the back renders as a true aspect-by-aspect table.
2. Add `prompts/comparison.md`; include the new type in the generator's
   auto-detection instruction.
3. Render as a responsive table (stacks vertically on narrow screens); add a
   `--badge-comparison-*` token pair following the existing badge pattern.
4. Focused tests mirroring S1 coverage.

**Done when:** a "difference between X and Y" topic produces a comparison card
whose table renders consistently in light/dark mode.

### Phase S3 — Progressive disclosure and rendering polish *(fresh session OK,
after S1; independent of S2)*

1. Wrap the `Detail` section of `back.html` in `<details>/<summary>` so recall
   practice sees only the brief answer first; style the summary as a subtle
   disclosure row consistent with `.section-title`.
2. Verify `<details>` behaviour on Anki desktop and AnkiDroid before committing
   to it; fall back to always-visible detail on unsupported clients.
3. Add shared MathJax macro configuration for common notation.
4. Manual smoke test: one card per existing type, light/dark, desktop + mobile.

**Done when:** review flow shows brief-first with expandable detail on all
target clients and no visual regressions.

### Phase S4 — Worked-example card type *(fresh session OK, after S1;
independent of S2/S3)*

The only type that trains production instead of recognition.

1. Add `CardType.EXAMPLE`: `front` = problem statement, `back_brief` = final
   answer, `back_detail` = fully worked steps; reuse `steps` from S1.
2. Add `prompts/example.md` (problem difficulty matched to the topic, no
   trivial restatements) and register the type in auto-detection.
3. Badge token pair + template branch consistent with other types.
4. Focused tests.

**Done when:** a problem-style topic yields an example card with answer-first,
steps-expandable layout.

### Phase S5 — Misconception callout *(optional, small; fold into S2 or S3
session)*

Rather than a new card type, add an optional `common_mistakes: list[str]`
field rendered as a small warning-styled callout at the bottom of the detail
section, using `--error`/muted tones already defined. Update
`_system.md` guidance on when to populate it.

### Phase S6 — Remove legacy math collection *(fully independent; fresh
session OK anytime)*

Resolve the dead-code item already tracked in "CLI Review": delete
`src/ankinote/collections/math/` and `src/ankinote/cli/math.py` after grepping
for references (CLI registration, tests, docs), then tick off the TODO item.
STEM supersedes it.

### Delivery order and dependencies

```
S1 structured schema foundation          S6 legacy math cleanup
        │                                (independent, any time)
        ├────────► S2 comparison type
        ├────────► S3 disclosure polish
        └────────► S4 example type
                    │
                    └─► S5 misconception callout (optional)
```

After S1 merges, S2, S3, S4, and S6 are mutually independent and each sized for
a single focused session.

## 5. Pre-existing issues snapshot *(recorded 2026-08-26, before S2–S6)*

These issues existed before the STEM card expansion started. New sessions must
not mistake them for their own regressions, and must not silently fix or
discard them:

1. **45 basedpyright errors** (`make check`) spread over existing code,
   e.g. `src/ankinote/ui/pages/notetypes.py` (`notify` literal-type argument)
   and `src/ankinote/ui/pages/settings.py` (`ClickEventArguments` passed where
   `str` is expected). Verified identical before and after S1; none are in
   `src/ankinote/collections/stem/` or its tests. Fixing them is out of scope
   for S2–S6 unless explicitly requested; when touching an affected file,
   keep the error count from increasing.
2. **Uncommitted working-tree changes unrelated to the STEM expansion**, seen
   alongside the S1 diff in `git status`: `src/ankinote/ui/pages/settings.py`,
   `src/ankinote/ui/config.py`, `src/ankinote/services/ai.py`,
   `src/ankinote/services/tts.py`, `src/ankinote/collections/word/generator.py`,
   `examples/anki/notes_with_media.py`.
   Per `Agents.md`, do not discard unrelated working-tree changes; commit them
   separately from STEM work once their owner confirms intent.

