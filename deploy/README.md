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
cp .env.example .env      # set ANKINOTE_STORAGE_SECRET (+ AnkiWeb login for headless)
docker compose up -d      # http://localhost:8080
```

**AI provider keys are configured in the web UI**, not in `.env` — open the
Settings page after first launch and add your text/image provider profiles and the
Google TTS key. They persist in the `ankinote-config` volume.

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
  `ankinote-config` volume (`/config` in the container) — there is no need to put
  them in `.env`.
- `ANKINOTE_STORAGE_SECRET` signs the GUI session cookie — generate one with
  `openssl rand -hex 32`. Defaults to a shared built-in value if unset.
- `ANKINOTE_PUBLISH` sets the published address/port (default `127.0.0.1:8080`).
  Use `8080` to bind all interfaces, `127.0.0.1:9000` for a different port.
- `headless/` additionally needs `ANKIWEB_USER` / `ANKIWEB_PASS` for the bundled
  AnkiConnect server.

## Customizing beyond `.env`

For structural changes — an extra volume, another service, a different network —
drop a `compose.override.yaml` next to the stack's `compose.yaml`. Compose loads
and merges it automatically on `docker compose up`; it is gitignored.

```yaml
# deploy/standard/compose.override.yaml
services:
  ankinote:
    volumes:
      - ./media:/media
```

Note list merges *append* (e.g. a `ports:` entry in the override is added, not
replaced) — for the published port use `ANKINOTE_PUBLISH` instead.
- `ANKINOTE_IMAGE` overrides the image/tag (default
  `ghcr.io/ignity21/ankinote-ai:latest`).

## Building locally

Images install a released version straight from PyPI:

```bash
docker build --build-arg ANKINOTE_VERSION=0.3.1 -t ankinote-ai ../..
```

(run from either stack directory; the build context is the repo root). The
`standard/compose.yaml` has a commented `build:` block for `docker compose build`.
