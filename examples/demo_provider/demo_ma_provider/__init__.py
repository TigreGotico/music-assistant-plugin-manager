"""Demo community provider — minimal example for music-assistant-plugin-manager."""

from __future__ import annotations

from typing import TYPE_CHECKING

from music_assistant_models.enums import ProviderFeature

if TYPE_CHECKING:
    from music_assistant_models.config_entries import ConfigEntry, ConfigValueType, ProviderConfig
    from music_assistant_models.provider import ProviderManifest

    from music_assistant.mass import MusicAssistant
    from music_assistant.models import MusicProvider

SUPPORTED_FEATURES: set[ProviderFeature] = set()


async def setup(mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig) -> MusicProvider:
    """Instantiate the provider."""
    from music_assistant.models.music_provider import MusicProvider as _Base
    prov = _Base(mass, manifest, config, supported_features=SUPPORTED_FEATURES)
    return prov


async def get_config_entries(
    mass: MusicAssistant,
    instance_id: str | None = None,
    action: str | None = None,
    values: dict[str, ConfigValueType] | None = None,
) -> tuple[ConfigEntry, ...]:
    """Return config entries (none needed for this demo)."""
    return ()
