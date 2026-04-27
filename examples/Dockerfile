FROM ghcr.io/music-assistant/server:beta

# Install mapm and community provider packages from local source
COPY . /build/
RUN pip install --no-cache-dir \
    /build/plugin-manager \
    /build/plugin-manager/examples/radiosoma_provider

ENTRYPOINT ["python", "-m", "music_assistant_plugin_manager"]
