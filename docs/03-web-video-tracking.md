# YouTube / B 站：跟踪方式、去重、频道推荐

## 1. YouTube 怎么跟踪

**官方 YouTube Data API v3**（需要 Google Cloud 的 API key，免费额度为每天 10,000 单位）。

| 步骤 | 接口 | 配额消耗 |
|---|---|---|
| 频道 → 上传列表 | `channels.list?part=contentDetails` 得到 `uploads` 播放列表（`UC…` → `UU…`） | 1 |
| 全量回溯 | `playlistItems.list`，每页 50 条 | 每页 1 |
| 视频详情 | `videos.list?part=snippet,contentDetails`，每次最多 50 个 ID | 每次 1 |
| 系列/合集 | `playlists.list` + `playlistItems.list`（很多频道用播放列表组织系列） | 每页 1 |
| 日常增量 | RSS：`https://www.youtube.com/feeds/videos.xml?channel_id=UC…`（最近 15 条） | **0**（不走 API） |

- **成本很低**：一个 1000 条视频的频道，全量回溯约 40 单位。**避免用 `search.list`**（每次 100 单位）。
- **过滤 Shorts**：按时长过滤（建议 ≥ 5 分钟）。另有非官方的 `UULF…` 前缀（只列长视频），可用但不保证长期有效。
- **清晰度**：`contentDetails.definition` 只区分 `hd`（≥720p）和 `sd`，不区分 1080p。对 2014 年后的频道基本都是 `hd`，够用。
- **可拿到的字段**：标题、简介、发布时间、时长、标签、分类、默认语言、缩略图、播放量/点赞（统计字段可选）。

## 2. B 站怎么跟踪

B 站**没有面向公开数据的官方开放 API**，只能用网页端接口（非官方，可能变动，有风控）。

| 用途 | 接口（网页端） | 说明 |
|---|---|---|
| UP 主投稿列表 | `x/space/wbi/arc/search?mid=…` | 需要 WBI 签名（`w_rid`/`wts`），容易触发风控（-352 / 412） |
| 视频详情 | `x/web-interface/view?bvid=…` | 标题、简介、时长、发布时间、分 P、**`copyright`（1 = 自制，2 = 转载）** |
| 合集/系列 | `x/polymer/web-space/seasons_archives_list` | 对应 UP 主的“合集” |
| **官方纪录片区（PGC）** | `pgc/season/index/result?season_type=3`、`pgc/view/web/season?season_id=…` | B 站正版纪录片（自制的《人生一串》，以及引进的 BBC 等）——这是另一条有价值的数据源 |

- **实现建议**：
  - 全量回溯：用开源库 `bilibili-api-python`（已封装 WBI 签名），低频请求（每 2–3 秒一次）。
  - 日常增量：自建 **RSSHub**（`/bilibili/user/video/:uid`），定时拉。
- **风险**：接口非官方，需要接受偶发失效、需要维护；仅做个人/低频使用，不做大规模抓取。

## 3. YouTube ↔ B 站重复：情况与去重方案

### 重复主要有三种

| 类型 | 例子 | 怎么识别 |
|---|---|---|
| **A. 同一创作者双平台发布** | 很多中文 UP 主同时发 B 站和 YouTube | 先在**频道级**人工绑定（同一创作者），再按“时长 ±2 秒 + 发布日期 ±3 天”匹配视频 |
| **B. 官方或授权的中文字幕版** | 部分英文频道在 B 站有官方/授权账号（如 3Blue1Brown） | 同上：频道级绑定 + 时长匹配；B 站发布时间通常晚于 YouTube |
| **C. 未授权搬运** | B 站大量 `copyright = 2` 的转载 | **不跟踪**。B 站简介里常带原视频链接，可正则提取 YouTube 视频 ID 作关联（可选） |

### 建议的规则：从源头减少去重

1. **每个创作者只认一个“首发平台”**：英文创作者以 YouTube 为准，中文创作者以 B 站为准（大多数在 B 站首发）。
2. **只跟踪官方账号，不跟踪搬运**（B 站过滤 `copyright = 2`）。
3. 对 A、B 两类，另一平台的同一视频不作为新条目，而是挂在原条目下，作为“另一观看地址”。
4. 数据结构：`创作者 → 平台账号（多个）→ 视频`；视频之间用“同一内容”关系相连。

这样去重只发生在**已知的同一创作者内部**，规则简单，准确率高，不需要做跨全站的模糊匹配。

### 另一种重叠：电视台官方 YouTube 频道

BBC Earth、NOVA PBS、National Geographic、DW Documentary 的官方频道，以及 Timeline、Real Stories、Free Documentary 这类**正版重新上传电视纪录片的频道**，内容和电视/流媒体作品重叠。电视作品暂不去重，所以**这类频道暂不作为 YouTube 创作者跟踪**，以后可以作为电视作品的“观看渠道”来用。

## 4. YouTube 推荐频道（英文，待勾选）

> 标准：纪录片或深度长视频风格、制作精良、持续更新（或有大量存量），属于科学、工程、历史、经济、人文、自然地理。
> ⚠ 标记的频道含有时政/观点内容，需要逐条过滤或整体排除。

### 科学
- [ ] **Kurzgesagt – In a Nutshell** — 动画科普，宇宙/生物/社会
- [ ] **Veritasium** — 物理与科学，实验 + 纪录片风格
- [ ] **PBS Space Time** — 天体物理/理论物理，偏硬核
- [ ] **3Blue1Brown** — 数学可视化（B 站有官方中文账号）
- [ ] **Numberphile** — 数学
- [ ] **minutephysics** — 物理短讲
- [ ] **SmarterEveryDay** — 工程与物理实验
- [ ] **Steve Mould** — 物理现象
- [ ] **NileRed** — 化学实验
- [ ] **Cool Worlds** — 天文学（哥伦比亚大学 David Kipping）
- [ ] **Scott Manley** — 航天
- [ ] **Kyle Hill** — 科学，核能题材较多
- [ ] **LEMMiNO** — 纪录片风格的科学/历史谜题，更新慢但质量很高
- [ ] **Primer** — 进化/博弈的模拟动画

### 工程技术
- [ ] **Real Engineering** — 工程分析，航空、能源、军工技术
- [ ] **Practical Engineering** — 土木/基础设施
- [ ] **The B1M** — 建筑与超级工程（对应“超级工程”类）
- [ ] **Mustard** — 航空史与工程，纪录片级制作
- [ ] **Branch Education** — 3D 动画讲解芯片、电子设备原理
- [ ] **Asianometry** — 半导体与科技产业史（兼经济）
- [ ] **Everyday Astronaut** — 火箭工程
- [ ] **Mentour Pilot** — 航空事故分析
- [ ] **CuriousMarc** — 古董计算机/Apollo 设备修复
- [ ] **Plainly Difficult** — 工程事故

### 经济 / 商业
- [ ] **Wendover Productions** — 物流、交通、经济系统
- [ ] **Economics Explained** — 宏观经济、国家经济
- [ ] **Money & Macro** — 宏观经济、货币政策
- [ ] **Patrick Boyle** — 金融市场
- [ ] **Modern MBA** — 企业案例分析
- [ ] **Company Man** — 公司兴衰史
- [ ] **PolyMatter** — 经济、产业（⚠ 部分时政）
- [ ] **Bloomberg Originals** — 商业纪录片
- [ ] **CNBC**（纪录片/专题部分） — 商业纪录片
- [ ] **The Economist**（视频频道） — ⚠ 较多时政

### 历史
- [ ] **Fall of Civilizations** — 文明衰亡，单集 1–4 小时，纪录片级
- [ ] **Kings and Generals** — 军事史动画
- [ ] **Historia Civilis** — 罗马史
- [ ] **Epic History TV** — 战役与战争史
- [ ] **The Great War** — 一战（2014–2018 逐周讲述，已完结）
- [ ] **World War Two**（Indy Neidell） — 二战逐周讲述
- [ ] **OverSimplified** — 幽默动画讲历史，更新慢
- [ ] **Extra History** — 动画历史系列
- [ ] **Invicta** — 古代军事史
- [ ] **toldinstone** — 罗马社会文化
- [ ] **History Time** — 欧洲/英国史前与中世纪，长片
- [ ] **Tasting History with Max Miller** — 饮食史（兼人文）
- [ ] **Townsends** — 18 世纪生活史

### 自然 / 地理
- [ ] **RealLifeLore** — 地理（⚠ 部分时政）
- [ ] **Geography Now** — 国家概况
- [ ] **Atlas Pro** — 地理
- [ ] **Deep Look**（KQED/PBS） — 微距自然
- [ ] **Journey to the Microcosmos** — 微生物世界
- [ ] **Tom Scott** — 地点与奇闻，2024 年起停更，存量很多

### 人文 / 艺术 / 建筑
- [ ] **Great Art Explained** — 名画解读
- [ ] **Smarthistory** — 艺术史
- [ ] **Nerdwriter1** — 艺术/电影视频随笔
- [ ] **Stewart Hicks** — 建筑
- [ ] **The School of Life** — 哲学/心理

### 暂不建议（原因供参考）
- Vox、Johnny Harris：时政比例高
- Simon Whistler 系（Megaprojects、Biographics 等）：产量大，质量参差
- 老高与小茉等：伪科学/猎奇
- Timeline、Real Stories、Free Documentary 等电视纪录片重新上传频道：见第 3 节，暂不作为创作者跟踪

## 5. B 站候选 UP 主（中文，初步，待你补充和确认）

- 科学：二次元的中科院物理所、李永乐老师、毕导THU、芳斯塔芙（古生物/生物）、无穷小亮的科普日常（自然/生物）
- 工程/科技：回形针PaperClip
- 经济/商业：小Lin说、所长林超、柴知道
- 历史：史图馆
- 地理：星球研究所、地球知识局、中国国家地理
- 人文/心理：汤质看本质、意外艺术
- 另外：**B 站官方纪录片区（PGC）**单独作为一个数据源（自制和引进的正版纪录片）
