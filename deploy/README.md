# Deploying the ankinote web GUI

Published images (multi-arch `amd64` + `arm64`), tags `latest`, `<major>.<minor>`,
`<version>`:

- `ghcr.io/ignity21/ankinote-ai`
- `ignity21/ankinote-ai` (Docker Hub)

Two ready-made stacks:

| Directory | Use it when |
| --- | --- |
| [`standard/`](standard/) | You already run AnkiConnect — the Anki desktop app on the host, or one elsewhere. |
| [`headless/`](headless/) | You want a self-contained stack with a headless AnkiConnect that syncs with AnkiWeb; no Anki desktop app. |

Each directory is standalone:

```bash
cd deploy/standard        # or deploy/headless
cp .env.example .env      # then fill it in
docker compose up -d      # http://localhost:8080
```

## `standard/`

The container reaches your AnkiConnect via `ANKI_CONNECT_URL` (default
`http://host.docker.internal:8765`, i.e. the host). In the AnkiConnect add-on
config (Tools -> Add-ons -> AnkiConnect -> Config) set `"webBindAddress": "0.0.0.0"`
and add the container origin to `"webCorsOriginList"` (or use `"*"`), then restart
Anki.

## `headless/`

Runs `glechic/anki-connect-server` alongside the GUI on the compose network, so
`ANKI_CONNECT_URL` is fixed to `http://anki-connect-server:8765` and nothing is
published for it. Set `ANKIWEB_USER` / `ANKIWEB_PASS` in `.env` — the server syncs
the collection from AnkiWeb and keeps it in the `anki-data` volume. To use an
existing collection file instead, see the commented bind mount in
`headless/compose.yaml`.

## Config & secrets

- Provider profiles and API keys entered on the Settings page persist in the
  `ankinote-config` volume (`/config` in the container).
- `ANKINOTE_STORAGE_SECRET` signs the GUI session cookie — generate one with
  `openssl rand -hex 32`. Defaults to a shared built-in value if unset.
- `ANKINOTE_IMAGE` overrides the image/tag (default
  `ghcr.io/ignity21/ankinote-ai:latest`).

## Building locally

Images install a released version straight from PyPI:

```bash
docker build --build-arg ANKINOTE_VERSION=0.3.1 -t ankinote-ai ../..
```

(run from either stack directory; the build context is the repo root). The
`standard/compose.yaml` has a commented `build:` block for `docker compose build`.
