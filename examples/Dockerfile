FROM ghcr.io/music-assistant/server:beta

# The MA image ships uv, not pip, and MA lives in /app/venv — a bare `pip install`
# would land in a different interpreter.
COPY . /build/
RUN /app/venv/bin/uv pip install --prerelease=allow \
    /build/music-assistant-plugin-manager \
    /build/music-assistant-plugin-manager/examples/radiosoma_provider

# The base image's entrypoint passes --data-dir/--cache-dir to `mass` and preloads
# jemalloc; overriding ENTRYPOINT drops both, so the wrapper has to carry them or
# MA writes its database inside the container and loses it on every restart.
RUN printf '%s\n' \
 '#!/bin/sh' \
 'for path in /usr/lib/*/libjemalloc.so.2; do' \
 '  [ -f "$path" ] && export LD_PRELOAD="$path" MALLOC_CONF="background_thread:true,dirty_decay_ms:5000,muzzy_decay_ms:5000" && break' \
 'done' \
 'exec /app/venv/bin/python -m music_assistant_plugin_manager "$@"' \
 > /usr/local/bin/community-entrypoint.sh && chmod +x /usr/local/bin/community-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/community-entrypoint.sh", "--data-dir", "/data", "--cache-dir", "/data/.cache"]
