# Plugin author guide

## What you need to ship

A provider plugin is a regular pip package that contains:

1. A Python module (or package) with the required interface.
2. A `manifest.json` file co-located with the module.
3. An entrypoint declaration in `pyproject.toml`.

## pyproject.toml template

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "my-ma-provider"
version = "0.1.0"
description = "Short description"
requires-python = ">=3.11"
dependencies = [
    "music-assistant-plugin-manager",
]

[project.entry-points."music_assistant.provider"]
my_provider_domain = "my_provider_module"

[tool.setuptools.packages.find]
include = ["my_provider_module*"]

[tool.setuptools.package-data]
my_provider_module = ["manifest.json"]
```

- `my_provider_domain`: the MA domain string. It must be unique across all installed providers. Use snake_case.
- `my_provider_module`: the importable module name (top-level package or module on `sys.path`).

## manifest.json fields

Place `manifest.json` inside the provider module directory (next to `__init__.py`).

| Field | Required | Description |
|---|---|---|
| `domain` | yes | Unique identifier matching the entrypoint name |
| `name` | yes | Human-readable display name |
| `type` | yes | Provider type: `"music"`, `"player"`, `"metadata"`, or `"plugin"` |
| `description` | yes | One-sentence description shown in the MA UI |
| `codeowners` | yes | List of GitHub handles, e.g. `["@you"]` |
| `requirements` | yes | List of pip requirements the provider needs (may be `[]`) |
| `documentation` | no | URL to documentation |
| `stage` | no | `"beta"` or `"stable"` (defaults to `"stable"` if absent) |
| `multi_instance` | no | `true` if multiple configured instances are allowed (default `false`) |
| `icon` | no | Path to an icon file inside the package |

Minimal example (from `examples/demo_provider/demo_ma_provider/manifest.json`):

```json
{
  "type": "music",
  "domain": "demo_community_provider",
  "name": "Demo Community Provider",
  "description": "Example provider installed via music-assistant-plugin-manager.",
  "codeowners": ["@community"],
  "requirements": [],
  "documentation": "https://github.com/TigreGotico/music-assistant-plugin-manager"
}
```

## Required module interface

MA calls three things from the provider module at startup:

### `SUPPORTED_FEATURES`

```python
from music_assistant_models.enums import ProviderFeature

SUPPORTED_FEATURES: set[ProviderFeature] = {
    ProviderFeature.SEARCH,
    ProviderFeature.BROWSE,
}
```

Declare only features your provider actually implements. Common values:

| Value | What it enables |
|---|---|
| `ProviderFeature.SEARCH` | Provider appears in global search |
| `ProviderFeature.BROWSE` | Provider exposes a browseable folder tree |
| `ProviderFeature.LIBRARY_TRACKS` | User library sync for tracks |
| `ProviderFeature.LIBRARY_ALBUMS` | User library sync for albums |
| `ProviderFeature.LIBRARY_ARTISTS` | User library sync for artists |
| `ProviderFeature.LIBRARY_PLAYLISTS` | User library sync for playlists |
| `ProviderFeature.LIBRARY_RADIOS` | User library sync for radio stations |
| `ProviderFeature.RECOMMENDATIONS` | Provider can surface recommendations |

### `async def setup(mass, manifest, config) -> ProviderInstanceType`

Instantiates the provider class and returns it.

```python
from music_assistant.models.music_provider import MusicProvider
from music_assistant_models.provider import ProviderManifest
from music_assistant_models.config_entries import ProviderConfig
from music_assistant.mass import MusicAssistant
from music_assistant.models import ProviderInstanceType

async def setup(
    mass: MusicAssistant,
    manifest: ProviderManifest,
    config: ProviderConfig,
) -> ProviderInstanceType:
    return MyProvider(mass, manifest, config, SUPPORTED_FEATURES)
```

### `async def get_config_entries(mass, instance_id, action, values) -> tuple[ConfigEntry, ...]`

Returns configuration fields shown in the MA UI when a user adds an instance of the provider. Return an empty tuple if no configuration is needed.

```python
from music_assistant_models.config_entries import ConfigEntry, ConfigValueType
from music_assistant.mass import MusicAssistant

async def get_config_entries(
    mass: MusicAssistant,
    instance_id: str | None = None,
    action: str | None = None,
    values: dict[str, ConfigValueType] | None = None,
) -> tuple[ConfigEntry, ...]:
    return ()
```

## Provider types and base classes

| `manifest.json` type | Base class to subclass | When to use |
|---|---|---|
| `"music"` | `music_assistant.models.music_provider.MusicProvider` | Streaming services, radio, local files |
| `"player"` | `music_assistant.models.player_provider.PlayerProvider` | Speaker / playback hardware |
| `"metadata"` | `music_assistant.models.metadata_provider.MetadataProvider` | Artwork, lyrics, biographies |
| `"plugin"` | `music_assistant.models.plugin.PluginProvider` | General-purpose automation |

For music providers, subclass `MusicProvider` and override only the methods that correspond to the features in `SUPPORTED_FEATURES`.

## Lifecycle hooks

Override these methods on your provider class as needed:

| Method | When it is called |
|---|---|
| `async handle_async_init(self)` | After the provider instance is created, before it is exposed to MA |
| `async loaded_in_mass(self)` | After the provider is fully registered with MA |
| `async unload(self)` | When MA shuts down or the provider is disabled |
| `async update_config(self, config)` | When the user changes provider configuration |

## Worked example: `radiosoma_provider`

Source: `examples/radiosoma_provider/radiosoma_ma_provider/__init__.py`

`SomaFMProvider` subclasses `MusicProvider` and declares `SUPPORTED_FEATURES = {ProviderFeature.SEARCH, ProviderFeature.BROWSE}`.

**Startup**: `handle_async_init` fetches `http://api.somafm.com/channels.xml` using `self.mass.http_session` (MA's shared aiohttp session), parses it with `xml.etree.ElementTree`, and populates `self._stations`. No third-party dependencies are needed.

**Browse**: `browse(path)` returns genre folders at the top level, then radio items filtered by genre when a folder is entered. Paths use the form `<domain>://<genre>`.

**Search**: `search(query, media_types, limit)` does a case-insensitive substring match on station title and genre. Results are cached for 24 hours via MA's `@use_cache(3600 * 24)` decorator.

**Streaming**: `get_stream_details(item_id, media_type)` fetches the station's PLS playlist, extracts the first `File1=` URL, and returns a `StreamDetails` with `stream_type=StreamType.HTTP`, `content_type=ContentType.MP3`, and `can_seek=False`.

**Manifest** (`examples/radiosoma_provider/radiosoma_ma_provider/manifest.json`):

```json
{
  "type": "music",
  "domain": "radiosoma",
  "name": "SomaFM",
  "description": "Curated, ad-free internet radio from SomaFM, 40+ eclectic channels.",
  "codeowners": ["@TigreGotico"],
  "stage": "beta",
  "requirements": [],
  "multi_instance": false
}
```

No `requirements` are declared. The provider uses only MA's built-in aiohttp session and the Python standard library.

---
[← Architecture](architecture.md) · [Home](index.md) · [Deployment →](deployment.md)
