import pytest

from documentary.pipeline.states import LibrarySummary


@pytest.mark.parametrize(
    "summary, status, text",
    [
        (LibrarySummary("季", 5, 3, 0), "partial", "3/5 季已入库"),
        (LibrarySummary("季", 5, 0, 2), "planned", "未入库，计划中 2 季"),
        (LibrarySummary("季", 2, 2, 0), "have", "全部已入库（2 季）"),
        (LibrarySummary("季", 0, 0, 0), "none", "没有季"),
        (LibrarySummary("集", 300, 42, 0), "partial", "已入库 42 集"),
        (LibrarySummary("集", 300, 0, 0), "missing", "未入库（共 300 集）"),
        (LibrarySummary("集", 3, 1, 2), "partial", "已入库 1 集，计划中 2 集"),
        (LibrarySummary("", 1, 0, 1), "planned", "计划中"),
    ],
)
def test_summary(summary, status, text):
    assert summary.status == status and summary.text == text
