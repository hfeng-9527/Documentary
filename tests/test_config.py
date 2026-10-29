from pathlib import Path

import pytest

from documentary.core.config import PROJECT_ROOT, ConfigError, Settings, check_config, load_settings


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} 不在 {path.name} 里"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_repo_config_passes():
    r = check_config(PROJECT_ROOT / "config")
    assert r.ok, r.errors
    assert r.stats["brands.yaml"].count >= 3
    assert r.stats["themes.yaml"].missing_ids is None


def test_unknown_theme(config_dir):
    _edit(config_dir / "brands.yaml", "default_themes: [nature]", "default_themes: [natur]")
    r = check_config(config_dir)
    assert not r.ok
    assert any(
        "brands.yaml" in e and "UK-2" in e and "natur 不在 themes.yaml" in e for e in r.errors
    )


def test_wrong_type_points_to_item_and_field(config_dir):
    _edit(config_dir / "brands.yaml", "start_year: 2010", "start_year: abc")
    r = check_config(config_dir)
    assert r.errors == [
        "brands.yaml 第 1 条（code=UK-2） 字段 start_year：应该是整数，现在是 'abc'"
    ]


def test_missing_and_extra_field(config_dir):
    _edit(
        config_dir / "series.yaml", "per_episode: true, since_year", "per_epsiode: true, since_year"
    )
    r = check_config(config_dir)
    assert any("字段 per_epsiode：多余的字段" in e for e in r.errors)


def test_literal_field(config_dir):
    _edit(config_dir / "channels.yaml", "channel_type: independent", "channel_type: indie")
    r = check_config(config_dir)
    assert any(
        "channels.yaml 第 1 条（key=veritasium） 字段 channel_type：只能是" in e for e in r.errors
    )


def test_pilot_needs_id(config_dir):
    _edit(config_dir / "series.yaml", "tmdb_tv_id: 3562", "tmdb_tv_id: null")
    r = check_config(config_dir)
    assert any("key=nova" in e and "试点栏目要填 tmdb_tv_id" in e for e in r.errors)


def test_duplicate_key(config_dir):
    path = config_dir / "channels.yaml"
    text = path.read_text(encoding="utf-8")
    line = next(ln for ln in text.splitlines() if "key: veritasium" in ln)
    path.write_text(text + line + "\n", encoding="utf-8")
    r = check_config(config_dir)
    assert "channels.yaml：key=veritasium 重复" in r.errors


def test_yaml_syntax_error_has_line(config_dir):
    (config_dir / "awards.yaml").write_text("awards:\n  - {award: oscar\n", encoding="utf-8")
    r = check_config(config_dir)
    assert any(e.startswith("awards.yaml 第") and "YAML 格式错误" in e for e in r.errors)


def test_missing_file(config_dir):
    (config_dir / "themes.yaml").unlink()
    r = check_config(config_dir)
    assert any(e.startswith("themes.yaml：找不到文件") for e in r.errors)


def test_unknown_brand_is_warning_only(config_dir):
    r = check_config(config_dir)
    assert r.ok
    assert any("US-1" in w for w in r.warnings)


def test_settings_relative_dir_resolved_against_project(tmp_path):
    s = Settings(_env_file=None, data_dir="data")
    assert s.data_dir == PROJECT_ROOT / "data"
    assert s.db_path.name == "documentary.db"


def test_settings_errors(monkeypatch):
    monkeypatch.setenv("WEB_PORT", "abc")
    monkeypatch.setenv("PROXY_URL", "127.0.0.1:10808")
    with pytest.raises(ConfigError) as e:
        load_settings()
    text = str(e.value)
    assert "WEB_PORT：应该是整数" in text
    assert "PROXY_URL：要以 http:// 或 socks5:// 开头" in text


def test_rules_unknown_theme(config_dir):
    _edit(config_dir / "rules.yaml", "  science.math:", "  science.maths:")
    r = check_config(config_dir)
    assert "rules.yaml themes：science.maths 不在 themes.yaml 里" in r.errors


def test_rules_bad_field(config_dir):
    _edit(config_dir / "rules.yaml", "    tmdb_genres: [10763]", "    tmdb_genre: [10763]")
    r = check_config(config_dir)
    assert any("rules.yaml 字段 exclude.2.tmdb_genre：多余的字段" in e for e in r.errors)


def test_tmdb_key_blank_is_none(tmp_path):
    s = Settings(_env_file=None, data_dir=tmp_path, tmdb_api_key="  ")
    assert s.tmdb_api_key is None
