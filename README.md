# 纪录片跟踪

个人使用的网页应用：整理和跟踪主流纪录片，作为家庭 NAS 下载片源的决策依据。
设计文档在 `docs/`，从 `docs/plan.md` 开始看。

## 在 Windows 上安装和运行

下面的命令都在 **PowerShell** 里运行（开始菜单搜“PowerShell”）。

### 0. 外网慢的话，先让这个窗口走代理

装 uv、下载 Python 和依赖都要访问境外网站。慢或连不上时，先在 PowerShell 窗口里运行：

```powershell
$env:HTTP_PROXY  = "http://127.0.0.1:10808"
$env:HTTPS_PROXY = "http://127.0.0.1:10808"
$env:UV_HTTP_TIMEOUT = "120"     # 下载超时从 30 秒放宽到 120 秒
```

只对当前窗口有效，关掉窗口就失效，**每开一个新窗口都要重新运行**。如果 10808 是 socks 端口（http 写法连不上），把 `http://` 换成 `socks5://`。
`uv sync` 下载中途超时，直接再运行一次就行，已经下载完的包不会重新下载。

git **不读**上面的设置，要单独给 git 配代理（只需一次）：

```powershell
git config --global http.proxy http://127.0.0.1:10808
git config --global https.proxy http://127.0.0.1:10808
```

不需要了用 `git config --global --unset http.proxy` 和 `git config --global --unset https.proxy` 取消。

### 1. 装 uv（只需一次）

uv 是 Python 环境管理工具，会自动下载这个项目需要的 Python 3.12，不用另外装 Python。

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

装完**关掉 PowerShell 再重新打开**（第 0 步的代理设置要重新运行一次），检查：

```powershell
uv --version
```

### 2. 下载代码、装依赖

```powershell
cd D:\          # 换成你想放项目的位置
git clone https://github.com/hfeng-9527/documentary.git Documentary
cd Documentary
uv sync
```

以后更新代码：在 `Documentary` 文件夹里运行 `git pull`，再运行 `uv sync`。

### 3. 配置

```powershell
Copy-Item .env.example .env
```

`.env` 里是数据目录、代理、网页端口和密钥，每一项的说明写在文件里。
要采集 TMDB 数据，加一行你的 TMDB API key（申请步骤见 `docs/sessions.md` 第 6.1 节）：

```
TMDB_API_KEY=你的32位key
```

已有 `.env` 的（迭代 0 复制过的）直接在里面加这一行，不用重新复制。
`.env` 只在你电脑上，不会提交到 GitHub。

### 4. 初始化数据库、检查配置

```powershell
uv run doc db upgrade      # 建库；以后版本更新改了表结构时也运行这条（会自动先备份）
uv run doc check-config    # 检查 .env 和 config\*.yaml
```

数据默认放在项目里的 `data\` 文件夹（数据库、备份、日志）。

### 5. 打开网页

```powershell
uv run doc web
```

浏览器打开 http://localhost:8000 。在 PowerShell 窗口按 `Ctrl+C` 停止。

### 6. 采集数据（TMDB）

TMDB 在境外，要开着代理（`.env` 里的 `PROXY_URL`）。

```powershell
uv run doc discover --source tmdb --dry-run   # 先预览：只抓取和初筛，列出会新增什么，不写数据库
uv run doc discover --source tmdb             # 正式运行
```

- 现在只跑试点：品牌 BBC Earth（UK-2）、Netflix（ST-1），重点栏目 NOVA、Horizon、Inside the Factory。
- 第一次从品牌起始年份全部查一遍，要几分钟；以后再运行只查新出的，已经有的不会重复。
- 只跑一个：`--brand UK-2` 或 `--series nova`。
- 某个品牌失败不影响其他品牌，下次从它自己上次成功的时间接着查。
- 跑完到网页的“审核”页处理新发现的条目。

## 命令一览

| 命令 | 作用 |
|---|---|
| `uv run doc version` | 显示版本号 |
| `uv run doc check-config` | 检查配置，结果记一条运行记录 |
| `uv run doc db upgrade` | 建库 / 升级表结构 |
| `uv run doc discover --source tmdb` | 发现新内容（`--brand`、`--series` 只跑一个，`--dry-run` 只预览） |
| `uv run doc web` | 启动网页 |
| `uv run doc --help` | 全部命令的帮助 |

## 开发

```powershell
uv run pytest            # 自动化测试
uv run ruff check        # 代码检查
uv run ruff format       # 统一格式
```

每次推送到 GitHub，会在 Ubuntu 和 Windows 上自动跑一遍检查和测试（`.github/workflows/ci.yml`）。
