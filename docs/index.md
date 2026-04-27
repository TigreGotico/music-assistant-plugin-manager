# music-assistant-plugin-manager

Entrypoint-based provider discovery for [Music Assistant](https://music-assistant.io) — install providers as plain pip packages.

## Overview

Music Assistant requires all providers to live inside `music_assistant/providers/`. This library patches MA's discovery at process start so that any package registered under the `music_assistant.provider` entrypoint group is found and loaded without modifying MA source or rebuilding its Docker image.

## Key modules

| Module | Key symbol | Purpose | Source |
|---|---|---|---|
| `bootstrap` | `install()` | Applies both patches; idempotent | `music_assistant_plugin_manager/bootstrap.py:21` |
| `finder` | `MassProviderFinder` | `importlib` meta-path hook | `music_assistant_plugin_manager/finder.py:14` |
| `entrypoints` | `scan_entrypoints()` | Reads `music_assistant.provider` entrypoint group | `music_assistant_plugin_manager/entrypoints.py:10` |
| `manifest` | `load_manifest_json()` | Loads `manifest.json` from a plugin package | `music_assistant_plugin_manager/manifest.py:11` |
| `__init__` | `find_providers()`, `load_provider()` | Public convenience API | `music_assistant_plugin_manager/__init__.py:9` |
| `__main__` | `main()` | Wrapper launcher entry point | `music_assistant_plugin_manager/__main__.py:8` |

## Contents

- [Installation and deployment](../README.md#install)
- [Architecture](architecture.md)
- [Plugin author guide](plugin-authors.md)
- [Deployment](deployment.md)
