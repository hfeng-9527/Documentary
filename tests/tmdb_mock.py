"""假的 TMDB：按请求找 tests/fixtures/tmdb/ 里的样例返回（README 有文件名规则）。"""

from __future__ import annotations

import json
import re
from pathlib import Path

import httpx

FIXTURES = Path(__file__).parent / "fixtures" / "tmdb"
KEY = "0123456789abcdef0123456789abcdef"


class FakeTmdb:
    def __init__(self, fixtures: Path = FIXTURES, *, key: str = KEY):
        self.fixtures = fixtures
        self.key = key
        self.calls: list[str] = []
        self.fail: dict[str, int] = {}  # 路径片段 → 返回的状态码

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path.removeprefix("/3")
        params = request.url.params
        self.calls.append(path)
        for frag, code in self.fail.items():
            if frag in path:
                return httpx.Response(code, json={"status_message": "fake error"})
        if params.get("api_key") != self.key:
            return httpx.Response(401, json={"status_code": 7, "status_message": "Invalid API key"})
        name = self._name(path, params)
        f = self.fixtures / f"{name}.json" if name else None
        if not f or not f.is_file():
            return httpx.Response(404, json={"status_code": 34})
        return httpx.Response(200, json=json.loads(f.read_text(encoding="utf-8")))

    @staticmethod
    def _name(path: str, params) -> str | None:
        if path == "/discover/tv":
            kind = "networks" if "with_networks" in params else "companies"
            ids = params.get(f"with_{kind}")
            return f"discover-{kind}-{ids}-p{params.get('page', '1')}"
        if m := re.fullmatch(r"/tv/(\d+)/season/(\d+)", path):
            return f"season-{m[1]}-{m[2]}"
        if m := re.fullmatch(r"/tv/(\d+)", path):
            return f"tv-{m[1]}"
        return None

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self)
