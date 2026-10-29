"""HTTP 客户端：代理、超时、重试、限速、密钥打码（architecture.md 第 5 节）。

每个来源声明自己走不走代理（`abroad=True` 走 `PROXY_URL`），来源模块不自己处理代理。
出错时抛 SourceError 的子类，信息是给人看的中文，里面不含密钥。
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

import httpx

from documentary import __version__
from documentary.core.config import Settings
from documentary.core.logging import redact

log = logging.getLogger(__name__)

USER_AGENT = f"documentary-tracker/{__version__} (personal use)"
RETRY_STATUS = {429, 500, 502, 503, 504}


class SourceError(Exception):
    """来源请求失败。fatal=True 表示其他品牌/栏目也不用再试了（如 key 错、代理不通）。"""

    fatal = False


class AuthError(SourceError):
    fatal = True


class ProxyError(SourceError):
    fatal = True


class NotFound(SourceError):
    pass


class HttpClient:
    def __init__(
        self,
        settings: Settings,
        *,
        name: str,
        abroad: bool,
        rate_per_sec: float = 4.0,
        retries: int = 3,
        timeout: float = 20.0,
        headers: dict[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.name = name
        self.proxy = settings.proxy_url if abroad else None
        self.min_interval = 1.0 / rate_per_sec if rate_per_sec > 0 else 0.0
        self.retries = retries
        self.sleep = sleep
        self.requests = 0
        self._last = 0.0
        self._client = httpx.Client(
            proxy=None if transport else self.proxy,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT, **(headers or {})},
            transport=transport,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        attempt = 0
        while True:
            attempt += 1
            self._throttle()
            self.requests += 1
            try:
                resp = self._client.get(url, params=params)
            except httpx.ProxyError as e:
                raise ProxyError(self._proxy_msg(e)) from None
            except httpx.ConnectError as e:
                if self.proxy:  # 走代理时连接失败，基本都是代理没开或地址不对
                    raise ProxyError(self._proxy_msg(e)) from None
                err: SourceError = SourceError(f"{self.name} 连接失败：{redact(str(e))}")
                wait = None
            except httpx.TimeoutException:
                err, wait = SourceError(f"{self.name} 请求超时"), None
            except httpx.HTTPError as e:
                err, wait = SourceError(f"{self.name} 请求出错：{redact(str(e))}"), None
            else:
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code == 401:
                    raise AuthError(self._auth_msg())
                if resp.status_code == 404:
                    raise NotFound(f"{self.name} 找不到：{redact(str(resp.url))}")
                err = SourceError(
                    f"{self.name} 返回 HTTP {resp.status_code}：{redact(str(resp.url))}"
                )
                if resp.status_code not in RETRY_STATUS:
                    raise err
                wait = _retry_after(resp)
            if attempt > self.retries:
                raise err
            delay = wait if wait is not None else 2 ** (attempt - 1)
            log.warning("%s，%s 秒后重试（第 %d 次）", err, delay, attempt)
            self.sleep(delay)

    def _throttle(self) -> None:
        if not self.min_interval:
            return
        gap = time.monotonic() - self._last
        if gap < self.min_interval:
            self.sleep(self.min_interval - gap)
        self._last = time.monotonic()

    def _proxy_msg(self, e: Exception) -> str:
        return (
            f"连不上代理 {self.proxy}：请确认代理软件开着，"
            f"并检查 .env 的 PROXY_URL（{redact(str(e))}）"
        )

    def _auth_msg(self) -> str:
        return f"{self.name} 拒绝了 API key（401），请检查 .env 的 {self.name.upper()}_API_KEY"


def _retry_after(resp: httpx.Response) -> float | None:
    value = resp.headers.get("Retry-After")
    try:
        return min(float(value), 60.0) if value else None
    except ValueError:
        return None
