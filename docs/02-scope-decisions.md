# 范围决策记录（第三版）

> **注意**：本文件是讨论过程记录，当前有效的范围见 `scope.md`，跟踪方案见 `tracking.md`。

> 基于 `01-scope-candidates.md` 第 0 节的问题，记录已确认的决定。

| # | 问题 | 决定 |
|---|---|---|
| Q1 | 起始年份 | 默认 2010，各品牌按 HD 普及时间微调（见 01 第 3 节） |
| Q2 | 2010 年前的高清经典 | **收录**，标准见下 |
| Q3 | 自然/地理 | **收录** |
| Q4 | 时政/调查新闻 | **不收** |
| Q5 | 纪实剧/历史重演 | **不收** |
| Q6 | 院线纪录长片 | **收录** |
| Q7 | YouTube / B 站 | **只收 YouTube，不考虑 B 站**；电视台官方 YouTube 频道也跟踪。方案见 `03-web-video-tracking.md` |
| Q8 | 语种 | 收英文、中文原产；**非中英原产的作品，有官方英文配音版才收**（只有英文字幕不算） |
| Q9 | 排除 | 伪科学、真人秀、真实犯罪、体育、明星传记、央视主旋律政论片 **一律不收** |
| — | 电视/流媒体作品去重 | **暂不做**，第一步只建基础数据 |
| — | YouTube ↔ B 站去重 | 不考虑 B 站，**不再需要** |
| — | 电视台官方 YouTube 上传 ↔ 电视作品 | 暂不去重，只预留关联字段 |
| — | 聚合频道（Free Documentary、Timeline、Real Stories、Spark 等） | 按普通 YouTube 频道管理 |
| — | NHK、ARTE | **不收**（电视作品和 YouTube 频道都不收） |

## 由此带来的范围调整

- 移出：US-4 FRONTLINE、US-10 中 VICE 一类、OT-3 Al Jazeera、OT-2 *Four Corners*；History 的 *Washington* / *Grant* 等人物纪实剧；NatGeo *Mars*；Netflix *Roman Empire*；US-9 CNN 年代史中偏时政部分需逐部判断。
- 移出：EU-1 ARTE、ASIA-4 NHK（整体不收）。
- 有条件保留（非中英原产）：EU-2 ZDF Terra X、EU-3 *Apocalypse*、EU-6 ORF、ASIA-5 韩国三台。
  - 品牌保留在候选池里，但**按作品逐部判断**：有官方英文配音版才收，只有英文字幕的不收。
  - 预期情况（待核实）：
    - *Apocalypse*：主要几部有英文旁白版（如 *Apocalypse: The Second World War*），可收。
    - DW Documentary：本身就以英文制作播出，可收。
    - ZDF Terra X、ORF *Universum*、韩国三台：部分作品通过国际发行做了英文版，需要逐部查。
- 移出：ASIA-3 中的 B 站自制纪录片（B 站整体不考虑；如果作品在其他平台有正版发行，仍可按电视/流媒体作品收录）。
- 移出（类型）：Netflix 的真实犯罪、体育类；HBO 的真实犯罪类。

## 2010 年前高清经典：收录标准

**标准**：原生高清拍摄，且存在官方 1080p 发行（蓝光或正版流媒体 1080p）。不满足的（如 2001 年的 *The Blue Planet* 为标清）不收。

候选（待核实）：
- BBC：*Planet Earth*(2006)、*Galápagos*(2006)、*Earth: The Power of the Planet*(2007)、*The Story of India*(2007)、*Nature's Great Events*(2009)、*Life*(2009)
- BBC × CCTV：*Wild China /《美丽中国》*(2008)
- PBS / Ken Burns：*The War*(2007)、*The National Parks*(2009)
- Channel 4 / PBS：*The Ascent of Money*(2008)
- 院线：*Earth*(2007)、*Home*(2009)、*Océans*(2009，法语原产→按 Q8 排除，除非放宽)
- CCTV：《故宫》(2005，是否高清母版待核实)

## 院线纪录长片：跟踪来源

- 奥斯卡最佳纪录长片（提名 + 获奖）
- 金马奖最佳纪录片（中文作品的主要来源）
- Sundance、IDFA 等电影节（可选，量大，后续再定）
- 叠加主题过滤：只留科学、工程、历史、经济、人文、自然地理

## 数据字段上的影响

- 每部作品需要记录：原产语种、是否有官方英文配音、是否有中文版本。
- 非中英原产的作品，以“有官方英文配音”作为入库条件。
