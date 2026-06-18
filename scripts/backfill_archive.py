# -*- coding: utf-8 -*-
"""
补全归档目录中带「AI 摘要/总结生成失败」占位文案的条目。

扫描 output/<source>/<date>/<batch>.json，对 items 数组中 chinese_summary /
backend_focus / ai_summary 含失败占位的项调用 content_items.summarize_content_items
重新生成中文摘要，写回原文件并保留原 generated_at。

设计要点：
- 按 source 维度分批调用，每个 source 一次 AI 请求，避免单次 prompt 过大。
- 调用前清空失败占位，让 summarize_content_items 覆盖回新值。
- 写文件时同时更新 generated_at 为当前时间，并保留原 source 元数据。
- 每个文件在第一次写回前备份为 *.bak，出错可恢复。
- 失败的源/批次原样保留，下次再补。
"""

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"

sys.path.insert(0, str(ROOT))

FAIL_PATTERNS = (
    "（AI 摘要生成失败）",
    "（AI 总结生成失败）",
    "（AI 后端关注点生成失败）",
)

SUMMARY_FIELDS = ("chinese_summary", "ai_summary")
BACKEND_FIELDS = ("backend_focus",)


def _is_failed(value):
    if not value:
        return True
    return any(p in value for p in FAIL_PATTERNS)


def _strip_failed(value):
    if not value:
        return ""
    out = value
    for p in FAIL_PATTERNS:
        out = out.replace(p, "")
    return out.strip()


def _item_needs_backfill(item):
    for f in SUMMARY_FIELDS:
        if f in item and _is_failed(item.get(f, "")):
            return True
    for f in BACKEND_FIELDS:
        if f in item and _is_failed(item.get(f, "")):
            return True
    return False


def _scan_files():
    """列出所有需要补全的归档 JSON 文件。"""
    targets = []
    for jp in sorted(OUTPUT_DIR.rglob("*.json")):
        if jp.name == "latest.json":
            continue
        try:
            data = json.loads(jp.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[跳过] 解析失败 {jp}: {e}", file=sys.stderr)
            continue
        items = data.get("items") or []
        failed_items = [x for x in items if _item_needs_backfill(x)]
        if failed_items:
            targets.append((jp, data, failed_items))
    return targets


def _ensure_env(require_key=True):
    os.environ.setdefault("OPENAI_BASE_URL", "https://api.agently.top/v1")
    os.environ.setdefault("OPENAI_MODEL", "MiniMax-M3")
    if require_key and not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("缺少 OPENAI_API_KEY 环境变量")


def _summarize_group(items):
    """对一组 item 调用 AI 摘要。先清空失败占位。"""
    from content_items import summarize_content_items

    cleaned = []
    for it in items:
        new_it = dict(it)
        for f in SUMMARY_FIELDS:
            if f in new_it and _is_failed(new_it.get(f, "")):
                new_it[f] = ""
        for f in BACKEND_FIELDS:
            if f in new_it and _is_failed(new_it.get(f, "")):
                new_it[f] = ""
        cleaned.append(new_it)

    section_label = cleaned[0].get("source", "归档补全") if cleaned else "归档补全"
    summarize_content_items(cleaned, section_label=section_label)

    for orig, new in zip(items, cleaned):
        for f in SUMMARY_FIELDS:
            if f in orig and new.get(f):
                orig[f] = new[f]
        for f in BACKEND_FIELDS:
            if f in orig and new.get(f):
                orig[f] = new[f]


def _write_back(jp, data, failed_items):
    """调用 AI 后把新结果写回原文件。第一次写之前备份 .bak。"""
    items = data.get("items") or []
    targets = [x for x in items if _item_needs_backfill(x)]
    if not targets:
        return 0

    bak = jp.with_suffix(jp.suffix + ".bak")
    if not bak.exists():
        shutil.copy2(jp, bak)

    _summarize_group(targets)

    data["items"] = items
    data["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    if "item_count" in data:
        data["item_count"] = len(items)

    with open(jp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return len(targets)


def main(dry_run=False):
    _ensure_env(require_key=not dry_run)
    targets = _scan_files()
    print(f"扫描完成，需补全 {len(targets)} 个文件")

    total_items = 0
    total_fixed = 0
    failures = []

    for idx, (jp, data, failed_items) in enumerate(targets, 1):
        rel = jp.relative_to(OUTPUT_DIR)
        n = len(failed_items)
        total_items += n
        print(f"[{idx}/{len(targets)}] {rel}  待补 {n} 条 ... ", end="", flush=True)
        if dry_run:
            print("(dry-run)")
            continue
        try:
            fixed = _write_back(jp, data, failed_items)
            total_fixed += fixed
            print(f"OK, 补 {fixed} 条")
        except Exception as e:
            failures.append((rel, str(e)))
            print(f"FAIL: {e}")

    print()
    print(f"汇总: 计划补 {total_items} 条，实际补 {total_fixed} 条，失败批次 {len(failures)}")
    for rel, err in failures:
        print(f"  - {rel}: {err}")
    return 0 if not failures else 1


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    sys.exit(main(dry_run=dry))