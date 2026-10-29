from documentary.core.config import PROJECT_ROOT, check_config
from documentary.pipeline.prescreen import EXCLUDE, INCLUDE, screen
from documentary.sources.tmdb import TmdbSeries

CATALOG = check_config(PROJECT_ROOT / "config").catalog
NAMES = CATALOG.theme_names()


def _tv(**kw) -> TmdbSeries:
    base = dict(
        tmdb_id=1,
        name_en="X",
        name_zh=None,
        original_name="X",
        original_language="en",
        first_air_date=None,
        overview_en="",
        overview_zh=None,
    )
    return TmdbSeries(**{**base, **kw})


def _screen(tv, **kw):
    return screen(tv, CATALOG.rules, NAMES, **kw)


def test_brand_default_theme():
    sc = _screen(_tv(), brand_default=["nature"])
    assert sc.suggestion == INCLUDE and sc.themes == {"nature": "default"}
    assert sc.reasons == ["主题：自然/地理（品牌默认）"]


def test_tmdb_keyword_theme():
    sc = _screen(_tv(keywords=["Astronomy"]))
    assert sc.themes == {"science.space": "source"}
    assert "科学 · 宇宙/天文（TMDB 关键词 astronomy）" in sc.reasons[0]


def test_text_keyword_english_whole_word_and_chinese():
    assert _screen(_tv(overview_en="How factories work")).themes == {
        "engineering.manufacturing": "keyword"
    }
    # “sport” 不应该命中 “transport”
    sc = _screen(_tv(overview_en="The history of public transport"))
    assert sc.suggestion == INCLUDE and "sport" not in " ".join(sc.reasons)
    assert "economics" in _screen(_tv(name_zh="中国经济")).themes


def test_child_replaces_parent():
    sc = _screen(_tv(keywords=["black hole"]), brand_default=["science"])
    assert sc.themes == {"science.space": "source"}


def test_preset_is_final():
    sc = _screen(_tv(overview_en="science and philosophy"), preset=["science"])
    assert sc.themes == {"science": "preset"}


def test_exclusions():
    sc = _screen(_tv(keywords=["true crime"], overview_en="A murder case"))
    assert sc.suggestion == EXCLUDE
    assert "疑似真实犯罪：TMDB 关键词 true crime" in sc.reasons
    sc = _screen(_tv(genre_ids=[99, 10764]), brand_default=["nature"])
    assert sc.suggestion == EXCLUDE and "疑似真人秀：TMDB 类型 真人秀" in sc.reasons


def test_language():
    sc = _screen(_tv(original_language="es"), brand_default=["nature"])
    assert sc.suggestion == EXCLUDE
    assert "非中英原产（原始语种 es），需确认有英文配音" in sc.reasons
    assert _screen(_tv(original_language="zh"), brand_default=["nature"]).suggestion == INCLUDE
    assert _screen(_tv(original_language="cn"), brand_default=["nature"]).suggestion == INCLUDE


def test_no_theme_needs_human():
    sc = _screen(_tv(overview_en="Stories you have never heard."))
    assert sc.suggestion is None and sc.reasons == ["未判断出主题，需人工"]
