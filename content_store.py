# -*- coding: utf-8 -*-
"""
按来源持久化统一信息项，并为 API 提供 Redis + 磁盘降级读取。
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from config import (
    OUTPUT_ARCHIVE_DIR,
    REDIS_KEY_PREFIX,
    REDIS_SNAPSHOT_TTL_SECONDS,
)
from redis_client import get_redis_client
from source_registry import (
    SOURCE_DEFINITIONS,
    get_source_by_content_source,
    get_source_by_id,
)

logger = logging.getLogger(__name__)


def build_source_snapshots(items, generated_at=None):
    """将统一信息项按来源拆成快照 payload。"""
    if generated_at is None:
        generated_at = datetime.now().isoformat()

    grouped = {}
    for item in items or []:
        source = get_source_by_content_source(item.get("source", ""))
        if not source:
            logger.warning("跳过未注册来源: %s", item.get("source", ""))
            continue
        grouped.setdefault(source["id"], []).append(item)

    snapshots = {}
    for source in SOURCE_DEFINITIONS:
        source_items = grouped.get(source["id"], [])
        if not source_items:
            continue
        snapshots[source["id"]] = {
            "generated_at": generated_at,
            "source": source,
            "item_count": len(source_items),
            "items": source_items,
        }
    return snapshots


def persist_source_snapshots(items, output_dir=OUTPUT_ARCHIVE_DIR):
    """按来源写磁盘归档，并尽力写入 Redis。"""
    snapshots = build_source_snapshots(items)
    archive_paths = {}
    redis_written = []
    redis_errors = []

    redis_client = get_redis_client()
    for source_id, snapshot in snapshots.items():
        archive_paths[source_id] = write_archive_snapshot(
            source_id,
            snapshot,
            output_dir,
        )
        if redis_client:
            try:
                write_redis_snapshot(redis_client, source_id, snapshot)
                redis_written.append(source_id)
            except Exception as e:
                redis_errors.append("{}: {}".format(source_id, e))
                logger.warning("写入 Redis 失败: %s", e)

    return {
        "snapshot_count": len(snapshots),
        "archive_paths": archive_paths,
        "redis_written": redis_written,
        "redis_errors": redis_errors,
    }


def write_archive_snapshot(source_id, snapshot, output_dir=OUTPUT_ARCHIVE_DIR):
    """写入 output/<source>/<YYYY-MM-DD>/<batch>.json。"""
    generated_at = snapshot.get("generated_at") or datetime.now().isoformat()
    date_text = generated_at[:10]
    target_dir = Path(output_dir) / source_id / date_text
    target_dir.mkdir(parents=True, exist_ok=True)

    batch_no = _next_batch_number(target_dir)
    output_path = target_dir / "{:02d}.json".format(batch_no)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    logger.info("来源归档已写出: %s", output_path)
    return str(output_path)


def write_redis_snapshot(redis_client, source_id, snapshot):
    """写入单来源最新快照到 Redis。"""
    key = _redis_key(source_id)
    redis_client.setex(
        key,
        REDIS_SNAPSHOT_TTL_SECONDS,
        json.dumps(snapshot, ensure_ascii=False),
    )
    logger.info("来源快照已写入 Redis: %s", key)


def load_latest_snapshot(source_id, output_dir=OUTPUT_ARCHIVE_DIR):
    """读取单来源最新快照，优先 Redis，失败后读磁盘最新批次。"""
    source = get_source_by_id(source_id)
    if not source:
        return None, "unknown"

    redis_client = get_redis_client()
    if redis_client:
        try:
            snapshot = load_redis_snapshot(redis_client, source_id)
            if snapshot:
                return snapshot, "redis"
        except Exception as e:
            logger.warning("读取 Redis 失败，降级到磁盘: %s", e)

    snapshot = load_latest_archive_snapshot(source_id, output_dir)
    if snapshot:
        return snapshot, "archive"
    return None, "empty"


def load_redis_snapshot(redis_client, source_id):
    """从 Redis 读取单来源最新快照。"""
    raw_value = redis_client.get(_redis_key(source_id))
    if not raw_value:
        return None
    if isinstance(raw_value, bytes):
        raw_value = raw_value.decode("utf-8")
    return json.loads(raw_value)


def load_latest_archive_snapshot(source_id, output_dir=OUTPUT_ARCHIVE_DIR):
    """从磁盘归档读取单来源最新批次。"""
    source_dir = Path(output_dir) / source_id
    if not source_dir.exists():
        return None

    date_dirs = [
        path for path in source_dir.iterdir()
        if path.is_dir()
    ]
    for date_dir in sorted(date_dirs, reverse=True):
        files = [
            path for path in date_dir.glob("*.json")
            if path.stem.isdigit()
        ]
        if not files:
            continue
        latest_file = sorted(files, key=lambda item: int(item.stem))[-1]
        with latest_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _next_batch_number(target_dir):
    numbers = []
    for path in target_dir.glob("*.json"):
        if path.stem.isdigit():
            numbers.append(int(path.stem))
    if not numbers:
        return 1
    return max(numbers) + 1


def _redis_key(source_id):
    return "{}:source:{}:latest".format(REDIS_KEY_PREFIX, source_id)
