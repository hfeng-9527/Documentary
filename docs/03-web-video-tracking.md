# YouTube：跟踪方式与频道清单

> **注意**：本文件是讨论过程记录，当前有效的范围见 `scope.md`，跟踪方案见 `tracking.md`。

> 范围：**只跟踪 YouTube，不考虑 B 站**。包括两类频道：独立创作者，以及电视台/流媒体的官方频道。

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

## 2. 电视台 / 流媒体官方频道（跟踪）

这类频道上传的内容混杂：完整剧集、片段、预告、幕后花絮都有。处理规则：

- **按内容类型打标签**：完整剧集/完整纪录片、片段、预告、其他。
  - 判断依据：时长（≥ 40 分钟基本是完整剧集，20–40 分钟需要看标题，< 20 分钟基本是片段）；标题关键词（如 “Full Episode”、“Full Documentary”）；所在播放列表。
- **默认只入库 ≥ 20 分钟的视频**，片段和预告不入库（如需要可以以后放开）。
- **与电视作品的关系**：电视作品暂不去重。视频表预留一个可空的“对应作品”字段，以后再关联（例如 NOVA 频道上传的某集对应 NOVA 的某一期）。
- **语种规则同样适用**：非英文的官方频道只收英文配音的内容。

### 官方频道清单（待勾选）

英国
- [ ] **BBC Earth** — BBC 自然历史部（BBC Natural History Unit）和 BBC 科学内容的官方频道，以片段为主，也有完整长片

美国 PBS
- [ ] **NOVA PBS Official** — 近年上传了不少完整剧集
- [ ] **American Experience | PBS** — 历史
- [ ] **Nature on PBS** — 自然
- [ ] **PBS Eons** — 古生物/演化（网络原创）
- [ ] **PBS Terra** — 地球科学/自然（网络原创）
- （PBS Space Time、Deep Look 已列在第 3 节）

美国有线电视
- [ ] **National Geographic**
- [ ] **Nat Geo Animals**
- [ ] **Discovery**
- [ ] **Science Channel**
- [ ] **HISTORY** — 需过滤 *Ancient Aliens* 等伪科学和真人秀
- [ ] **Smithsonian Channel**

流媒体
- [ ] **Our Planet**（Netflix 官方，已免费上传全集）
- （Netflix、Apple TV+ 主频道以预告为主，不建议跟踪）

欧洲 / 亚洲（英文版）
- [ ] **DW Documentary** — 以英文制作，大量完整纪录片
- [ ] **CCTV 纪录频道官方频道** — 需过滤主旋律政论片

### 正版重新上传的聚合频道（按普通 YouTube 频道管理）

这类频道获得授权后重新上传老电视纪录片。**决定：当作普通 YouTube 频道管理**，不和电视作品做关联：
- [ ] **Free Documentary** / **Free Documentary - Nature**
- [ ] **Timeline – World History Documentaries**
- [ ] **Real Stories**（⚠ 真实犯罪内容多，需过滤）
- [ ] **Spark**（科学/工程）

## 3. 独立创作者频道（英文，待勾选）

> 标准：纪录片或深度长视频风格、制作精良、持续更新（或有大量存量），属于科学、工程、历史、经济、人文、自然地理。
> ⚠ 标记的频道含有时政/观点内容，需要逐条过滤或整体排除。

### 科学
- [ ] **Kurzgesagt – In a Nutshell** — 动画科普，宇宙/生物/社会
- [ ] **Veritasium** — 物理与科学，实验 + 纪录片风格
- [ ] **PBS Space Time** — 天体物理/理论物理，偏硬核
- [ ] **3Blue1Brown** — 数学可视化
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
- 中文创作者：B 站不考虑，只有在 YouTube 有官方频道的才可以加进来
