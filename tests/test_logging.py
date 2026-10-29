from documentary.core.logging import redact


def test_redact_api_key():
    url = "https://api.themoviedb.org/3/tv/1?api_key=abc123&language=zh-CN"
    assert redact(url) == "https://api.themoviedb.org/3/tv/1?api_key=***&language=zh-CN"
    assert redact("monkey=1") == "monkey=1"
