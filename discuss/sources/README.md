---
title: 政策原始资料与解析数据
created: 2026-10-06
updated: 2026-10-06
---

# sources：政策原始资料与解析数据

本目录存放讨论所依据的**政策原文快照**与**解析后的结构化数据**。政策网页会失效或改版，因此保留原始文件。

## 目录结构

```
sources/
├── README.md              本文件
├── raw/                   原始文件快照（不改动）
│   ├── nhsa-2026-08-14-检验类立项指南.html                    政策页面快照
│   ├── nhsa-2026-08-14-附件1-检验类医疗服务价格项目立项指南试行.xlsx
│   ├── nhsa-2026-08-14-附件2-映射关系表.xlsx
│   └── smpaa-2026-08-13-上海执行省际联盟IVD集采结果通知.html
├── parsed/                解析产物（可由 scripts/ 重新生成）
│   ├── test_item.csv            662 个主项目
│   └── test_item_code_map.csv   官方编码映射
└── scripts/
    └── parse_xlsx.py      可复现的解析脚本
```

## 来源

| 文件 | 来源 | 日期 |
|---|---|---|
| nhsa 两份 | https://www.nhsa.gov.cn/art/2026/8/14/art_14_21766.html | 2026-08-14 |
| smpaa 一份 | https://www.smpaa.cn/xxgk/gggs/2026/08/13/23689.shtml | 2026-08-13（沪药事药械〔2026〕4号） |

## 重新生成 parsed/

```bash
cd <仓库根>
python3 discuss/sources/scripts/parse_xlsx.py \
  "discuss/sources/raw/nhsa-2026-08-14-附件1-检验类医疗服务价格项目立项指南试行.xlsx" \
  "discuss/sources/raw/nhsa-2026-08-14-附件2-映射关系表.xlsx" \
  "discuss/sources/parsed"
```

预期输出：`test_item.csv` 662 行；`test_item_code_map.csv` 约 3825 条（NHSA_MEDICAL 约 1919 + NHC_2023 约 1906），其中 7 处标记 `align_ok=FALSE`。

## 字段说明

### parsed/test_item.csv（662 行）

| 列 | 含义 |
|---|---|
| `item_seq` | 附件 1 的序号 1..662，**当前唯一稳定的主键** |
| `item_name` | 项目名称 |
| `service_output` | 服务产出 |
| `price_composition` | 价格构成 |
| `surcharge_items` | 加收项 |
| `extension_items` | 扩展项 |
| `unit` | 计价单位（次 / 项 …） |
| `pricing_note` | **计价说明**——含指标别名与项目级特殊计价规则，是映射与风险标记的语料金矿 |

### parsed/test_item_code_map.csv（约 3825 条）

| 列 | 含义 |
|---|---|
| `item_seq` / `item_name` | 指向 `test_item.csv` |
| `code_system` | `NHSA_MEDICAL`（医保医疗服务项目分类与代码）/ `NHC_2023`（国家卫健委 2023 版技术规范） |
| `code` | 旧编码，如 `002501010150200` / `CAA05EC1` |
| `code_item_name` | 旧项目名。**`NHC_2023` 一列约 49% 带方法学后缀**（如「全血细胞计数+五分类测定-电阻抗激光荧光法」），这是 SKU 映射的关键抓手 |
| `align_ok` | `True` 表示编码与名称可一一配对；`False` 表示该单元格两侧数量不等，**已原样保留、未经配对**，需人工核对 |

## 已知数据问题（不要当干净数据用）

1. **7 处 `align_ok=FALSE`**（4 处在 NHSA 列、3 处在 NHC 列），多为名称本身含空格导致。涉及「血液染色形态学检测费」「血型抗体效价测定费」「人类白细胞抗体检测费」「人类免疫缺陷病毒核酸检测费」「结核分枝杆菌核酸检测费」「人乳头瘤病毒核酸检测费」「结核分枝杆菌相关γ-干扰素检测费」等行。使用前需人工核对原始单元格。
2. **同一编码可能出现在多个项目下**（去重后约 1800 / 1752，未去重 1919 / 1906），是「多对多」的真实形态，不是重复错误。
3. **两个附件的最后一行是「使用说明」，不是数据行**——解析脚本已按「序号为纯数字」过滤，直接读 xlsx 时要注意。
4. 附件 1 的 `使用说明` 10 条是**规范性规则**（联检折扣、数据上传减收、参考区间减收等），不在 `test_item.csv` 里，已摘录进 [03 文档](../03-政策追踪-2026检验类立项指南与上海集采.md)。

## 更新方式（政策迭代时）

1. 找到新的政策页面（立项指南按「成熟一批、发布一批」推进，后续会有修订或新批次）。
2. 下载页面与 xlsx 附件，**带 referer**：
   ```bash
   curl -sL -A "Mozilla/5.0 ..." "<文章页URL>" -o page.html
   curl -sL -A "Mozilla/5.0 ..." -e "<文章页URL>" \
        "http://www.nhsa.gov.cn/module/download/downfile.jsp?classid=0&filename=<hash>.xlsx" -o att.xlsx
   ```
   附件地址写在页面 `<meta name="Image" content="...">` 中。
3. 存为 `raw/<来源>-<日期>-<说明>.xlsx`，重跑解析脚本，核对行数。

## 抓取注意事项

- **nhsa.gov.cn** 可直接 curl。
- **smpaa.cn** 使用加速乐（jiasule）/ 知道创宇云防御，部分页面返回拦截页或 403。有效做法：带正常浏览器 UA + `-e <参考页>` + **失败重试**（实测重试后多能通过）。
- 上海集采的**中选企业与中选价格清单不在公开网页**，需登录国家医保招采子系统「医药管理－公告管理－公告信息查询」下载——**这份清单目前缺失，是本项目最大的数据缺口**。

## 变更记录

| 日期 | 变更 |
|---|---|
| 2026-10-06 | 初稿：原始文件落盘 + 662 项目与映射表解析为 CSV |
