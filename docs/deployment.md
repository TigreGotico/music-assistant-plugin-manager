# Deployment

## Running locally (without Docker)

```bash
pip install music-assistant-plugin-manager my-ma-provider
python -m music_assistant_plugin_manager
```

Or use the console script installed by the package:

```bash
music-assistant-community
```

Both are equivalent. MA's normal configuration and data directory conventions apply.

### Environment variables

MA itself reads these at startup:

| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `warning` | Python log level: `debug`, `info`, `warning`, `error` |

`music-assistant-plugin-manager` uses MA's standard logging infrastructure and logs under the `music_assistant_plugin_manager` logger name.

## Docker

### Image layout

The official MA server image is `ghcr.io/music-assistant/server:beta`. It ships a Python venv at `/app/venv` that contains only `uv` as a package manager — there is no `pip` binary. Install additional packages with:

```bash
/app/venv/bin/uv pip install <package>
```

### Dockerfile

The example at `examples/Dockerfile` installs packages from a local source tree:

```dockerfile
FROM ghcr.io/music-assistant/server:beta

COPY . /build/
RUN /app/venv/bin/uv pip install \
    /build/plugin-manager \
    /build/plugin-manager/examples/radiosoma_provider

ENTRYPOINT ["python", "-m", "music_assistant_plugin_manager"]
```

Key points:

- `COPY . /build/` places the repo root (which contains the `plugin-manager/` subdirectory) into the image.
- The `RUN` layer installs the manager library and the example provider in a single `uv pip install` call.
- `ENTRYPOINT` overrides MA's default entry point. `CMD` from the base image is preserved and passed through.

To install published packages instead of local source, replace the paths with package names:

```dockerfile
RUN /app/venv/bin/uv pip install \
    music-assistant-plugin-manager \
    my-ma-provider==1.2.3
```

### docker-compose

Full working snippet matching the example at `examples/docker-compose.yml`:

```yaml
services:
  music-assistant-server:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: music-assistant-server
    restart: always
    user: ${MAIN_GID}:${MAIN_UID}
    network_mode: host
    ports:
      - 5353:5353
      - 44148:44148
      - 8927:8927
      - 8095:8095
      - 8097:8097
    volumes:
      - ${DATA_BASE_DIR}/music-assistant:/data/
    cap_add:
      - SYS_ADMIN
      - DAC_READ_SEARCH
    security_opt:
      - apparmor:unconfined
    environment:
      LOG_LEVEL: info
    deploy:
      resources:
        limits:
          cpus: "0.50"
          memory: 5G
```

`MAIN_GID` and `MAIN_UID` should be set in a `.env` file or exported in the shell before running `docker compose up`.

`DATA_BASE_DIR` is the host path under which MA will store its database and configuration.

`network_mode: host` is required for mDNS discovery (port 5353). The explicit `ports:` list is informational when `network_mode: host` is active but useful as documentation of which ports MA uses.

---
[← Plugin author guide](plugin-authors.md) · [Home](index.md)
