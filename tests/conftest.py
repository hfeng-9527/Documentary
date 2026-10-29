import shutil
from pathlib import Path

import pytest

from documentary.core.config import PROJECT_ROOT, Settings


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """仓库里 config/ 的一份拷贝，测试可以随便改。"""
    d = tmp_path / "config"
    shutil.copytree(PROJECT_ROOT / "config", d)
    return d


@pytest.fixture
def settings(tmp_path: Path, config_dir: Path) -> Settings:
    return Settings(_env_file=None, data_dir=tmp_path / "data", config_dir=config_dir)
