"""初筛：给每条新发现的作品一个建议（收录 / 排除 / 判断不了）、理由和主题（scope.md 第 6 节）。

只给建议，不改跟踪状态；最后由你在审核页决定。规则在 config/rules.yaml。
主题来源的优先顺序：栏目预设（有预设就只用预设）→ 品牌默认 → TMDB 关键词 → 标题和简介里的关键词。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cache

from documentary.core.config import KeywordRule, Rules
from documentary.sources.tmdb import TmdbSeries

INCLUDE, EXCLUDE = "include", "exclude"
ORIGIN_ZH = {
    "preset": "栏目预设",
    "default": "品牌默认",
    "source": "TMDB 关键词",
    "keyword": "关键词",
    "llm": "大模型建议",
    "manual": "人工",
}
_GENRE_ZH = {10764: "真人秀", 10763: "新闻", 10767: "脱口秀"}


@dataclass
class Screening:
    suggestion: str | None  # include / exclude / None（需人工）
    reasons: list[str] = field(default_factory=list)
    themes: dict[str, str] = field(default_factory=dict)  # 主题 key → 来源（ORIGIN_ZH 的键）


def screen(
    s: TmdbSeries,
    rules: Rules,
    theme_names: dict[str, str],
    *,
    preset: list[str] = (),
    brand_default: list[str] = (),
) -> Screening:
    text = " ".join(filter(None, [s.name_en, s.name_zh, s.overview_en, s.overview_zh]))
    keywords = {k.lower() for k in s.keywords}

    themes: dict[str, str] = {}
    evidence: dict[str, str] = {}
    for key in preset:
        themes.setdefault(key, "preset")
    for key in brand_default:
        themes.setdefault(key, "default")
    # 重点栏目的预设主题是你定的，不再用关键词往上加
    for key, rule in ({} if preset else rules.themes).items():
        if key in themes:
            continue
        hit = _tmdb_hit(rule, keywords)
        if hit:
            themes[key], evidence[key] = "source", hit
            continue
        hit = _text_hit(rule, text)
        if hit:
            themes[key], evidence[key] = "keyword", f"“{hit}”"
    # 有子类时去掉同一大类本身（“科学 · 宇宙/天文”已经说明是科学）
    for key in list(themes):
        if "." not in key and any(k.startswith(key + ".") for k in themes):
            del themes[key]

    reasons: list[str] = []
    excluded = False
    for rule in rules.exclude:
        genre = next((g for g in rule.tmdb_genres if g in s.genre_ids), None)
        if genre is not None:
            hit = f"TMDB 类型 {_GENRE_ZH.get(genre, genre)}"
        elif kw := _tmdb_hit(rule, keywords):
            hit = f"TMDB 关键词 {kw}"
        elif word := _text_hit(rule, text):
            hit = f"标题或简介含“{word}”"
        else:
            continue
        reasons.append(f"疑似{rule.label}：{hit}")
        excluded = True

    lang = s.original_language
    if rules.languages and lang and lang not in rules.languages:
        reasons.append(f"非中英原产（原始语种 {lang}），需确认有英文配音")
        excluded = True

    if themes:
        parts = []
        for key, origin in themes.items():
            how = ORIGIN_ZH[origin] + (f" {evidence[key]}" if key in evidence else "")
            parts.append(f"{theme_names.get(key, key)}（{how}）")
        reasons.insert(0, "主题：" + "、".join(parts))

    if excluded:
        suggestion = EXCLUDE
    elif themes:
        suggestion = INCLUDE
    else:
        suggestion = None
        reasons.append("未判断出主题，需人工")
    return Screening(suggestion, reasons, themes)


def _tmdb_hit(rule: KeywordRule, keywords: set[str]) -> str | None:
    return next((k for k in rule.tmdb if k.lower() in keywords), None)


def _text_hit(rule: KeywordRule, text: str) -> str | None:
    return next((w for w in rule.text if _pattern(w).search(text)), None)


@cache
def _pattern(word: str) -> re.Pattern[str]:
    if word.isascii():  # 英文按整词，不分大小写
        return re.compile(rf"(?<![A-Za-z0-9]){re.escape(word)}(?![A-Za-z0-9])", re.IGNORECASE)
    return re.compile(re.escape(word))  # 中文按包含
