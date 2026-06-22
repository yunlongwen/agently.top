#!/usr/bin/env python3
"""
清理 output/ 下的「与工程无关」条目。

供过滤规则上线后立刻清理已写入磁盘的 latest.json 和归档目录；
后续采集由 build_all_content_items 在源头过滤，无需再跑这个脚本。

用法：
  python3 scripts/cleanup_irrelevant.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.content_items import _is_irrelevant_item


def _filter_file(path: Path) -> tuple[int, int]:
    """过滤单个 JSON 文件，返回 (处理前条数, 处理后条数)。"""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items", [])
    before = len(items)
    kept = [i for i in items if not _is_irrelevant_item(i)]
    after = len(kept)
    if after == before:
        return before, after
    data["items"] = kept
    data["item_count"] = after
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return before, after


def main():
    output_dir = ROOT / "output"
    if not output_dir.exists():
        print(f"output 目录不存在: {output_dir}")
        return

    total_before = 0
    total_after = 0
    touched = 0

    # 1. latest.json
    latest = output_dir / "latest.json"
    if latest.exists():
        b, a = _filter_file(latest)
        total_before += b
        total_after += a
        if b != a:
            touched += 1
            print(f"  {latest.relative_to(ROOT)}: {b} -> {a} (丢弃 {b - a})")

    # 2. 归档目录
    for source_dir in sorted(output_dir.iterdir()):
        if not source_dir.is_dir():
            continue
        if source_dir.name in ("latest.json", "email_preview.html", "logs"):
            continue
        for json_file in sorted(source_dir.rglob("*.json")):
            b, a = _filter_file(json_file)
            total_before += b
            total_after += a
            if b != a:
                touched += 1
                print(f"  {json_file.relative_to(ROOT)}: {b} -> {a} (丢弃 {b - a})")

    print(f"\n共处理 {touched} 个文件，过滤前 {total_before} 条 -> 过滤后 {total_after} 条 (丢弃 {total_before - total_after})")


if __name__ == "__main__":
    main()