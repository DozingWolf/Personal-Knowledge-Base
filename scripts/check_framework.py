#!/usr/bin/env python3
"""框架完整性校验：目录约定 / 配置可解析 / 文档围栏与内部链接 / 内核隔离性。

用法：
    python3 scripts/check_framework.py

退出码：0 = 全部通过；1 = 有失败项（逐条打印）。
无第三方依赖（PyYAML 缺失时跳过 YAML 解析，仅告警）。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 框架必需路径（按 docs/00 与 README 的约定）
REQUIRED_PATHS = [
    "README.md",
    "AGENTS.md",
    "pyproject.toml",
    ".python-version",
    ".gitignore",
    "config/config.example.yaml",
    "core/README.md",
    "domains/README.md",
    "domains/ivd/README.md",
    "domains/ivd/registry.yaml",
    "domains/ivd/layer_template.yaml",
    "apps/README.md",
    "docs/README.md",
    "docs/00-文档体系与编写规范.md",
    "docs/decisions/README.md",
    "docs/decisions/0001-kernel-domain-app-layers.md",
    "discuss/README.md",
]

YAML_FILES = [
    "config/config.example.yaml",
    "domains/ivd/registry.yaml",
    "domains/ivd/layer_template.yaml",
]

# 内核不许出现领域字面量（ADR 0001 的硬约束）
KERNEL_DIRS = ["core", "apps"]
DOMAIN_LITERALS = re.compile(r"ivd|nhsa|smpaa|医保|检测项目|集采|注册证", re.IGNORECASE)

FENCE = re.compile(r"^```", re.M)
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

failures: list[str] = []
warnings: list[str] = []


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def check_required_paths() -> None:
    for rp in REQUIRED_PATHS:
        if not (ROOT / rp).exists():
            failures.append(f"缺少必需路径: {rp}")


def check_yaml() -> None:
    try:
        import yaml  # type: ignore
    except ImportError:
        warnings.append("未安装 PyYAML，跳过 YAML 解析（uv add --dev pyyaml）")
        return
    for rp in YAML_FILES:
        path = ROOT / rp
        if not path.exists():
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            failures.append(f"YAML 解析失败: {rp} -> {exc}")
            continue
        if data is None:
            failures.append(f"YAML 为空文件: {rp}")

    # registry 与 layer_template 的结构性契约
    reg_path = ROOT / "domains/ivd/registry.yaml"
    if reg_path.exists():
        reg = yaml.safe_load(reg_path.read_text(encoding="utf-8")) or {}
        for key in ("domain", "ontology", "sources", "code_systems", "review_card"):
            if key not in reg:
                failures.append(f"registry.yaml 缺少顶层键: {key}")
        if reg.get("layer_template") != "layer_template.yaml":
            failures.append("registry.yaml 的 layer_template 应指向 layer_template.yaml")

    lay_path = ROOT / "domains/ivd/layer_template.yaml"
    if lay_path.exists():
        lay = yaml.safe_load(lay_path.read_text(encoding="utf-8")) or {}
        layers = lay.get("layers") or []
        if len(layers) != 6:
            failures.append(f"layer_template.yaml 应为 6 层，实际 {len(layers)}")
        ids = {x.get("id") for x in layers}
        for e in lay.get("edges") or []:
            for side in ("from", "to"):
                if e.get(side) not in ids:
                    failures.append(f"layer_template.yaml 的边引用了未知层: {e.get(side)}")


def check_markdown() -> None:
    for path in sorted(ROOT.rglob("*.md")):
        if any(part.startswith(".") for part in path.relative_to(ROOT).parts):
            continue
        text = path.read_text(encoding="utf-8")
        if len(FENCE.findall(text)) % 2:
            failures.append(f"{rel(path)}: 代码围栏不成对")

        for raw in MD_LINK.findall(text):
            target = raw.strip().split("#")[0]
            if not target or target.startswith(("http://", "https://", "mailto:", "/")):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                failures.append(f"{rel(path)}: 链接目标不存在 -> {target}")


def check_kernel_isolation() -> None:
    for d in KERNEL_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.py")):
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if line.lstrip().startswith("#"):
                    continue
                if DOMAIN_LITERALS.search(line):
                    failures.append(f"内核出现领域字面量: {rel(path)}:{i} -> {line.strip()[:60]}")


def main() -> int:
    check_required_paths()
    check_yaml()
    check_markdown()
    check_kernel_isolation()

    for w in warnings:
        print(f"[warn] {w}")
    if failures:
        print(f"FAIL ({len(failures)})")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"PASS  必需路径 {len(REQUIRED_PATHS)} 项 / YAML {len(YAML_FILES)} 个 / "
          f"Markdown 围栏与内部链接 / 内核隔离性")
    return 0


if __name__ == "__main__":
    sys.exit(main())
