"""原始数据：各来源返回的内容原样压缩存进单独的 `<DATA_DIR>/raw.db`（data-model.md 第 2.5 节）。

以后调整规则时用它重新判断，不用重新抓。每个“来源 + 种类 + 编号”保留最新一份，
内容变化时多留几份历史（最多 KEEP 份）；内容没变只更新抓取时间。
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import zlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

KEEP = 3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_record (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    kind TEXT NOT NULL,
    external_id TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    payload BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_raw_key ON raw_record (source, kind, external_id, id);
"""


class RawStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(path)
        self._con.execute("PRAGMA journal_mode=WAL")
        self._con.executescript(_SCHEMA)

    def close(self) -> None:
        self._con.close()

    def __enter__(self) -> RawStore:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def put(self, source: str, kind: str, external_id: str, payload: Any) -> None:
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        now = datetime.now(UTC).isoformat()
        key = (source, kind, external_id)
        with self._con:
            row = self._con.execute(
                "SELECT id, content_hash FROM raw_record WHERE source=? AND kind=? "
                "AND external_id=? ORDER BY id DESC LIMIT 1",
                key,
            ).fetchone()
            if row and row[1] == digest:
                self._con.execute("UPDATE raw_record SET fetched_at=? WHERE id=?", (now, row[0]))
                return
            self._con.execute(
                "INSERT INTO raw_record (source, kind, external_id, fetched_at, content_hash, "
                "payload) VALUES (?, ?, ?, ?, ?, ?)",
                (*key, now, digest, zlib.compress(text.encode("utf-8"))),
            )
            self._con.execute(
                "DELETE FROM raw_record WHERE source=? AND kind=? AND external_id=? AND id NOT IN "
                "(SELECT id FROM raw_record WHERE source=? AND kind=? AND external_id=? "
                "ORDER BY id DESC LIMIT ?)",
                (*key, *key, KEEP),
            )

    def get(self, source: str, kind: str, external_id: str) -> Any | None:
        row = self._con.execute(
            "SELECT payload FROM raw_record WHERE source=? AND kind=? AND external_id=? "
            "ORDER BY id DESC LIMIT 1",
            (source, kind, external_id),
        ).fetchone()
        return json.loads(zlib.decompress(row[0])) if row else None

    def count(self) -> int:
        return self._con.execute("SELECT COUNT(*) FROM raw_record").fetchone()[0]
