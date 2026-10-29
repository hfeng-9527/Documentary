# 迭代 0：工程骨架（v0.0）

> 状态：计划已确认（2026-10-29）；开发和自测完成，**等你验收**（第 6 节）。
> 依据：`plan.md` 第 5 节、`process.md`、`architecture.md` 第 1、4、5、7、9.5 节、`data-model.md` 第 5 节。
> 分支：`iter-0-skeleton`。验收通过后开合并请求合并到 `main`，打标签 `v0.0`。

---

## 1. 目标

把“能写代码、能运行、能测试”的基础搭好，并在你的 Windows 电脑上验证环境没问题。
**这个迭代不碰任何数据来源**（不调 TMDB，不需要 API key、不需要代理）。

## 2. 包含的功能

| # | 内容 | 具体做什么 |
|---|---|---|
| 1 | 项目结构 | 按 `architecture.md` 第 4 节建目录：`src/documentary/{core,web}`、`tests/`、`alembic/`、`reports/`；其他模块（`sources/`、`pipeline/`、`sync/`、`llm/`）等用到的迭代再建，不放空文件 |
| 2 | 工程文件 | `pyproject.toml`（Python 3.12，依赖见第 5 节）+ `uv.lock`；`.gitattributes`（统一 LF）；`.gitignore`（含 `data/`、`.env`）；`.env.example`；`CHANGELOG.md`（v0.0 一段）；根目录 `README.md`（Windows 安装运行步骤） |
| 3 | 配置加载 | `core/config.py`：用 pydantic-settings 读 `.env` / 环境变量（`DATA_DIR`、`PROXY_URL`、`WEB_HOST`、`WEB_PORT`、`LOG_LEVEL`）；读并校验 `config/*.yaml` 现有 6 个文件（品牌、频道、重点栏目、主题、手动收录、奖项）。出错时指出**哪个文件、第几条、哪个字段、什么问题**，例如“brands.yaml 第 3 条 default_themes 里的 natur 不在 themes.yaml 里” |
| 4 | 配置校验规则 | 必填字段、类型；`code` / `key` 不重复；引用的主题 key 必须在 `themes.yaml` 里；`brand_code` 不在 `brands.yaml` 里时只给**提醒**、不算错误（品牌表迭代 2a 才补全，现在 NOVA 等引用的 US-1 等还没有）；`pilot: true` 的条目编号不能是 `null`（其余条目允许 `null`，只统计“还有几个没查”） |
| 5 | 数据库 | `core/db.py`：SQLite，WAL 模式，文件在 `<DATA_DIR>/documentary.db`；Alembic 迁移框架；第一个迁移建 `run` 运行记录表（字段见第 4 节） |
| 6 | 命令行 | Typer，命令名 `doc`：`doc version`（版本号）、`doc check-config`（检查 `.env` + 全部 YAML，打印各文件条目数、未查编号数，通过/失败）、`doc db upgrade`（建库/升级表结构，内部调 Alembic） |
| 7 | 网页 | FastAPI + Jinja2 + htmx（htmx 放本地 `static/`，不走外网 CDN）；`doc web` 启动；首页显示：版本号、配置检查结果、数据库状态、最近几条运行记录（现在是空的）；另有 `/health` 返回 `ok` |
| 8 | 运行记录 | 跑 `doc check-config` 时写一条 `run` 记录，验证“命令 → 数据库 → 网页”这条路通 |
| 9 | 日志 | `core/logging.py`：控制台 + `<DATA_DIR>/runs/` 下的日志文件；预留脱敏 `api_key` 的过滤器 |
| 10 | 测试 | pytest：配置校验（正确配置通过；各类错误配置报出正确的位置）、迁移能建表、首页和 `/health` 能打开、`doc version` / `check-config` 命令；ruff 检查和格式化 |
| 11 | 自动检查 | GitHub Actions：每次推送在 Ubuntu **和 Windows** 上跑 ruff + pytest（Windows 那一路用来尽早发现路径、编码问题） |

## 3. 不包含的功能（留给后面的迭代）

- 任何数据来源（TMDB 等）和 `core/http.py` 代理客户端 → 迭代 1
- 除 `run` 以外的表 → 迭代 1 起按 `data-model.md` 第 5 节逐步建
- `config/rules.yaml`（主题关键词、评分门槛）→ 迭代 1 用到时建（`architecture.md` 第 4 节里列了这个文件，现在还没有）
- `run` 表的排队、进度字段 → 迭代 3
- Dockerfile、docker-compose → 迭代 5
- ntfy、运行报告正文 → 迭代 3

## 4. `run` 表（本迭代的字段）

按 `data-model.md`，本迭代只建基础字段，排队和进度在迭代 3 通过迁移加：

| 字段 | 说明 |
|---|---|
| id | 编号 |
| task | 任务名（本迭代只有 `check-config`） |
| trigger | `cli` / `cron` / `web` |
| params | 参数（JSON） |
| status | `running` / `success` / `partial` / `failed` |
| started_at / finished_at | 时间（UTC） |
| stats | 统计（JSON） |
| report_path | 报告文件路径（本迭代为空） |

## 5. 依赖

运行：fastapi、uvicorn、jinja2、typer、pydantic-settings、pyyaml、sqlalchemy、alembic。
开发：pytest、ruff、httpx（测试网页用）。
`httpx`、BeautifulSoup 等抓取用的库在迭代 1 起再加。

## 6. 验收清单（你在 Windows 上操作）

全部在 PowerShell 里运行。外网慢时先按 README 第 0 步设代理（`127.0.0.1:10808`）。

```
[ ] 1. 装 uv：README 第 1 步。重新打开 PowerShell 后 `uv --version` 显示版本号
[ ] 2. 下载代码并切到开发分支：
         git clone https://github.com/hfeng-9527/documentary.git Documentary
         cd Documentary
         git checkout iter-0-skeleton
         uv sync
       应该看到 uv 下载 Python 3.12 和依赖，最后没有报错
[ ] 3. Copy-Item .env.example .env   （不用改内容）
[ ] 4. uv run doc version            → 显示 0.0.0
[ ] 5. uv run doc db upgrade         → “✓ 数据库已是最新（表结构版本 0001）”，
                                       项目里出现 data\documentary.db
[ ] 6. uv run doc check-config       → 列出 6 个文件的条目数（品牌 3、频道 2、栏目 26、主题 6、
                                       手动收录 13、奖项 0），1 条黄色提醒（品牌表还没补全），
                                       最后 “✓ 配置检查通过”
[ ] 7. 用记事本打开 config\brands.yaml，把第一个 default_themes: [nature] 改成 [natur]，保存，
       再跑 uv run doc check-config  → 红字 “brands.yaml（code=UK-2）字段 default_themes：
                                       natur 不在 themes.yaml 里”，最后 “✗ 配置检查未通过”
       改回 [nature]，再跑一次确认通过
[ ] 8. uv run doc web                → 显示网页地址；浏览器打开 http://localhost:8000 ：
       - 顶部 “纪录片跟踪 v0.0.0”
       - 配置检查 “通过”，6 个文件的表格
       - 数据库 “正常”
       - 最近运行里有第 6、7 步的 check-config 记录：通过的显示“成功”（绿字），
         改错那次显示“失败”（红字），时间是你电脑的本地时间
       PowerShell 里按 Ctrl+C 停止
[ ] 9. 打开 https://github.com/hfeng-9527/documentary/actions ，iter-0-skeleton 分支最新一次
       运行是绿色对勾（Ubuntu 和 Windows 两项都通过）
```

有任何一步和描述不一样，把那一步的输出（或截图）发给我。

## 7. 需要你做的 / 决定的

1. **装 uv**：开发完成、验收时按 README 装即可，现在不用做。
2. **请确认**以下几个默认选择（不同意的直接说）：
   - 网页端口 **8000**，Windows 上只监听本机（`127.0.0.1`）；树莓派上再改成监听局域网
   - Windows 上数据目录默认放**项目文件夹里的 `data/`**（已在 `.gitignore`，不会提交）
   - 自动检查在 Ubuntu 和 Windows 两个系统上都跑（GitHub 对公开 / 私有仓库都有免费额度，这个项目用量很小）
   - 版本号写法：代码里 `0.0.0`，Git 标签 `v0.0`
   - **已确认**（2026-10-29）。另：你电脑上的本地代理是 `127.0.0.1:10808`，外网慢时装 uv、`uv sync` 可以走这个代理（README 里写明），`.env.example` 的 `PROXY_URL` 也以它为例
3. 确认本计划后，我开始写代码。

## 8. 验收结果

2026-10-29，你在 Windows 上操作（`D:\AI\Projects\Claude\Documentary\Documentary`）：

| 步骤 | 结果 |
|---|---|
| 1–2 装 uv、clone、`uv sync` | 通过。过程中遇到两个网络问题：git clone 被重置（git 不读 PowerShell 的代理变量，要用 `git config --global http.proxy`）；`uv sync` 下载超时（设 `UV_HTTP_TIMEOUT=120` 后重跑）。README 第 0 步已补上这两点 |
| 3–6 `.env`、version、db upgrade、check-config | 通过，输出与清单一致 |
| 7 故意改错 default_themes | 通过：报出 `brands.yaml（code=UK-2）字段 default_themes：natur 不在 themes.yaml 里`，改回后通过 |
| 8 网页 | 首页、样式、htmx 都正常加载（待你确认页面内容） |
| 9 GitHub Actions | 通过（Ubuntu、Windows 两项都是绿色） |

小问题：浏览器请求 `/favicon.ico` 返回 404（没有网站图标），不影响使用，不处理。
