from documentary.core.raw import KEEP, RawStore


def test_put_get_dedup_and_history(tmp_path):
    with RawStore(tmp_path / "raw.db") as raw:
        raw.put("tmdb", "tv", "1", {"name": "A"})
        raw.put("tmdb", "tv", "1", {"name": "A"})  # 没变：不新增
        assert raw.count() == 1
        for i in range(KEEP + 2):
            raw.put("tmdb", "tv", "1", {"name": f"B{i}"})
        assert raw.count() == KEEP  # 只留最近几份
        assert raw.get("tmdb", "tv", "1") == {"name": f"B{KEEP + 1}"}
        assert raw.get("tmdb", "tv", "2") is None
