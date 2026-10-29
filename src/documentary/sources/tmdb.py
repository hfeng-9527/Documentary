"""TMDB：按品牌发现纪录片系列、取系列详情和季（source-mapping.md 第 2 节）。

只管把数据拿回来、转成下面的结构，并把原始返回存进 raw.db；收不收录由 pipeline 判断。
接口文档：https://developer.themoviedb.org/reference
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import httpx

from documentary.core.config import Settings
from documentary.core.http import HttpClient, SourceError
from documentary.core.raw import RawStore

BASE = "https://api.themoviedb.org/3"
GENRE_DOCUMENTARY = 99
MAX_PAGES = 500  # TMDB discover 最多翻 500 页
_ZH_REGIONS = ["CN", "SG", "TW", "HK"]  # 中文译名的优先顺序


class MissingKey(SourceError):
    fatal = True


@dataclass
class TmdbSeason:
    number: int
    name: str | None
    air_date: date | None
    episode_count: int | None
    tmdb_id: int | None


@dataclass
class TmdbEpisode:
    number: int
    name: str | None
    air_date: date | None
    runtime: int | None
    overview: str | None
    tmdb_id: int | None


@dataclass
class TmdbSeries:
    tmdb_id: int
    name_en: str | None
    name_zh: str | None
    original_name: str | None
    original_language: str | None
    first_air_date: date | None
    overview_en: str | None
    overview_zh: str | None
    networks: list[tuple[int, str]] = field(default_factory=list)
    companies: list[tuple[int, str]] = field(default_factory=list)
    genre_ids: list[int] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    imdb_id: str | None = None
    vote_average: float | None = None
    vote_count: int | None = None
    poster_path: str | None = None
    seasons: list[TmdbSeason] = field(default_factory=list)
    next_air_date: date | None = None


class Tmdb:
    def __init__(
        self,
        settings: Settings,
        raw: RawStore | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] | None = None,
    ):
        key = settings.tmdb_api_key
        if not key:
            raise MissingKey(
                ".env 里缺 TMDB_API_KEY：在项目文件夹的 .env 里加一行 TMDB_API_KEY=你的key"
            )
        # 32 位的是 API Key（放在参数里）；很长的一串是 Read Access Token（放在请求头里）
        self._params = {"api_key": key} if len(key) <= 40 else {}
        headers = {"Authorization": f"Bearer {key}"} if len(key) > 40 else {}
        extra = {"sleep": sleep} if sleep else {}
        self.http = HttpClient(
            settings, name="TMDB", abroad=True, headers=headers, transport=transport, **extra
        )
        self.raw = raw

    def close(self) -> None:
        self.http.close()

    @property
    def requests(self) -> int:
        return self.http.requests

    def _get(self, path: str, **params: Any) -> Any:
        return self.http.get_json(f"{BASE}{path}", {**self._params, **params})

    # ---------- 发现 ----------

    def discover_tv(
        self, *, since: date, networks: list[int] = (), companies: list[int] = ()
    ) -> Iterator[dict[str, Any]]:
        """纪录片类型的系列，首播日期从 since 起（含未来已公布的）。返回列表页的简要条目。"""
        params: dict[str, Any] = {
            "with_genres": GENRE_DOCUMENTARY,
            "first_air_date.gte": since.isoformat(),
            "sort_by": "first_air_date.asc",
            "include_null_first_air_dates": "false",
            "language": "en-US",
        }
        if networks:
            params["with_networks"] = "|".join(map(str, networks))
        if companies:
            params["with_companies"] = "|".join(map(str, companies))
        page = 1
        while True:
            data = self._get("/discover/tv", page=page, **params)
            yield from data.get("results") or []
            total = min(int(data.get("total_pages") or 1), MAX_PAGES)
            if page >= total:
                return
            page += 1

    # ---------- 详情 ----------

    def series(self, tv_id: int) -> TmdbSeries:
        data = self._get(
            f"/tv/{tv_id}",
            language="en-US",
            append_to_response="keywords,external_ids,translations",
        )
        if self.raw:
            self.raw.put("tmdb", "tv", str(tv_id), data)
        return parse_series(data)

    def season(self, tv_id: int, number: int) -> list[TmdbEpisode]:
        data = self._get(f"/tv/{tv_id}/season/{number}", language="en-US")
        if self.raw:
            self.raw.put("tmdb", "season", f"{tv_id}/{number}", data)
        return [parse_episode(e) for e in data.get("episodes") or []]


# ---------- 解析 ----------


def parse_series(d: dict[str, Any]) -> TmdbSeries:
    zh = _zh_translation(d)
    keywords = (d.get("keywords") or {}).get("results") or []
    nxt = d.get("next_episode_to_air") or {}
    return TmdbSeries(
        tmdb_id=int(d["id"]),
        name_en=_s(d.get("name")),
        name_zh=_s(zh.get("name")),
        original_name=_s(d.get("original_name")),
        original_language=_s(d.get("original_language")),
        first_air_date=_date(d.get("first_air_date")),
        overview_en=_s(d.get("overview")),
        overview_zh=_s(zh.get("overview")),
        networks=[(n["id"], n.get("name") or "") for n in d.get("networks") or []],
        companies=[(c["id"], c.get("name") or "") for c in d.get("production_companies") or []],
        genre_ids=[g["id"] for g in d.get("genres") or []],
        keywords=[k["name"] for k in keywords if k.get("name")],
        imdb_id=_s((d.get("external_ids") or {}).get("imdb_id")),
        vote_average=d.get("vote_average"),
        vote_count=d.get("vote_count"),
        poster_path=_s(d.get("poster_path")),
        seasons=[
            TmdbSeason(
                number=int(s["season_number"]),
                name=_s(s.get("name")),
                air_date=_date(s.get("air_date")),
                episode_count=s.get("episode_count"),
                tmdb_id=s.get("id"),
            )
            for s in d.get("seasons") or []
        ],
        next_air_date=_date(nxt.get("air_date")),
    )


def parse_episode(e: dict[str, Any]) -> TmdbEpisode:
    return TmdbEpisode(
        number=int(e["episode_number"]),
        name=_s(e.get("name")),
        air_date=_date(e.get("air_date")),
        runtime=e.get("runtime"),
        overview=_s(e.get("overview")),
        tmdb_id=e.get("id"),
    )


def _zh_translation(d: dict[str, Any]) -> dict[str, Any]:
    items = (d.get("translations") or {}).get("translations") or []
    zh = {t.get("iso_3166_1"): t.get("data") or {} for t in items if t.get("iso_639_1") == "zh"}
    for region in _ZH_REGIONS:
        data = zh.get(region) or {}
        if _s(data.get("name")):
            # 简介可能只有别的地区有，缺了就往后找
            overview = next(
                (zh[r]["overview"] for r in _ZH_REGIONS if _s((zh.get(r) or {}).get("overview"))),
                None,
            )
            return {"name": data["name"], "overview": overview}
    return {}


def _s(v: Any) -> str | None:
    if v is None:
        return None
    v = str(v).strip()
    return v or None


def _date(v: Any) -> date | None:
    try:
        return date.fromisoformat(v) if v else None
    except ValueError:
        return None
