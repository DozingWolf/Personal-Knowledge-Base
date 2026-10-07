---
title: IVD 领域包
created: 2026-10-06
updated: 2026-10-06
status: 骨架（registry / layer_template 已建，其余待实施）
---

# domains/ivd — 体外诊断试剂贸易领域包

> **第一个领域包**。IVD 的全部领域语义（检测项目、编码体系、集采、注册证、测定方法学…）都收敛在这个目录内，`core/` 里不许出现。

## 一、资产清单

| 文件 / 目录 | 内容 | 状态 |
|---|---|---|
| [registry.yaml](registry.yaml) | **唯一接入点**：来源、文档类型、实体类型、编码体系、关系类型、注册表引用 | 🟨 骨架 |
| [layer_template.yaml](layer_template.yaml) | 六层传导栈（政策→支付→检测项目→产品→SKU→营收） | 🟩 已成文 |
| `ontology/` | 本体扩展：`extends` 内核上层本体，定义 TestItem / Product / Registration / Policy 子类 | ⬜ 待建（M4 定稿时） |
| `dict/analyte.yaml` | 检测指标词典（别名 → 规范名） | ⬜ 待建（语料已在手） |
| `dict/methodology.yaml` | 方法学词典（含大类归属） | ⬜ 待建（语料已在手） |
| `scorecard.yaml` | 评分卡：维度、权重、阈值 | ⬜ 待建（M13 设计时） |
| `terminology.yaml` | **政策术语 ↔ 业务语言**对照（专家界面用） | ⬜ 稍后（用户已明确暂缓） |
| `questions.md` | 能力问题 + 决策日志 | ⬜ 待建 |

## 二、领域特有概念（不许进内核）

| 概念 | 说明 |
|---|---|
| **检测项目 TestItem** | 662 个立项指南项目。政策作用的单元，也是映射的右侧端点 |
| **编码体系** | `NHSA_MEDICAL`（医保医疗服务项目）、`NHC_2023`（国家卫健委技术规范）、未来对齐 `LOINC` |
| **方法学** | 生化 / 免疫 / 分子 / 血液 / 微生物 / POCT；同项目不同方法学形成**替代关系** |
| **注册证 Registration** | NMPA 注册证号、有效期、核准适用范围 |
| **集采状态** | 中选 / 非中选 /「不视为非中选」/ 未纳入 + 中选价 + 协议量 + 周期 |
| **价格规则集 PriceRuleSet** | 联检分档折扣、数据上传减收、参考区间减收、间接计算不另收 |
| **仪器 ↔ 试剂绑定** | 封闭 / 开放系统；"换不换平台"比"换不换试剂"影响大一个量级 |

## 三、领域数据现状

| 数据 | 位置 | 状态 |
|---|---|---|
| 662 个检测项目 | [discuss/sources/parsed/test_item.csv](../../discuss/sources/parsed/test_item.csv) | 🟩 已解析 |
| 3825 条官方编码映射 | [discuss/sources/parsed/test_item_code_map.csv](../../discuss/sources/parsed/test_item_code_map.csv) | 🟩 已解析（7 处 `align_ok=FALSE` 待人工核对） |
| 政策原文快照 | [discuss/sources/raw/](../../discuss/sources/raw/) | 🟩 已归档 |
| 集采中选清单与中选价 | 国家医保招采子系统（需登录） | ⬜ **最大缺口** |
| ERP 商品清单 | 公司内部 | ⬜ 待交付 |

## 四、关键参考文献

- 业务与传导栈：[discuss/02](../../discuss/02-业务建模-IVD贸易与传导栈.md)
- 两份政策分析：[discuss/03](../../discuss/03-政策追踪-2026检验类立项指南与上海集采.md)
- SKU ↔ 检测项目映射设计：[discuss/04](../../discuss/04-数据工程-SKU与检测项目映射.md)
