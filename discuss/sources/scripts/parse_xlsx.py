#!/usr/bin/env python3
"""解析国家医保局《检验类医疗服务价格项目立项指南（试行）》的两个 xlsx 附件。

背景
----
来源: https://www.nhsa.gov.cn/art/2026/8/14/art_14_21766.html (2026-08-14)
附件1: 检验类医疗服务价格项目立项指南（试行）      -> 662 个主项目
附件2: 检验类医疗服务价格项目立项指南映射关系表    -> 新项目 <-> 旧编码 的官方映射

用法
----
    python3 parse_xlsx.py <附件1.xlsx> <附件2.xlsx> <输出目录>

输出
----
    test_item.csv           662 个主项目（忠实于附件 1）
    test_item_code_map.csv  官方编码映射（附件 2）

实现说明
--------
* xlsx 本质是 zip，直接读 xl/worksheets/sheet1.xml 即可，无需第三方库。
* 本文件的字符串是 inlineStr 内联形式，**没有** xl/sharedStrings.xml；脚本对
  两种情况都做了兼容。
* 附件 1 前 3 行是标题与表头，附件 2 前 5 行是标题、说明与双层表头；
  两个附件的**最后一行是「使用说明」，不是数据行**，需按序号为纯数字来过滤。
* 附件 2 的编码单元格里用空白分隔多个编码，对应的名称单元格也按同一顺序排列。
  实测 662 行中有 4 行（NHSA 列）/ 3 行（NHC 列）两侧数量不等，通常是名称
  本身含空格所致。此类行不强行配对，而是标记 align_ok=FALSE 并原样保留，
  交由人工核对，避免制造错误数据。
"""

import csv
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

# 附件 1：表头在第 3 行（0-based 索引 2），数据从索引 3 开始
ATT1_HEADER_ROW = 2
# 附件 2：表头占第 3-4 行（0-based 索引 2、3），数据从索引 5 开始
ATT2_DATA_START = 5

CODE_SYSTEM = {
    'G': 'NHSA_MEDICAL',   # 医保医疗服务项目分类与代码（项目编码）
    'I': 'NHC_2023',       # 国家卫健委 2023 版技术规范（项目编码）
}


def read_xlsx(path):
    """把一个 worksheet 读成 [{列名: 值}]，列名为 A/B/C...（丢弃公式、只取值）。"""
    with zipfile.ZipFile(path) as z:
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            root = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in root.findall(NS + 'si'):
                shared.append(''.join(t.text or '' for t in si.iter(NS + 't')))

        root = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        rows = []
        for row in root.iter(NS + 'row'):
            cells = {}
            for c in row.findall(NS + 'c'):
                ref = c.get('r') or ''
                m = re.match(r'[A-Z]+', ref)
                col = m.group(0) if m else ''
                if not col:
                    continue
                t = c.get('t')
                v = c.find(NS + 'v')
                isel = c.find(NS + 'is')
                if t == 'inlineStr' and isel is not None:
                    val = ''.join(x.text or '' for x in isel.iter(NS + 't'))
                elif t == 's' and v is not None:
                    val = shared[int(v.text)]
                elif v is not None:
                    val = v.text
                else:
                    val = ''
                # 单元格内换行会破坏 CSV 可读性，统一压成空格
                cells[col] = re.sub(r'\s+', ' ', (val or '')).strip()
            rows.append(cells)
        return rows


def is_data_row(r):
    """只保留序号为纯数字的行（排除「使用说明」等尾部说明行）。"""
    return r.get('A', '').strip().isdigit()


def pair_codes(codes_raw, names_raw):
    """把编码串与名称串按空白配对。

    返回 (pairs, align_ok)。两侧数量不一致时不强行配对：
    整串作为单条记录保留，并标记 align_ok=False 供人工核对。
    """
    codes = codes_raw.split()
    names = names_raw.split()
    if not codes and not names:
        return [], True
    if len(codes) == len(names):
        return list(zip(codes, names)), True
    # 无法可靠配对：原样保留，交由人工处理
    return [(codes_raw, names_raw)], False


def parse_att1(path, outdir):
    rows = read_xlsx(path)
    data = [r for r in rows[ATT1_HEADER_ROW + 1:] if is_data_row(r)]
    out = os.path.join(outdir, 'test_item.csv')
    with open(out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['item_seq', 'item_name', 'service_output', 'price_composition',
                    'surcharge_items', 'extension_items', 'unit', 'pricing_note'])
        for r in data:
            w.writerow([r.get('A', ''), r.get('B', ''), r.get('C', ''), r.get('D', ''),
                        r.get('E', ''), r.get('F', ''), r.get('G', ''), r.get('H', '')])
    return len(data)


def parse_att2(path, outdir):
    rows = read_xlsx(path)
    data = [r for r in rows[ATT2_DATA_START:] if is_data_row(r)]
    out = os.path.join(outdir, 'test_item_code_map.csv')
    n_rows = n_mismatch = 0
    with open(out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['item_seq', 'item_name', 'code_system', 'code',
                    'code_item_name', 'align_ok'])
        for r in data:
            n_rows += 1
            seq, name = r.get('A', ''), r.get('B', '')
            for code_col, name_col in (('G', 'H'), ('I', 'J')):
                pairs, ok = pair_codes(r.get(code_col, ''), r.get(name_col, ''))
                if not ok:
                    n_mismatch += 1
                for code, cname in pairs:
                    if not code and not cname:
                        continue
                    w.writerow([seq, name, CODE_SYSTEM[code_col], code, cname, ok])
    return len(data), n_mismatch


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    att1, att2, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(outdir, exist_ok=True)

    n1 = parse_att1(att1, outdir)
    print(f'test_item.csv          : {n1} 行')

    n2, mism = parse_att2(att2, outdir)
    print(f'test_item_code_map.csv : {n2} 个主项目，{mism} 处编码/名称数量不匹配（已标记 align_ok=FALSE）')

    if n1 != 662:
        print(f'⚠ 附件 1 期望 662 个主项目，实际解析 {n1} 个，请核对。', file=sys.stderr)


if __name__ == '__main__':
    main()
