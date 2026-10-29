# 正式收录范围 v1

> 这是**当前有效**的范围定义，汇总了 `01`–`03` 的讨论结果。
> `[x]` = 收录，`[ ]` = 默认不收。勾选状态是我按已有决定给出的默认值，不同意的直接改。

---

## 1. 总则

| 项目 | 规则 |
|---|---|
| 时间 | 默认 2010 年起，各品牌起点见第 2 节；2010 年前的高清经典按第 5 节标准例外收录 |
| 语种 | 英文、中文原产；非中英原产的作品**必须有官方英文配音版**（只有字幕不算） |
| 主题 | 科学、工程技术、历史、经济/商业、人文、自然/地理 |
| 形式 | 电视/流媒体纪录片系列、纪录长片（院线 + 流媒体独立长片，按评分收录）、YouTube 视频 |
| 不收 | 时政/调查新闻、纪实剧/历史重演、伪科学、真人秀、真实犯罪、体育、音乐/明星传记、央视主旋律政论片 |
| 不收的平台 | B 站 |
| 去重 | 第一步不做；YouTube 视频预留一个可空的“对应电视作品”字段 |

---

## 2. 电视 / 流媒体品牌

| 收录 | 编号 | 品牌 | 起点 | 备注 |
|---|---|---|---|---|
| [x] | UK-1 | BBC（Two / Four / Studios） | 2010 | 含 *Horizon*；*Storyville* 只收符合主题的 |
| [x] | UK-2 | BBC Natural History Unit / BBC Earth | 2010（经典回补到 2006） | |
| [x] | UK-3 | Channel 4 | 2010 | *Unreported World* 属时政，不收 |
| [x] | UK-4 | Sky Documentaries / Sky Nature | 2010 | |
| — | UK-5 | 独立制作公司（Silverback 等） | — | 只作“出品方”标签，不单独跟踪 |
| [x] | US-1 | PBS / NOVA | 2010 | |
| [x] | US-2 | PBS：*American Experience*、*Secrets of the Dead*、*Nature* | 2010 | |
| [ ] | US-2b | PBS：*Independent Lens*、*POV* | — | 以社会议题为主，默认不收 |
| [x] | US-3 | Ken Burns / Florentine Films | 2009（*The National Parks*） | |
| [x] | US-5 | National Geographic | 2010 | 纪实剧（如 *Mars*）不收 |
| [x] | US-6 | Discovery / Science Channel | 2010 | 真人秀不收 |
| [x] | US-7 | History Channel | 2010 | 伪科学、真人秀、人物纪实剧不收 |
| [x] | US-8 | Smithsonian Channel | 2010 | |
| [x] | US-9 | CNN Original Series / CNN Films | 2013 | 年代史只收历史向，*Parts Unknown* 收 |
| [x] | US-10 | HBO Documentary Films | 2010 | 只收符合主题的（如 *The Inventor*），真实犯罪不收 |
| [x] | ST-1 | Netflix | 2015 | |
| [x] | ST-2 | Apple TV+ | 2019 | |
| [x] | ST-3 | Disney+ | 2019 | 与 National Geographic 内容重叠，暂不去重 |
| [ ] | ST-4 | Amazon Prime Video | — | 原创以体育和真实犯罪为主，默认不收 |
| [ ] | ST-5 | CuriosityStream / MagellanTV | — | 量大，质量参差，默认不收 |
| [x] | EU-2 | ZDF Terra X | 2010 | 只收有英文配音版的 |
| [x] | EU-3 | *Apocalypse* 系列（France 2） | 2009 | 只收英文旁白版 |
| [x] | EU-5 | DW Documentary | 2010 | 通过 YouTube 跟踪（第 4 节） |
| [x] | EU-6 | ORF *Universum* | 2010 | 只收有英文配音版的 |
| [x] | ASIA-1 | CCTV（含 CCTV-9 纪录频道） | 2011 | 主旋律政论片不收 |
| [x] | ASIA-2 | 其他中国电视台（湖南卫视、上海 SMG 等） | 2010 | |
| [x] | ASIA-3 | 中国网络平台（腾讯视频、优酷等，不含 B 站） | 2016 | |
| [x] | ASIA-5 | 韩国 KBS / EBS / MBC | 2010 | 只收有英文配音版的，预计很少 |
| [x] | ASIA-6 | 台湾公视 | 2010 | |
| [x] | OT-1 | CBC（*The Nature of Things*） | 2010 | |
| [x] | OT-2 | ABC Australia（*Catalyst*） | 2010 | *Four Corners* 属时政，不收 |

已移出：FRONTLINE、VICE、Al Jazeera、NHK、ARTE。

---

## 3. 纪录长片（院线 + 流媒体独立长片）

> 范围包括院线上映的纪录片，也包括流媒体平台的独立纪录长片（如 Netflix 的 *My Octopus Teacher*），统称“纪录长片”。
> **以评分为主要入库标准**，奖项只作补充。

### 入库规则（满足任一条，且通过主题过滤）

| 规则 | 条件（初始值，建库后用真实数据校准） |
|---|---|
| A. 英文片评分 | IMDb 评分 ≥ 7.0，且评分人数 ≥ 2,000 |
| B. 中文片评分 | 豆瓣评分 ≥ 7.5，且评价人数 ≥ 3,000 |
| C. 奖项 | 奥斯卡最佳纪录长片、金马奖最佳纪录片的提名或获奖作品，不看评分直接入库 |

- **评分人数门槛是关键**：冷门片评分人数少，分数容易虚高，只看分数会混进大量小众作品。
- 中文片在 IMDb 上评分人数普遍很少，所以单独用豆瓣。
- 阈值是我给的起始值，还没用真实数据验证。建库时先跑一遍 2010 年至今的数据，看命中多少部、有没有明显漏掉的名作，再调整。

### 新片的评分会变化

新片刚上映时评分人数少，达不到门槛。所以：
- 新片先进入 `观察中` 状态，不直接判定；
- 上映后 12 个月内，每次双周检查都重新拉评分；
- 达到门槛转 `待审核`，12 个月仍未达到则转 `已排除`（以后获奖仍可按规则 C 入库）。

## 4. YouTube 频道

### 入库门槛

| 频道类型 | 时长门槛 | 说明 |
|---|---|---|
| 电视台官方频道 | ≥ 20 分钟 | 片段和预告不入库 |
| 聚合频道（重新上传） | ≥ 20 分钟 | 按普通 YouTube 频道管理 |
| 独立创作者 | ≥ 5 分钟 | 主要为了过滤 Shorts |

所有频道的视频都要过主题过滤（第 6 节）。

### 4.1 电视台官方频道

- [x] BBC Earth
- [x] NOVA PBS Official
- [x] American Experience | PBS
- [x] Nature on PBS
- [x] PBS Eons
- [x] PBS Terra
- [x] National Geographic
- [x] Nat Geo Animals
- [x] Discovery
- [x] Science Channel
- [x] HISTORY
- [x] Smithsonian Channel
- [x] Our Planet（Netflix）
- [x] DW Documentary
- [x] CCTV 纪录频道官方频道

### 4.2 聚合频道

- [x] Free Documentary
- [x] Free Documentary - Nature
- [x] Timeline – World History Documentaries
- [x] Real Stories（真实犯罪内容要过滤）
- [x] Spark

### 4.3 独立创作者

科学
- [x] Kurzgesagt – In a Nutshell
- [x] Veritasium
- [x] PBS Space Time
- [x] 3Blue1Brown
- [x] Numberphile
- [x] minutephysics
- [x] SmarterEveryDay
- [x] Steve Mould
- [x] NileRed
- [x] Cool Worlds
- [x] Scott Manley
- [x] Kyle Hill
- [x] LEMMiNO
- [x] Primer

工程技术
- [x] Real Engineering
- [x] Practical Engineering
- [x] The B1M
- [x] Mustard
- [x] Branch Education
- [x] Asianometry
- [x] Everyday Astronaut
- [x] Mentour Pilot
- [x] CuriousMarc
- [x] Plainly Difficult

经济 / 商业
- [x] Wendover Productions
- [x] Economics Explained
- [x] Money & Macro
- [x] Patrick Boyle
- [x] Modern MBA
- [x] Company Man
- [x] PolyMatter（时政内容要过滤）
- [x] Bloomberg Originals
- [x] CNBC（只收纪录片/专题）
- [ ] The Economist（时政比例高，默认不收）

历史
- [x] Fall of Civilizations
- [x] Kings and Generals
- [x] Historia Civilis
- [x] Epic History TV
- [x] The Great War
- [x] World War Two
- [x] OverSimplified
- [x] Extra History
- [x] Invicta
- [x] toldinstone
- [x] History Time
- [x] Tasting History with Max Miller
- [x] Townsends

自然 / 地理
- [x] RealLifeLore（时政内容要过滤）
- [x] Geography Now
- [x] Atlas Pro
- [x] Deep Look
- [x] Journey to the Microcosmos
- [x] Tom Scott

人文 / 艺术 / 建筑
- [x] Great Art Explained
- [x] Smarthistory
- [x] Nerdwriter1
- [x] Stewart Hicks
- [x] The School of Life

默认不收：Vox、Johnny Harris（时政多）；Megaprojects、Biographics 等 Simon Whistler 系频道（质量参差）；老高与小茉（伪科学）。

---

## 5. 2010 年前高清经典

**标准**：原生高清拍摄，且有官方 1080p 发行（蓝光或正版流媒体）。

候选（入库时逐部核实）：*Planet Earth*(2006)、*Galápagos*(2006)、*Earth: The Power of the Planet*(2007)、*The Story of India*(2007)、*The War*(2007)、*Earth*(2007 院线)、*Wild China /《美丽中国》*(2008)、*The Ascent of Money*(2008)、*Life*(2009)、*Nature's Great Events*(2009)、*The National Parks*(2009)、*Home*(2009 院线)、《故宫》(2005，待核实是否高清母版)

---

## 6. 主题标签

每条作品或视频至少打一个主题标签，打不上的不收：

- **科学**：宇宙/天文、物理、化学/材料、生命科学/进化、医学/人体、数学、地球科学/气候
- **工程技术**：超级工程/建筑、交通/航空航天、制造业、能源、工程事故、计算机/互联网/AI
- **历史**：古代文明/考古、中国史、世界史、战争/军事史、近现代
- **经济/商业**：金融/货币、企业/商业史、产业/全球化、社会经济
- **人文**：艺术/设计/建筑、哲学/宗教、文学、饮食文化、地方风土、手艺/匠人
- **自然/地理**：野生动物、海洋、地理/风光
