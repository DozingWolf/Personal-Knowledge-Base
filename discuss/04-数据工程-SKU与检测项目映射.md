---
title: 数据工程——SKU 与检测项目映射
created: 2026-10-06
updated: 2026-10-06
status: 设计完成，待实施
---

# 04 数据工程：SKU ↔ 检测项目映射

> 问题：ERP 里的商品与《检验类医疗服务价格项目立项指南》的 662 个项目**很难对上，需要专家判断**。
> 目标：设计一套可开工的映射流程与表结构。**专家是公司内部的产品 / 商务专家，不是医保政策专家**——这决定了界面必须用业务语言。

## 一、诊断：为什么必然对不上

**因为 ERP 商品和 662 个项目，是两套不同的分类逻辑在描述两件不同的事：**

- ERP 商品 = **产品**（卖的东西）：某品牌某型号 ALT 测定试剂盒（IFCC 法），80mL×2
- 662 个项目 = **服务项目**（医院收钱的名目）：丙氨酸氨基转移酶检测费，单位「次」

难点按严重程度：

**① 粒度不对齐（最致命）**

| 情形 | 例子 |
|---|---|
| 一个 SKU → 多个项目 | 复合质控品 / 联检试剂盒同时覆盖多个指标 |
| 一个项目 → 多个 SKU | 「葡萄糖检测费」对应生化试剂、POCT 试纸、血气模块 |
| 一个项目含多个指标 | 「血常规检测费（全血细胞计数和五分类）」含 RBC、WBC、Hb、MCV… |
| 计价组合 | 乙肝两对半 = 抗体费×3 + 抗原费×2，**不是一个项目对一盒试剂** |
| SKU 根本不对应项目 | 仪器、清洗液、样本杯、管路、电极、软件 |

**② 术语两套**：ALT / 丙氨酸氨基转移酶 / 谷丙转氨酶 / GPT；HBsAg / 乙肝表面抗原 / 乙型肝炎病毒表面抗原。

**③ 方法学不在项目名里**：「葡萄糖检测费」看不出是化学法、己糖激酶法还是 POCT。

**④ 加收项 / 扩展项**：商品可能同时命中主项与某个加收项。

**⑤ 注册证适用范围**是最权威依据，但写法是「用于体外定量测定人血清样本中的 XX」，仍需解析。

## 二、认知转变：这不是「连接」，是「映射」

**「不对应」是合法且必须的答案。** 若抱着「每个商品都得找到项目」的心态，会卡死在仪器、质控品、校准品、清洗液上。五种关系类型：

| 关系 | 含义 | 处理 |
|---|---|---|
| `EXACT` | 精确一一对应 | 直接采用 |
| `PARTIAL` | 部分对应（复合试剂覆盖多指标） | 拆到指标级 |
| `COMPONENT` | 是某项目的组成部分（质控品、校准品） | 挂到所服务的项目/平台 |
| `NO_ITEM` | 不对应任何检验项目（仪器、耗材、软件） | **显式标记，不是遗漏** |
| `AMBIGUOUS` | 依赖口径，需专家定 | 进审核队列 |

## 三、关键发现：附件 2 的第三列是一把现成的钥匙

**国家卫健委 2023 版技术规范那一列，642 条里 317 条（49%）带方法学后缀：**

```
医保编码列:  002501010150200 → 血细胞分析(全血细胞计数+五分类)
卫健委列:    CAA05EC1 → 全血细胞计数+五分类测定-电阻抗激光荧光法
             CAA05EB1 → 全血细胞计数+五分类测定-电阻抗激光法
             CAA05EA1 → 全血细胞计数+三分群测定-电阻抗法
```

出现频次最高的方法学后缀：化学法(29)、凝固法(21)、直接涂片镜检法(14)、酶联免疫法(12)、光学显微镜法(9)、透射比浊免疫法(8)、卡式柱凝集法(8)、试管凝集法(7)、聚集法(6)、凝集法(5)、化学发光免疫法(5)、高通量测序法(5)、流式细胞术(4)、分光光度法(4)、微流控芯片法(4)、干化学法(3)、胶体金免疫层析法(3)、免疫荧光法(3)…

**为什么这是钥匙**：ERP 商品名（原厂试剂盒名）几乎都带方法学，而**医保编码那一列不带，卫健委这一列带**。

**因此映射不要用「项目名」单键，要用「检测指标 + 方法学」双键：**

- 左边从 ERP 提取：指标名 + 方法学
- 右边从卫健委列提取：指标名 + 方法学后缀
- 医保编码列只用来做最后的**归一收口**（多个方法学收口到同一收费项目）

这能一并解决「术语不同 + 方法学缺失」两个难点。

## 四、表结构（8 张，核心 3 张）

**核心 3 张：`test_item`、`erp_sku`、`sku_item_mapping`。其余为辅助。**

```sql
-- 1. 检测项目主数据（来自附件 1）
test_item(
  test_item_id      TEXT PK,          -- 内部ID TI-0001
  item_seq          INT,              -- 附件1序号 1..662
  item_name         TEXT,             -- 项目名称
  service_output    TEXT,             -- 服务产出        ← 专家界面要用
  price_composition TEXT,             -- 价格构成
  surcharge_items   TEXT,             -- 加收项
  extension_items   TEXT,             -- 扩展项
  unit              TEXT,             -- 计价单位
  pricing_note      TEXT,             -- 计价说明        ← 业务规则金矿
  category          TEXT,             -- 临床类别（我方归类）
  method_class      TEXT,             -- 生化/免疫/分子/血液/微生物/POCT
  flag_panel_discount INT,            -- 是否受联检分档折扣影响
  flag_ref_interval   INT,            -- 是否在参考区间减收清单
  flag_data_upload    INT,            -- 是否要求上传数据
  source_version    TEXT,             -- '2026试行版'
  source_url        TEXT
)

-- 2. 官方编码映射（来自附件 2，多对多）
test_item_code_map(
  map_id        TEXT PK,
  test_item_id  TEXT FK,
  code_system   TEXT,   -- 'NHSA_MEDICAL'(约1800个) | 'NHC_2023'(约1752个)
  code          TEXT,
  code_item_name TEXT,  -- 旧项目名 ← 卫健委列带方法学！
  methodology   TEXT,   -- 从 code_item_name 抽出的方法学
  partition     TEXT,   -- MAIN | SURCHARGE | EXTENSION
  UNIQUE(code_system, code)
)

-- 3. ERP 商品（规范化后）
erp_sku(
  sku_id          TEXT PK,      -- ERP 商品编码
  sku_name        TEXT,         -- 原始商品名
  manufacturer    TEXT,         -- 原厂/品牌
  reg_cert_no     TEXT,         -- 注册证号
  spec            TEXT,         -- 规格
  -- 以下为机器派生
  normalized_name TEXT,         -- 规范化名称
  analyte_norm    TEXT,         -- 规范指标名
  methodology_norm TEXT,        -- 规范方法学
  sku_class       INT,          -- 1=试剂 2=辅助品 3=仪器设备 9=待定
  platform_norm   TEXT,         -- 适用平台/仪器
  revenue_weight  REAL          -- 营收权重 ← 决定审核优先级
)

-- 4. 映射边表（核心资产）
sku_item_mapping(
  mapping_id    TEXT PK,
  sku_id        TEXT FK,
  test_item_id  TEXT FK,        -- NO_ITEM 时为 NULL
  relation_type TEXT,           -- EXACT|PARTIAL|COMPONENT|NO_ITEM|AMBIGUOUS
  analyte_id    TEXT,           -- PARTIAL 时指明是哪个指标
  mapping_basis TEXT,           -- NAME|PRICING_NOTE|METHODOLOGY|REG_CERT|LEGACY_CODE|EXPERT
  confidence    REAL,           -- 0..1
  evidence      TEXT,           -- JSON：命中词/原文片段/候选差异
  status        TEXT,           -- MACHINE_SUGGESTED|EXPERT_CONFIRMED|DISPUTED|REJECTED
  reviewer      TEXT,
  reviewed_at   TEXT,
  no_item_reason TEXT,          -- 仪器/耗材/辅助品/其他
  note          TEXT,
  UNIQUE(sku_id, test_item_id, analyte_id)
)

-- 5. 指标别名词典
analyte_dict(
  term_id   TEXT PK,
  term      TEXT,      -- 'ALT' / '谷丙转氨酶' / 'GPT'
  term_type TEXT,      -- ABBR|FULL|COLLOQ|EN
  canonical TEXT,      -- '丙氨酸氨基转移酶'
  source    TEXT,      -- '附件1计价说明'|'附件2'|'专家补充'|'ERP'
  UNIQUE(term, canonical)
)

-- 6. 方法学词典
methodology_dict(
  term_id     TEXT PK,
  term        TEXT,    -- 'IFCC法' / '速率法' / '化学发光法'
  canonical   TEXT,
  method_class TEXT,   -- 大类
  source      TEXT
)

-- 7. 审核任务队列
review_task(
  task_id    TEXT PK,
  sku_id     TEXT FK,
  priority   INT,      -- 按 revenue_weight 降序
  reason     TEXT,     -- MULTI_CANDIDATE|NO_CANDIDATE|CONFLICT|LOW_CONFIDENCE
  candidates TEXT,     -- JSON: Top-3 + 理由
  assigned_to TEXT,
  state      TEXT,     -- OPEN|IN_PROGRESS|DONE|SKIPPED
  created_at TEXT, closed_at TEXT
)

-- 8. 沉淀规则
mapping_rule(
  rule_id      TEXT PK,
  rule_type    TEXT,   -- NAME_PATTERN|ANALYTE|METHOD|CATEGORY
  pattern      TEXT,
  target_item_id TEXT,
  relation_type  TEXT,
  hit_count    INT,
  derived_from TEXT,   -- 来自哪条专家确认
  active       INT
)
```

**要点**：`sku_item_mapping` 是**多对多边表**，别压成一对一；`PARTIAL` 靠 `analyte_id` 拆到指标级；`NO_ITEM` 的 `test_item_id` 允许为 NULL 但**必须显式记录**；`status` 与 `reviewer` 必须有——**未确认的映射不能拿去算营收**。

## 五、映射流程（7 步）

| 步 | 做什么 | 谁 |
|---|---|---|
| **0** | 导入附件 1（662 项 + 使用说明）、附件 2（编码映射）、ERP 商品清单 | 机器 |
| **1** | **商品预分类**：见下表 | 机器 |
| **2** | **名称规范化与要素抽取**：从 `sku_name` 抽检测指标、方法学、适用平台并归一 | 机器（LLM） |
| **3** | **三路候选生成**：见下表 | 机器 |
| **4** | **置信度打分与分层**：见下表 | 机器 |
| **5** | **专家审核**（见第六节） | **人** |
| **6** | **规则沉淀**：专家确认 → 生成 `mapping_rule` → 重跑未处理 SKU，迭代至队列清空 | 机器 |
| **7** | **验收**（见第七节） | 人 + 机器 |

**Step 1 预分类规则：**

| 规则 | 归类 |
|---|---|
| 名称含 质控 / 校准 / 定标 / 清洗 / 稀释 / 缓冲 / 样本杯 / 吸头 / 管路 / 电极 / 溶血剂 / 鞘液 | `辅助品` |
| 名称含 分析仪 / 仪器 / 流水线 / 软件 / 系统 / 模块 / 工作站 | `仪器设备` |
| 名称含 测定试剂盒 / 检测试剂盒 / 试纸条 / 检测卡，且有指标 | `试剂` |
| 其余 | `待定` |

→ 能砍掉 20–40% 的量，让它们**根本不进专家队列**。

**Step 2 的免费语料**：附件 1 的「计价说明」列就是官方的**指标缩写-全称对照表**（血常规那条直接列了 RBC/WBC/L/N/M/E/B/Hb/MCV/MCH/MCHC/HCT），白捡的词典语料。

**Step 3 三路候选：**

| 路径 | 依据 | 说明 |
|---|---|---|
| A 名称匹配 | 规范指标 + 方法学 → `code_map.code_item_name` | **主力路径**，卫健委列带方法学 |
| B 旧码倒查 | SKU 若带旧医保编码 → `code_map` 直查 | 最准，依赖 ERP 是否存该字段 |
| C 注册证范围 | 解析注册证「适用范围」文本 | 兜底与交叉验证 |

三路合并去重 → **Top-3 候选**。**LLM 只出候选与理由，不要让它直接给答案**（答案可信度无法验证）。

**Step 4 打分与分层：**

打分：指标精确匹配 +0.4；方法学匹配或语境兼容 +0.3；唯一候选 +0.2；旧码路径支持 +0.3；名称相似度 +0~0.2；候选冲突 −0.3。

| 分数 | 处置 |
|---|---|
| ≥0.85 且唯一 | 自动通过，抽样复核 5% |
| 0.5–0.85 | **专家必看** |
| <0.5 或无候选 | **专家必看** |
| Step 1 判定的辅助品/仪器 | 自动 `COMPONENT` / `NO_ITEM`，抽样复核 |

**这一步是整套流程的价值所在**：3000 个 SKU 里可能只有 400–600 个真需要人判断。**别让专家从第一行开始看。**

## 六、专家界面：按「一屏决策」设计

**约束：内部产品/商务专家熟悉「这个试剂干什么」，但不熟「什么是加收项、什么是联检折扣」。**

**左侧｜ERP 商品全貌**
商品名、原厂、规格、注册证号、**注册证适用范围原文**（他们最信的判断依据），以及若有的采购价与销量。

**中间｜Top-3 候选**，每个展示四样：

1. 项目名称 + 序号
2. **服务产出**（原文照搬，最直观说明「这个项目是干什么的」）
3. **计价说明**（业务规则，**决定映射的商业后果**）
4. 该候选下的**方法学列表** + 匹配理由 + 高亮的命中证据

**右侧｜操作**（选项少而明确）

- 选这个
- 都不对 → 手动搜索 662 项目（支持按指标名 / 拼音搜）
- 不对应任何项目 → 选原因（仪器 / 耗材 / 辅助品 / 其他）
- 一个商品对多个项目 → 多选
- **不确定 → 挂起转交**（这条必须有，否则专家会硬选，污染数据）

**批量操作**：同类商品自动分组（同原厂 + 同指标 + 同方法学），一次决策应用到整组。**这是把工时压下来的关键。**

## 七、验收标准与优先级

| 指标 | 目标 |
|---|---|
| **营收加权映射覆盖率** | 覆盖 80% 营收的 SKU 全部有 `EXPERT_CONFIRMED` |
| SKU 数量覆盖率 | 次要指标，长尾不重要 |
| 准确性 | 抽样 30 条人工复核，错误率 <5% |
| 残留冲突 | `AMBIGUOUS` + `DISPUTED` 占比 <5% |

**「营收加权」四个字很重要**：若 200 个 SKU 占 90% 营收，映射完这 200 个，分析就已可用。**不要为长尾 SKU 拖延上线。**

`review_task.priority` 按 `revenue_weight` 降序——**按营收排，不按编码排**。即使只做完一半，覆盖的价值也最大。

## 八、两个副产品洞察

1. **映射不上本身是情报。** 「很难对上」若集中在某几类，说明商品结构里辅助品/仪器占比高，毛利实际来自耗材绑定——这是「产品组合优化」的重要输入。
2. **反证品类集中度。** 若 SKU 大量收口到少数几个价格项目，说明**组合暴露度高度集中**，一次集采就能打穿。**这个结论不依赖内部数据，只看映射结果就能估算。**

## 九、需要从 ERP 提供的东西

| # | 字段 | 重要性 |
|---|---|---|
| 1 | 商品编码 + 商品名称 | **必需** |
| 2 | 原厂 / 品牌 | 重要（用于分组与批量） |
| 3 | 注册证号 | 有则路径 C 可用，大幅提高置信度 |
| 4 | 规格 | 包装量，用于 PARTIAL 拆分 |
| 5 | 品类 / 分类字段 | Step 1 预分类的起点 |
| 6 | **是否存了旧医保编码** | **若有，映射难度下降一个数量级**（附件 2 直接把 1800 个旧码映射到 662 个新项目） |
| 7 | 采购价 / 销售价 / 销量 | 决定 `revenue_weight` 与审核优先级 |

## 十、实施建议

- **第一版只建 3 张核心表**（`test_item`、`erp_sku`、`sku_item_mapping`）；`review_task` 与 `mapping_rule` 等要跑专家队列和第二轮迭代时再建。
- **先映射高价值 SKU**（占 80% 营收的），不要追求全量。

---

## 变更记录

| 日期 | 变更 |
|---|---|
| 2026-10-06 | 初稿：难点诊断 + 表结构 + 7 步流程 + 专家界面设计 |
