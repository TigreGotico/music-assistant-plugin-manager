# music-assistant-plugin-manager

Ship a [Music Assistant](https://music-assistant.io) provider as a standalone pip package. No PR to the MA core repository is required.

MA requires all providers to live inside the server's `music_assistant/providers/` directory. This library patches MA's provider discovery at runtime so that any pip-installable package registered under the `music_assistant.provider` entrypoint group is automatically found and loaded.

## How it works

Two patches are applied before MA starts:

1. **Import hook** (`MassProviderFinder`): intercepts `music_assistant.providers.<domain>` imports and redirects them to the real plugin module.
2. **Manifest patch**: patches `MusicAssistant.__load_provider_manifests` to also inject `manifest.json` files from entrypoint-registered packages.

A **wrapper launcher** applies both patches. Users run `python -m music_assistant_plugin_manager` (or the `music-assistant-community` script) instead of the normal MA entry point. This needs no `.pth` files and no edits to MA source.

## Install

```bash
pip install music-assistant-plugin-manager
```

Requires Python >= 3.11 and a working Music Assistant installation.

## Quick start

```bash
# Install your community provider alongside this library
pip install my-ma-provider

# Start Music Assistant through the wrapper
python -m music_assistant_plugin_manager
# or equivalently:
music-assistant-community
```

## Docker

The recommended way to run community providers in a container is to extend the official MA server image.

**Dockerfile** (see `examples/Dockerfile` for a working copy):

```dockerfile
FROM ghcr.io/music-assistant/server:beta

COPY . /build/
RUN /app/venv/bin/uv pip install \
    /build/plugin-manager \
    /build/plugin-manager/examples/radiosoma_provider

ENTRYPOINT ["python", "-m", "music_assistant_plugin_manager"]
```

Note: the MA server image ships only `uv` inside the venv, not `pip`. Use `/app/venv/bin/uv pip install`.

**docker-compose.yml** (see `examples/docker-compose.yml`):

```yaml
services:
  music-assistant-server:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: music-assistant-server
    restart: always
    network_mode: host
    volumes:
      - ${DATA_BASE_DIR}/music-assistant:/data/
    environment:
      LOG_LEVEL: info
```

See [docs/deployment.md](docs/deployment.md) for a full compose snippet and local-run instructions.

## Writing a provider plugin

Declare the entrypoint in your `pyproject.toml`:

```toml
[project.entry-points."music_assistant.provider"]
my_provider_domain = "my_provider_module"
```

Your module must contain:

| Item | Type | Description |
|---|---|---|
| `manifest.json` | file | MA provider manifest (domain, name, type, …) |
| `setup` | `async def` | Instantiates and returns the provider |
| `get_config_entries` | `async def` | Returns a tuple of `ConfigEntry` objects |
| `SUPPORTED_FEATURES` | `set[ProviderFeature]` | Feature flags the provider advertises |

See [docs/plugin-authors.md](docs/plugin-authors.md) for the full guide, manifest field reference, and a worked example.

## Examples

| Example | What it shows |
|---|---|
| `examples/demo_provider/` | Minimal scaffold with no real functionality |
| `examples/radiosoma_provider/` | Full `MusicProvider` subclass: SomaFM internet radio via stdlib XML + aiohttp, `SEARCH` and `BROWSE` features |

## License

Apache 2.0
