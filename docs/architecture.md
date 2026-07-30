# Architecture

## Problem

Music Assistant discovers providers by scanning `music_assistant/providers/` at startup. There is no supported extension point for packages installed outside that directory tree. A community author must either submit a PR to the MA repository or manually copy files into the installed server image.

## Solution overview

`music-assistant-plugin-manager` installs two runtime patches before MA's own startup code runs, then delegates to MA's normal `main()`. Nothing in MA's source is modified on disk.

```
python -m music_assistant_plugin_manager
        |
        v
  bootstrap.install()
    |-- MassProviderFinder  --> sys.meta_path[0]
    |-- _apply_manifest_patch --> patches MusicAssistant.__load_provider_manifests
        |
        v
  music_assistant.__main__.main()   (normal MA startup)
```

## Wrapper launcher

`music_assistant_plugin_manager/__main__.py:8`: `main()`

Calls `bootstrap.install()` first, then imports and calls `music_assistant.__main__.main`. This ordering guarantees the patches are in place before any MA module that touches provider discovery is imported. The console script `music-assistant-community` (declared in `pyproject.toml`) invokes this same `main()`.

## Import hook: `MassProviderFinder`

`music_assistant_plugin_manager/finder.py:14`: `MassProviderFinder`

Registered as `sys.meta_path[0]` so it runs before all other finders. Its `find_spec()` method intercepts any import whose fully-qualified name starts with `music_assistant.providers.`. It extracts the domain portion and looks it up in the entrypoint map (`{domain: module_name}`).

If the domain is known, `find_spec` locates the real spec through `importlib.util.find_spec(real_module_name)` and returns a new `ModuleSpec` pointing at `_AliasLoader`. `_AliasLoader.exec_module` loads the real module (or reuses it from `sys.modules`) and copies all its attributes into the alias module object. It then also registers the real module under its own name in `sys.modules`.

Sub-module imports (`music_assistant.providers.<domain>.<submodule>`) are handled by splitting on the first `.` and prepending the real parent module name.

## Manifest patch

`music_assistant_plugin_manager/bootstrap.py:44`: `_apply_manifest_patch()`

MA's `MusicAssistant` class has a private async method `__load_provider_manifests` (name-mangled to `_MusicAssistant__load_provider_manifests`). The patch replaces this method with a wrapper that:

1. Calls the original method so all built-in providers are loaded first.
2. Iterates `ep_map` and, for each domain not already present in `self._provider_manifests`, calls `load_manifest_json(module_name)` and constructs a `ProviderManifest` via `ProviderManifest.from_json`.
3. Logs and skips any provider whose `manifest.json` cannot be loaded. It does not abort startup.

The replacement method is marked with `._mapm_patched = True` so repeated calls to `_apply_manifest_patch` are idempotent.

Built-in providers always win: community providers whose domain collides with a built-in are silently skipped (step 2's `if domain in self._provider_manifests: continue`).

## Entrypoint scanning

`music_assistant_plugin_manager/entrypoints.py:10`: `scan_entrypoints()`

Calls `importlib.metadata.entry_points(group="music_assistant.provider")`. Each entry point's `.name` is the provider domain and `.value` is the fully-qualified module name. Returns `{domain: module_name}`.

## Manifest loading

`music_assistant_plugin_manager/manifest.py:11`: `load_manifest_json(module_name)`

Imports the module, then reads `manifest.json` via `importlib.resources.files(mod) / "manifest.json"`. Falls back to `Path(mod.__file__).parent / "manifest.json"` if the resources API raises.

## Public convenience API

`music_assistant_plugin_manager/__init__.py`

| Function | What it does |
|---|---|
| `find_providers() -> dict[str, str]` | Returns `{domain: module_name}` for all installed plugins |
| `load_provider(domain) -> module or None` | Imports and returns the provider module for a domain |

These are thin wrappers over `scan_entrypoints()` and `importlib.import_module`. They are not used by the bootstrap path itself.

## Why not a `.pth` file?

A `.pth` file with executable code runs during site-package initialization, very early in the Python startup sequence, before the user's process code. This makes it impossible to guarantee ordering relative to other site-packages hooks. It also creates import side effects that are hard to debug. The wrapper launcher approach keeps the patch explicit, traceable, and testable.

---
[Home](index.md) · [Plugin author guide →](plugin-authors.md)
