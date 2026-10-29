"""配置加载：`.env`（环境相关、密钥）和 `config/*.yaml`（品牌、频道等，architecture.md 第 7 节）。

两类问题分开报告：
- 错误：配置写错了，必须改（字段缺失、类型不对、引用了不存在的主题、试点条目没填编号）。
- 提醒：现在允许、以后要补的（引用了品牌表里还没有的品牌，迭代 2a 补全）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """`.env` 和环境变量里的配置。"""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    data_dir: Path = Path("data")
    config_dir: Path = PROJECT_ROOT / "config"
    proxy_url: str | None = None
    web_host: str = "127.0.0.1"
    web_port: int = 8000
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("data_dir", "config_dir")
    @classmethod
    def _resolve(cls, v: Path) -> Path:
        return v if v.is_absolute() else PROJECT_ROOT / v

    @field_validator("proxy_url")
    @classmethod
    def _check_proxy(cls, v: str | None) -> str | None:
        if not v:
            return None
        if not v.startswith(("http://", "https://", "socks5://", "socks5h://")):
            raise ValueError("要以 http:// 或 socks5:// 开头，例如 http://127.0.0.1:10808")
        return v

    @field_validator("log_level", mode="before")
    @classmethod
    def _upper(cls, v: Any) -> Any:
        return v.upper() if isinstance(v, str) else v

    @property
    def db_path(self) -> Path:
        return self.data_dir / "documentary.db"


def load_settings() -> Settings:
    """读 `.env`；出错时抛出 ConfigError，信息里指出是哪一项。"""
    try:
        return Settings()
    except ValidationError as e:
        lines = [
            f".env 的 {'.'.join(map(str, err['loc'])).upper()}：{_zh(err)}" for err in e.errors()
        ]
        raise ConfigError(lines) from None


class ConfigError(Exception):
    def __init__(self, lines: list[str]):
        super().__init__("\n".join(lines))
        self.lines = lines


# ---------- config/*.yaml 的格式 ----------


class _Item(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Brand(_Item):
    code: str
    name: str
    start_year: int
    tmdb_networks: list[int] = []
    tmdb_companies: list[int] = []
    default_themes: list[str] = []
    notes: str | None = None
    enabled: bool = True
    pilot: bool = False


class Channel(_Item):
    key: str
    name: str
    youtube_channel_id: str | None
    channel_type: Literal["official", "aggregator", "independent"]
    min_duration_min: int
    default_themes: list[str] = []
    filters: list[str] = []
    enabled: bool = True


class Series(_Item):
    key: str
    name: str
    tmdb_tv_id: int | None
    brand_code: str | None = None
    themes: list[str] = []
    per_episode: bool = False
    since_year: int = 2010
    enabled: bool = True
    pilot: bool = False


class ThemeChild(_Item):
    key: str
    name: str


class Theme(_Item):
    key: str
    name: str
    children: list[ThemeChild] = []


class Include(_Item):
    title: str
    kind: Literal["series", "film"]
    year: int
    tmdb_id: int | None
    brand_code: str | None = None
    notes: str | None = None


class Award(_Item):
    award: Literal["oscar", "golden_horse"]
    year: int
    result: Literal["nominee", "winner"]
    title: str
    tmdb_movie_id: int | None


# 文件名 → (顶层键, 条目格式, 用来称呼条目的字段, 统计“还没查编号”的判断)
_FILES: dict[str, tuple[str, type[_Item], str, Any]] = {
    "brands.yaml": (
        "brands",
        Brand,
        "code",
        lambda b: not b.tmdb_networks and not b.tmdb_companies,
    ),
    "channels.yaml": ("channels", Channel, "key", lambda c: c.youtube_channel_id is None),
    "series.yaml": ("series", Series, "key", lambda s: s.tmdb_tv_id is None),
    "themes.yaml": ("themes", Theme, "key", None),
    "includes.yaml": ("includes", Include, "title", lambda i: i.tmdb_id is None),
    "awards.yaml": ("awards", Award, "title", lambda a: a.tmdb_movie_id is None),
}


@dataclass
class FileStat:
    count: int = 0
    missing_ids: int | None = None


@dataclass
class Catalog:
    brands: list[Brand] = field(default_factory=list)
    channels: list[Channel] = field(default_factory=list)
    series: list[Series] = field(default_factory=list)
    themes: list[Theme] = field(default_factory=list)
    includes: list[Include] = field(default_factory=list)
    awards: list[Award] = field(default_factory=list)


@dataclass
class CheckResult:
    catalog: Catalog
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, FileStat] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def check_config(config_dir: Path) -> CheckResult:
    """读并校验全部 YAML 配置。不抛异常，问题都放在结果里。"""
    result = CheckResult(Catalog())
    for fname, (top, model, ident, missing) in _FILES.items():
        items = _load_file(config_dir / fname, top, model, ident, result.errors)
        setattr(result.catalog, top, items)
        stat = FileStat(count=len(items))
        if missing is not None:
            stat.missing_ids = sum(1 for it in items if missing(it))
        result.stats[fname] = stat
    _cross_check(result)
    return result


def _load_file(path: Path, top: str, model: type[_Item], ident: str, errors: list[str]) -> list:
    fname = path.name
    if not path.is_file():
        errors.append(f"{fname}：找不到文件（{path}）")
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        where = f"第 {mark.line + 1} 行" if mark else ""
        errors.append(f"{fname} {where}：YAML 格式错误（{getattr(e, 'problem', e)}）")
        return []
    if not isinstance(data, dict) or top not in data:
        errors.append(f"{fname}：最外层要有 `{top}:`")
        return []
    raw = data[top] or []
    if not isinstance(raw, list):
        errors.append(f"{fname}：`{top}:` 下面应该是列表（每条以 - 开头）")
        return []
    items = []
    for i, entry in enumerate(raw, start=1):
        label = f"第 {i} 条"
        if isinstance(entry, dict) and entry.get(ident):
            label += f"（{ident}={entry[ident]}）"
        if not isinstance(entry, dict):
            errors.append(f"{fname} {label}：应该是“字段: 值”的形式")
            continue
        try:
            items.append(model.model_validate(entry))
        except ValidationError as e:
            for err in e.errors():
                loc = ".".join(str(p) for p in err["loc"])
                errors.append(f"{fname} {label} 字段 {loc}：{_zh(err)}")
    return items


def _cross_check(r: CheckResult) -> None:
    c = r.catalog

    theme_keys: set[str] = set()
    for t in c.themes:
        theme_keys.add(t.key)
        for ch in t.children:
            if not ch.key.startswith(t.key + "."):
                r.errors.append(f"themes.yaml 子类 {ch.key}：要以“{t.key}.”开头")
            theme_keys.add(ch.key)

    for fname, items, attr in [
        ("brands.yaml", c.brands, "code"),
        ("channels.yaml", c.channels, "key"),
        ("series.yaml", c.series, "key"),
        ("themes.yaml", [*c.themes, *(ch for t in c.themes for ch in t.children)], "key"),
    ]:
        seen: set[str] = set()
        for it in items:
            v = getattr(it, attr)
            if v in seen:
                r.errors.append(f"{fname}：{attr}={v} 重复")
            seen.add(v)

    def refs(fname: str, ident: str, field_name: str, items: list) -> None:
        for it in items:
            for key in getattr(it, field_name):
                if key not in theme_keys:
                    r.errors.append(
                        f"{fname}（{ident}={getattr(it, ident)}）字段 {field_name}："
                        f"{key} 不在 themes.yaml 里"
                    )

    refs("brands.yaml", "code", "default_themes", c.brands)
    refs("channels.yaml", "key", "default_themes", c.channels)
    refs("series.yaml", "key", "themes", c.series)

    brand_codes = {b.code for b in c.brands}
    unknown: set[str] = set()
    for items in (c.series, c.includes):
        for it in items:
            if it.brand_code and it.brand_code not in brand_codes:
                unknown.add(it.brand_code)
    if unknown:
        r.warnings.append(
            f"有 {len(unknown)} 个品牌被引用了、但还不在 brands.yaml 里（迭代 2a 补全）："
            + "、".join(sorted(unknown))
        )

    for b in c.brands:
        if b.pilot and not b.tmdb_networks and not b.tmdb_companies:
            r.errors.append(f"brands.yaml（code={b.code}）：试点品牌要填 TMDB 播出方或出品公司编号")
    for s in c.series:
        if s.pilot and s.tmdb_tv_id is None:
            r.errors.append(f"series.yaml（key={s.key}）：试点栏目要填 tmdb_tv_id")


_ZH = {
    "missing": "缺少这个字段",
    "extra_forbidden": "多余的字段（是不是拼错了？）",
    "int_type": "应该是整数",
    "int_parsing": "应该是整数",
    "int_from_float": "应该是整数",
    "bool_type": "应该是 true 或 false",
    "bool_parsing": "应该是 true 或 false",
    "string_type": "应该是文字",
    "list_type": "应该是列表，例如 [a, b]",
}


def _zh(err: dict) -> str:
    t = err["type"]
    if t == "literal_error":
        expected = err["ctx"]["expected"].replace(" or ", ", ")
        return f"只能是 {expected}，现在是 {err['input']!r}"
    if t == "value_error":
        return str(err["ctx"]["error"])
    return _ZH.get(t, err["msg"]) + (f"，现在是 {err['input']!r}" if t != "missing" else "")
