# 版本记录

每个版本写：新增了什么、修了什么、需要你手动做的事。

## v0.0 — 迭代 0：工程骨架

**新增**
- 项目结构、`pyproject.toml` + `uv.lock`（Python 3.12，uv 管理）
- `doc` 命令：`version`、`check-config`、`db upgrade`、`web`
- 配置检查：`.env` 和 `config/*.yaml` 六个文件，出错时指出文件、条目、字段
- SQLite 数据库 + Alembic 迁移，第一张表 `run`（运行记录）；升级表结构前自动备份
- 网页首页：版本号、配置检查结果、数据库状态、最近运行记录
- 自动化测试（pytest）、代码检查（ruff）；GitHub Actions 在 Ubuntu 和 Windows 上自动跑

**需要你做的**
- 装 uv，复制 `.env.example` 为 `.env`（步骤见 `README.md`）
