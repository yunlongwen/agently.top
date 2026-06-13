# -*- coding: utf-8 -*-
"""
公开只读 FastAPI。

Nginx 可将 /api/ 反代到本服务，Vue 前端只读取最新来源快照。
"""

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from access_log import AccessLogMiddleware, start_stats_reporter
from config import API_CORS_ORIGINS, API_MAX_ITEMS_PER_SOURCE
from content_store import (
    is_valid_history_date,
    list_recent_history_dates,
    load_history_archive_snapshot,
    load_latest_snapshot,
)
from scheduler import start_scheduler, stop_scheduler
from source_registry import SOURCE_DEFINITIONS, get_source_by_id
from logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="GitHub Trending Spider API")

# 访问日志中间件（记录每次请求的 IP、路径、耗时等）
app.add_middleware(AccessLogMiddleware)

if API_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            item.strip()
            for item in API_CORS_ORIGINS.split(",")
            if item.strip()
        ],
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )


@app.on_event("startup")
def on_startup():
    """API 启动时启动内置采集调度和统计报告。"""
    start_scheduler()
    start_stats_reporter()
    logger.info("[启动] API 服务已启动，访问日志和每小时统计已开启")


@app.on_event("shutdown")
def on_shutdown():
    """API 关闭时停止内置采集调度。"""
    stop_scheduler()
    logger.info("[关闭] API 服务已停止")


@app.get("/api/health")
def health_check():
    """健康检查。"""
    return {"status": "ok"}


@app.get("/api/sources")
def list_sources():
    """返回前端可展示的全部来源。"""
    logger.info("[数据] 请求来源列表 | 注册来源数=%d", len(SOURCE_DEFINITIONS))
    return {
        "sources": SOURCE_DEFINITIONS,
        "count": len(SOURCE_DEFINITIONS),
    }


@app.get("/api/history/dates")
def list_history_dates():
    """返回最近 7 天历史归档日期，不包含今天。"""
    dates = list_recent_history_dates(days=7)
    logger.info("[数据] 请求历史归档日期 | 日期数=%d", len(dates))
    return {
        "dates": dates,
        "count": len(dates),
    }


@app.get("/api/history/sources/{source_id}/dates/{date_text}")
def get_history_source(source_id, date_text):
    """返回指定日期、指定来源的历史归档快照。"""
    source = get_source_by_id(source_id)
    if not source:
        logger.warning("[数据] 请求了未知历史来源 | source_id=%s", source_id)
        raise HTTPException(status_code=404, detail="Unknown source")
    if not is_valid_history_date(date_text):
        logger.warning("[数据] 请求了非法历史日期 | date=%s", date_text)
        raise HTTPException(status_code=400, detail="Invalid date")

    snapshot, served_from, batch_file = load_history_archive_snapshot(source_id, date_text)
    if not snapshot:
        logger.info(
            "[数据] 历史来源=%s | 日期=%s | 读取自=无归档 | 条数=0",
            source_id, date_text,
        )
        return {
            "served_from": served_from,
            "batch_file": batch_file,
            "generated_at": "",
            "source": source,
            "item_count": 0,
            "items": [],
        }

    items = snapshot.get("items", [])[:API_MAX_ITEMS_PER_SOURCE]
    generated_at = snapshot.get("generated_at", "未知时间")
    logger.info(
        "[数据] 历史来源=%s | 日期=%s | 批次=%s | 条数=%d | 数据生成时间=%s",
        source_id, date_text, batch_file, len(items), generated_at,
    )
    return {
        "served_from": served_from,
        "batch_file": batch_file,
        "generated_at": generated_at,
        "source": snapshot.get("source", source),
        "item_count": len(items),
        "total_item_count": snapshot.get("item_count", len(items)),
        "items": items,
    }


@app.get("/api/sources/{source_id}/latest")
def get_latest_source(source_id):
    """返回单来源最新快照。"""
    source = get_source_by_id(source_id)
    if not source:
        logger.warning("[数据] 请求了未知来源 | source_id=%s", source_id)
        raise HTTPException(status_code=404, detail="Unknown source")

    snapshot, served_from = load_latest_snapshot(source_id)

    # 数据来源追踪日志（中文）
    if not snapshot:
        logger.info(
            "[数据] 来源=%s | 读取自=无数据 | 条数=0 | 说明=该来源暂无可用快照",
            source_id,
        )
        return {
            "served_from": served_from,
            "generated_at": "",
            "source": source,
            "item_count": 0,
            "items": [],
        }

    items = snapshot.get("items", [])[:API_MAX_ITEMS_PER_SOURCE]
    generated_at = snapshot.get("generated_at", "未知时间")

    # 根据数据来源输出不同中文提示
    if served_from == "redis":
        logger.info(
            "[数据] 来源=%s | 读取自=Redis缓存 | 条数=%d | 数据生成时间=%s",
            source_id, len(items), generated_at,
        )
    elif served_from == "archive":
        logger.info(
            "[数据] 来源=%s | 读取自=磁盘归档 | 条数=%d | 数据生成时间=%s | 说明=Redis不可用已降级到磁盘",
            source_id, len(items), generated_at,
        )
    else:
        logger.info(
            "[数据] 来源=%s | 读取自=%s | 条数=%d | 数据生成时间=%s",
            source_id, served_from, len(items), generated_at,
        )

    return {
        "served_from": served_from,
        "generated_at": generated_at,
        "source": snapshot.get("source", source),
        "item_count": len(items),
        "total_item_count": snapshot.get("item_count", len(items)),
        "items": items,
    }
