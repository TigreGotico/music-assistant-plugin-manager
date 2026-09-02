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

The example at `examples/Dockerfile` installs the manager from PyPI and optionally includes plugins from a local source tree:

```dockerfile
FROM ghcr.io/music-assistant/server:beta

RUN /app/venv/bin/uv pip install --prerelease=allow music-assistant-plugin-manager

# For developing plugins, copy them into the image and install from the local checkout.
COPY ./examples/radiosoma_provider /build/radiosoma_provider
RUN /app/venv/bin/uv pip install --prerelease=allow /build/radiosoma_provider

RUN printf '%s\n' \
 '#!/bin/sh' \
 'for path in /usr/lib/*/libjemalloc.so.2; do' \
 '  [ -f "$path" ] && export LD_PRELOAD="$path" MALLOC_CONF="background_thread:true,dirty_decay_ms:5000,muzzy_decay_ms:5000" && break' \
 'done' \
 'exec /app/venv/bin/python -m music_assistant_plugin_manager "$@"' \
 > /usr/local/bin/community-entrypoint.sh && chmod +x /usr/local/bin/community-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/community-entrypoint.sh", "--data-dir", "/data", "--cache-dir", "/data/.cache"]
```

The entrypoint script is written by the `RUN` layer: overriding the base image's `ENTRYPOINT` drops the `--data-dir`/`--cache-dir` arguments it passed to `mass`, and without them MA stores its database inside the container and loses every setting on restart.

Key points:

- The manager library and published plugins are installed from PyPI.
- For plugins under development, use `COPY` to include a local checkout and install it with `uv pip install /path`.
- The base image has no `CMD`; its `ENTRYPOINT` is `entrypoint.sh --data-dir /data --cache-dir /data/.cache`. Overriding `ENTRYPOINT` therefore replaces those arguments rather than adding to them, so the replacement must pass them itself.

#### Installing published plugins

To install published plugins from PyPI, add them to the `RUN` command:

```dockerfile
RUN /app/venv/bin/uv pip install --prerelease=allow \
    music-assistant-plugin-manager \
    my-ma-provider==1.2.3 \
    another-provider
```

#### Installing unpublished plugins

The MA server base image ships no `git`, so `pip install git+https://...` fails inside the container. Install unpublished plugins by copying the local checkout:

```dockerfile
COPY ./my-plugin /build/my-plugin
RUN /app/venv/bin/uv pip install --prerelease=allow /build/my-plugin
```

### docker-compose

Working snippet (the example at `examples/docker-compose.yml` additionally mounts a host music directory):

```yaml
services:
  music-assistant-server:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: music-assistant-server
    restart: always
    user: ${MAIN_UID}:${MAIN_GID}
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

`MAIN_UID` and `MAIN_GID` should be set in a `.env` file or exported in the shell before running `docker compose up`.

`DATA_BASE_DIR` is the host path under which MA will store its database and configuration.

`network_mode: host` is required for mDNS discovery (port 5353). The explicit `ports:` list is informational when `network_mode: host` is active but useful as documentation of which ports MA uses.

---
[← Plugin author guide](plugin-authors.md) · [Home](index.md)
