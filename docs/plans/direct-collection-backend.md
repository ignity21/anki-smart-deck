# Direct Collection Backend and AnkiWeb Sync

## Goal and Confirmed Behavior

Add an in-process backend that uses Anki's official Python library to operate on
an Anki collection directly. Keep the existing `AnkiConnectClient` backend.
The first release covers card creation, note type maintenance, media storage, and
complete AnkiWeb synchronization.

| Topic | Confirmed choice |
| --- | --- |
| Default backend | Standard installations continue to use AnkiConnect; headless Docker uses the direct backend. |
| Sync triggers | At startup, after each write batch, every five minutes, and manually. |
| Sync data | Both collection and media, including images and audio. |
| Full sync | Pause and require the user to choose upload or download; block writes until resolved. |
| Temporary offline state | After initial setup, permit local writes and synchronize after recovery. |
| Account model | One account and one collection per ankinote instance; support UI login and environment variables. |
| Concurrent processes | Do not support GUI and CLI processes opening the same collection simultaneously in the first release. |
| Migration | Support reusing the existing data directory and initializing a fresh directory from AnkiWeb. |

## Backend Interface and Lifecycle

- Keep `AnkiCollectionClient` as the collection-facing contract, with its model,
  deck, note, and media services. Add `DirectCollectionClient`; retain
  `AnkiConnectClient` as the remote/Desktop-Anki implementation.
- Add one backend factory and replace all direct `AnkiConnectClient` construction
  in the UI and CLI. Select it with `ANKI_BACKEND=connect|collection`; the default
  remains `connect`. `ANKI_COLLECTION_PATH` is required for `collection`.
- Create the direct backend once for the web application and close it during app
  shutdown. CLI commands create it for their command context and close it on
  completion. Individual pages and generation tasks borrow the shared runtime.
- Run every Anki `Collection` call in one dedicated worker thread. The asyncio
  layer submits typed work to that thread; raw Anki objects never cross the
  thread boundary.
- Serialize collection reads/writes and synchronization through this runtime.
  A note save is atomic from the application's perspective: deduplication,
  media storage, field update, and tag update complete before a sync can begin.
  AI generation does not hold the collection worker.
- Detect collection locking and report that the collection is in use when another
  process, including Anki Desktop or another ankinote CLI/GUI process, owns it.

## Local Collection Operations

- Implement the current application contract with Anki's supported collection
  APIs: note type lookup and creation, field addition, template addition and
  renaming, named template updates, CSS updates, deck lookup/creation, note
  lookup/add/update, tag replacement, and media storage.
- After creating or modifying a note type, reload it so ankinote receives
  Anki-assigned IDs, field order, and template data. Use normal model updates so
  schema changes participate in AnkiWeb synchronization.
- Preserve existing notes, cards, review history, and any user-owned extra
  fields or templates. Do not rebuild a note type to update it.
- Keep existing deduplication behavior: multiple matching notes are an error,
  not an arbitrary selection. Note type synchronization is idempotent.
- Return the actual stored media filename and use it to render sound/image
  references, accommodating Anki filename normalization or collision handling.

## AnkiWeb Sync and Account State

- Add a synchronization service with durable state: `not_logged_in`,
  `initializing`, `idle`, `syncing`, `pending`, `needs_full_sync_choice`, and
  `error`. Track collection and media outcomes plus the most recent successful
  synchronization time.
- Use Anki's own login, normal sync, full upload/download, and media sync APIs;
  do not implement the AnkiWeb protocol. Wait for media synchronization to
  finish and surface its errors before reporting success.
- Synchronize at runtime start, after each successful write batch, and on a
  five-minute interval. Coalesce duplicate requests. CLI commands wait for their
  batch's sync result before completing.
- On network errors, retain the local collection and retry with backoff. On
  credential failure, stop automatic login retries and require reauthentication.
  Retrying a sync never repeats AI generation or an already-completed local
  write.
- Initial setup must resolve synchronization before card writes. If Anki requires
  a full sync, do not automatically choose a destructive direction.
- Before a user-selected full upload or download, wait for queued writes and
  make a recoverable collection backup. Abort if the backup cannot be made.
  Reopen and invalidate cached collection objects after a sync that replaces the
  local collection.
- While a full-sync decision is pending, permit read-only status views but reject
  new writes and note type changes. This differs from a temporary network outage,
  where local writes are allowed.
- Persist the Anki sync credential after successful UI login in a separate
  restricted-permission file. Never expose it to the browser or logs. Environment
  configuration takes precedence and UI shows that the credentials are externally
  configured.
- Logout removes the saved sync credential and pauses automatic synchronization;
  it does not delete the local collection. Do not silently associate an existing
  collection directory with a different AnkiWeb account.

## UI, CLI, Deployment, and Migration

- Add Anki backend and sync controls to Settings: account login/logout, current
  sync status, last result, manual sync, and the five-minute interval setting.
  Present upload/download choices when a full sync is required.
- Report local-write success separately from AnkiWeb-sync success. A media sync
  failure must not make a completed card write look unsuccessful.
- Distinguish note type synchronization from AnkiWeb synchronization in English
  and Simplified Chinese UI text.
- Add `ankinote anki login`, `logout`, `status`, and `sync` commands.
  `sync --direction upload|download` resolves a required full sync in
  non-interactive deployments; unresolved conflicts return a nonzero status.
- Ship the direct backend as an `ankinote-ai[headless]` extra and initially pin
  `anki==26.8.1`. Preserve the standard image's AnkiConnect behavior; make the
  headless image install the extra.
- Simplify `deploy/headless/compose.yaml` to one ankinote service with the
  collection data volume. Keep `deploy/standard/compose.yaml` unchanged.
- Document migration: stop the old headless service, back up the complete data
  directory, preserve collection plus media data, verify ownership, then start
  the direct backend. A fresh directory initializes from AnkiWeb. Do not
  automatically remove old data.
- Do not publish a release, deploy containers, or migrate a real AnkiWeb account
  as part of this work.

## Implementation Order

1. Add backend selection, the collection worker runtime, and lifecycle ownership;
   prove the existing AnkiConnect path remains unchanged.
2. Implement and test direct model, deck, note, tag, and media operations using
   a temporary real collection.
3. Implement the synchronization service, credential persistence, full-sync
   decision flow, backups, and recovery behavior.
4. Connect all UI pages and CLI commands; ensure concurrent generation and
   synchronization are serialized without duplicate cards.
5. Update Docker images, Compose stacks, configuration docs, and migration docs.

## Test and Acceptance Plan

- Test Word, Phrase, Sentence, and STEM collection flows through the direct
  backend: first creation, repeated setup, missing fields, multiple templates,
  existing notes, tags, audio, images, and preserved review history.
- Test normal sync, full upload, full download, authentication failure, offline
  retry, media failure, backup failure, cancellation, restart, and unresolved
  full-sync write blocking.
- Test collection lock detection and the explicit unsupported GUI-plus-CLI
  concurrent-process case.
- Verify reusing a prior data directory and initializing a new directory from
  AnkiWeb. Automated tests use no personal AnkiWeb account; provide a manual
  two-device acceptance procedure for cards, audio, images, and remote edits.
- Run `uv run pytest`, `uv run ruff check`, and `uv run basedpyright`; identify
  any pre-existing failures separately from feature regressions.
