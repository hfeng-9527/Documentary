import httpx
import pytest

from documentary.core.http import AuthError, HttpClient, NotFound, ProxyError, SourceError


def _client(settings, handler, **kw):
    sleeps: list[float] = []
    c = HttpClient(
        settings,
        name="TMDB",
        abroad=True,
        rate_per_sec=0,
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
        **kw,
    )
    return c, sleeps


def test_ok(settings):
    c, _ = _client(settings, lambda r: httpx.Response(200, json={"a": 1}))
    assert c.get_json("https://x.test/a") == {"a": 1} and c.requests == 1


def test_retries_then_succeeds(settings):
    answers = iter(
        [
            httpx.Response(500),
            httpx.Response(429, headers={"Retry-After": "3"}),
            httpx.Response(200, json=[1]),
        ]
    )
    c, sleeps = _client(settings, lambda r: next(answers))
    assert c.get_json("https://x.test/a") == [1]
    assert sleeps == [1, 3.0] and c.requests == 3


def test_gives_up_after_retries(settings):
    c, sleeps = _client(settings, lambda r: httpx.Response(503))
    with pytest.raises(SourceError, match="HTTP 503"):
        c.get_json("https://x.test/a", {"api_key": "secret123"})
    assert c.requests == 4 and sleeps == [1, 2, 4]


def test_error_message_hides_key(settings):
    c, _ = _client(settings, lambda r: httpx.Response(400))
    with pytest.raises(SourceError) as e:
        c.get_json("https://x.test/a", {"api_key": "secret123"})
    assert "secret123" not in str(e.value) and "api_key=***" in str(e.value)


def test_401_is_fatal_and_not_retried(settings):
    c, _ = _client(settings, lambda r: httpx.Response(401))
    with pytest.raises(AuthError, match="TMDB_API_KEY") as e:
        c.get_json("https://x.test/a")
    assert e.value.fatal and c.requests == 1


def test_404(settings):
    c, _ = _client(settings, lambda r: httpx.Response(404))
    with pytest.raises(NotFound):
        c.get_json("https://x.test/a")


def test_timeout_is_retried(settings):
    def boom(r):
        raise httpx.ReadTimeout("slow", request=r)

    c, sleeps = _client(settings, boom, retries=1)
    with pytest.raises(SourceError, match="超时"):
        c.get_json("https://x.test/a")
    assert c.requests == 2


def test_connect_error_with_proxy_points_to_proxy(settings):
    settings = settings.model_copy(update={"proxy_url": "http://127.0.0.1:10808"})

    def refused(r):
        raise httpx.ConnectError("[Errno 111] Connection refused", request=r)

    c, _ = _client(settings, refused)
    with pytest.raises(ProxyError, match="连不上代理 http://127.0.0.1:10808") as e:
        c.get_json("https://x.test/a")
    assert e.value.fatal and c.requests == 1


def test_domestic_source_ignores_proxy(settings):
    settings = settings.model_copy(update={"proxy_url": "http://127.0.0.1:10808"})
    assert HttpClient(settings, name="豆瓣", abroad=False).proxy is None
    assert HttpClient(settings, name="TMDB", abroad=True).proxy == "http://127.0.0.1:10808"
