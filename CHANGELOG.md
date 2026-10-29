# 版本记录

每个版本写：新增了什么、修了什么、需要你手动做的事。

## v0.1 — 迭代 1：TMDB 小范围最小闭环

**新增**
- `doc discover --source tmdb`：按品牌发现纪录片系列（试点 BBC Earth、Netflix），直接跟踪重点栏目（试点 NOVA、Horizon、Inside the Factory，按集）；`--brand`、`--series` 只跑一个，`--dry-run` 只预览不写库
- 初筛（`config/rules.yaml`）：主题、疑似不收的类型、非中英原产，给出建议和理由，由你审核决定
- 网页：首页概览、审核（逐条 / 整组“全部收录”“按建议处理”、收录时改主题）、作品列表、待下载（按 TMDB 评分排序、只看计划中）、详情（季 / 集、评分、状态历史、改状态和主题）、中英文搜索
- 片源状态手动标记：普通系列按季，长青栏目按集（可整季标记），列表页可整部标记
- 数据库：作品、季、集、各来源编号、主题、评分、状态变化、检查进度等表（表结构版本 0002）；TMDB 原始返回另存 `data\raw.db`
- 网络：境外请求走 `PROXY_URL`，自动重试、限速，日志和报错里不显示 key

**需要你做的**
- `.env` 里加 `TMDB_API_KEY=你的key`
- 运行 `uv sync`、`uv run doc db upgrade`（自动先备份旧库）

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
