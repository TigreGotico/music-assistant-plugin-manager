"""SomaFM provider for Music Assistant — zero extra dependencies."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from music_assistant_models.enums import (
    ContentType,
    ImageType,
    MediaType,
    ProviderFeature,
    StreamType,
)
from music_assistant_models.errors import MediaNotFoundError, ProviderUnavailableError
from music_assistant_models.media_items import (
    AudioFormat,
    BrowseFolder,
    MediaItemImage,
    MediaItemType,
    ProviderMapping,
    Radio,
    SearchResults,
    UniqueList,
)
from music_assistant_models.streamdetails import StreamDetails

from music_assistant.controllers.cache import use_cache
from music_assistant.models.music_provider import MusicProvider

if TYPE_CHECKING:
    from music_assistant_models.config_entries import ConfigEntry, ConfigValueType, ProviderConfig
    from music_assistant_models.provider import ProviderManifest

    from music_assistant.mass import MusicAssistant
    from music_assistant.models import ProviderInstanceType

SUPPORTED_FEATURES = {
    ProviderFeature.SEARCH,
    ProviderFeature.BROWSE,
}

_CHANNELS_URL = "http://api.somafm.com/channels.xml"


@dataclass
class _Station:
    station_id: str
    title: str
    description: str
    genre: str
    image: str          # xlimage preferred
    mp3_pls: str        # fastpls format="mp3"


def _parse_channels(xml_bytes: bytes) -> list[_Station]:
    root = ET.fromstring(xml_bytes)
    stations: list[_Station] = []
    for ch in root.findall("channel"):
        mp3_pls = ""
        for pls in ch.findall("fastpls"):
            if pls.attrib.get("format") == "mp3":
                mp3_pls = pls.text or ""
                break

        image = (
            _text(ch, "xlimage")
            or _text(ch, "largeimage")
            or _text(ch, "image")
            or ""
        )
        stations.append(
            _Station(
                station_id=ch.attrib["id"],
                title=_text(ch, "title") or ch.attrib["id"],
                description=_text(ch, "description") or "",
                genre=_text(ch, "genre") or "",
                image=image,
                mp3_pls=mp3_pls,
            )
        )
    return stations


def _text(el: ET.Element, tag: str) -> str:
    child = el.find(tag)
    return (child.text or "").strip() if child is not None else ""


async def _resolve_pls(session, pls_url: str) -> str:
    """Fetch a PLS playlist and return the first File= stream URL."""
    async with session.get(pls_url) as resp:
        resp.raise_for_status()
        text = await resp.text(encoding="latin-1")
    for line in text.splitlines():
        if line.lower().startswith("file1="):
            return line.split("=", 1)[1].strip()
    raise MediaNotFoundError(f"No stream URL found in PLS: {pls_url}")


async def setup(
    mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig
) -> ProviderInstanceType:
    """Initialize provider(instance) with given configuration."""
    return SomaFMProvider(mass, manifest, config, SUPPORTED_FEATURES)


async def get_config_entries(
    mass: MusicAssistant,  # noqa: ARG001
    instance_id: str | None = None,  # noqa: ARG001
    action: str | None = None,  # noqa: ARG001
    values: dict[str, ConfigValueType] | None = None,  # noqa: ARG001
) -> tuple[ConfigEntry, ...]:
    """Return Config entries to setup this provider."""
    return ()


class SomaFMProvider(MusicProvider):
    """Music Assistant provider for SomaFM."""

    _stations: dict[str, _Station]

    @property
    def is_streaming_provider(self) -> bool:
        return True

    async def handle_async_init(self) -> None:
        """Fetch station list at startup."""
        await self._load_stations()

    async def _load_stations(self) -> None:
        try:
            async with self.mass.http_session.get(_CHANNELS_URL) as resp:
                resp.raise_for_status()
                data = await resp.read()
        except Exception as err:
            raise ProviderUnavailableError(f"Failed to fetch SomaFM channels: {err}") from err

        self._stations = {s.station_id: s for s in _parse_channels(data)}
        self.logger.debug("Loaded %d SomaFM stations", len(self._stations))

    def _get(self, station_id: str) -> _Station:
        st = self._stations.get(station_id)
        if st is None:
            raise MediaNotFoundError(f"SomaFM station '{station_id}' not found")
        return st

    def _to_radio(self, st: _Station) -> Radio:
        radio = Radio(
            item_id=st.station_id,
            provider=self.domain,
            name=st.title,
            provider_mappings={
                ProviderMapping(
                    item_id=st.station_id,
                    provider_domain=self.domain,
                    provider_instance=self.instance_id,
                )
            },
        )
        if st.description:
            radio.metadata.description = st.description
        if st.genre:
            radio.metadata.genres = set(st.genre.split("|"))
        if st.image:
            radio.metadata.images = UniqueList(
                [
                    MediaItemImage(
                        type=ImageType.THUMB,
                        path=st.image,
                        provider=self.instance_id,
                        remotely_accessible=True,
                    )
                ]
            )
        return radio

    @use_cache(3600 * 24)
    async def search(
        self, search_query: str, media_types: list[MediaType], limit: int = 10
    ) -> SearchResults:
        result = SearchResults()
        if MediaType.RADIO not in media_types:
            return result
        q = search_query.casefold()
        result.radio = [
            self._to_radio(s)
            for s in self._stations.values()
            if q in s.title.casefold() or q in s.genre.casefold()
        ][:limit]
        return result

    async def browse(self, path: str) -> Sequence[MediaItemType | BrowseFolder]:
        parts = [p for p in path.split("://")[1].split("/") if p] if "://" in path else []

        if not parts:
            genres: set[str] = set()
            for s in self._stations.values():
                for g in s.genre.split("|"):
                    if g:
                        genres.add(g)
            return [
                BrowseFolder(
                    item_id=g,
                    provider=self.domain,
                    path=f"{path}/{g}",
                    name=g.capitalize(),
                )
                for g in sorted(genres)
            ]

        genre_filter = parts[0]
        return [
            self._to_radio(s)
            for s in self._stations.values()
            if genre_filter in s.genre.split("|")
        ]

    async def get_radio(self, prov_radio_id: str) -> Radio:
        return self._to_radio(self._get(prov_radio_id))

    async def get_stream_details(self, item_id: str, media_type: MediaType) -> StreamDetails:
        st = self._get(item_id)
        if not st.mp3_pls:
            raise MediaNotFoundError(f"SomaFM station '{item_id}' has no MP3 stream")
        stream_url = await _resolve_pls(self.mass.http_session, st.mp3_pls)
        return StreamDetails(
            provider=self.domain,
            item_id=item_id,
            audio_format=AudioFormat(
                content_type=ContentType.MP3,
                bit_rate=128,
            ),
            media_type=MediaType.RADIO,
            stream_type=StreamType.HTTP,
            path=stream_url,
            can_seek=False,
            allow_seek=False,
        )
