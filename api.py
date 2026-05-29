# -*- coding: utf-8 -*-
"""
公开只读 FastAPI。

Nginx 可将 /api/ 反代到本服务，Vue 前端只读取最新来源快照。
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import API_CORS_ORIGINS, API_MAX_ITEMS_PER_SOURCE
from content_store import load_latest_snapshot
from scheduler import start_scheduler, stop_scheduler
from source_registry import SOURCE_DEFINITIONS, get_source_by_id

app = FastAPI(title="GitHub Trending Spider API")

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
    """API 启动时启动内置采集调度。"""
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    """API 关闭时停止内置采集调度。"""
    stop_scheduler()


@app.get("/api/health")
def health_check():
    """健康检查。"""
    return {"status": "ok"}


@app.get("/api/sources")
def list_sources():
    """返回前端可展示的全部来源。"""
    return {
        "sources": SOURCE_DEFINITIONS,
        "count": len(SOURCE_DEFINITIONS),
    }


@app.get("/api/sources/{source_id}/latest")
def get_latest_source(source_id):
    """返回单来源最新快照。"""
    source = get_source_by_id(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Unknown source")

    snapshot, served_from = load_latest_snapshot(source_id)
    if not snapshot:
        return {
            "served_from": served_from,
            "generated_at": "",
            "source": source,
            "item_count": 0,
            "items": [],
        }

    items = snapshot.get("items", [])[:API_MAX_ITEMS_PER_SOURCE]
    return {
        "served_from": served_from,
        "generated_at": snapshot.get("generated_at", ""),
        "source": snapshot.get("source", source),
        "item_count": len(items),
        "total_item_count": snapshot.get("item_count", len(items)),
        "items": items,
    }
