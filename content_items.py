# -*- coding: utf-8 -*-
"""
统一信息项模型、AI 摘要和 JSON 输出。
"""

import json
import logging
import os
import re
import time
from datetime import datetime

import requests

from config import AI_API_URL, AI_MODEL, GITHUB_TOKEN

logger = logging.getLogger(__name__)

SOURCE_GITHUB_DAILY = "GitHub Trending Daily"
SOURCE_GITHUB_WEEKLY = "GitHub Trending Weekly"
SOURCE_HACKER_NEWS = "Hacker News"
SOURCE_TLDR_AI = "TLDR AI"
SOURCE_OPENAI = "OpenAI"
SOURCE_ANTHROPIC = "Anthropic"
SOURCE_INFOQ_AI = "InfoQ AI Development"

CATEGORY_OPEN_SOURCE = "开源趋势"
CATEGORY_COMMUNITY = "社区讨论"
CATEGORY_AI_NEWS = "AI 快讯"
CATEGORY_OFFICIAL_AI = "AI 官方更新"
CATEGORY_AI_ENGINEERING = "AI 工程实践"


def make_content_item(source, category, title, url, published_at="", original_summary="",
                      chinese_summary="", backend_focus=""):
    """创建统一信息项。"""
    return {
        "source": source or "",
        "category": category or "",
        "title": title or "",
        "url": url or "",
        "published_at": published_at or "",
        "original_summary": original_summary or "",
        "chinese_summary": chinese_summary or "",
        "backend_focus": backend_focus or "",
    }


def summarize_content_items(items, section_label):
    """
    为统一信息项生成中文摘要和后端关注点。

    Args:
        items: 统一信息项列表
        section_label: 摘要场景说明

    Returns:
        list[dict]: 增强后的统一信息项
    """
    if not items:
        return items

    if not GITHUB_TOKEN:
        logger.warning("未配置 GITHUB_TOKEN，跳过 %s AI 摘要", section_label)
        for item in items:
            item["chinese_summary"] = "（未配置 AI Token，无法生成中文摘要）{}".format(
                item.get("original_summary", "")
            )
            item["backend_focus"] = "（未配置 AI Token，无法生成后端关注点）"
        return items

    item_lines = []
    for i, item in enumerate(items, 1):
        item_lines.append(
            "{}. 来源: {}\n   分类: {}\n   标题: {}\n   链接: {}\n   发布时间: {}\n   原文摘要: {}".format(
                i,
                item.get("source", ""),
                item.get("category", ""),
                item.get("title", ""),
                item.get("url", ""),
                item.get("published_at", ""),
                item.get("original_summary", ""),
            )
        )

    prompt = (
        "你是一个面向后端开发工程师的 AI 技术信息分析助手。\n"
        "以下是{}内容。请为每条生成中文摘要和后端工程师关注点。\n"
        "中文摘要 2-3 句，说明发生了什么和为什么重要；后端关注点 1-2 句，说明工程影响或可行动启发。\n\n"
        "请严格按照以下 JSON 格式返回，不要包含任何多余内容：\n"
        '{{"summaries": [{{"index": 1, "chinese_summary": "中文摘要", "backend_focus": "后端关注点"}}, ...]}}\n\n'
        "内容列表：\n{}"
    ).format(section_label, "\n\n".join(item_lines))

    summaries = _call_content_ai_api(prompt)
    if summaries:
        for summary in summaries:
            idx = summary.get("index", 0) - 1
            if 0 <= idx < len(items):
                items[idx]["chinese_summary"] = summary.get("chinese_summary", "")
                items[idx]["backend_focus"] = summary.get("backend_focus", "")

    for item in items:
        if not item.get("chinese_summary"):
            item["chinese_summary"] = "（AI 摘要生成失败）{}".format(
                item.get("original_summary", "")
            )
        if not item.get("backend_focus"):
            item["backend_focus"] = "（AI 后端关注点生成失败）"

    return items


def build_all_content_items(daily_repos, weekly_repos, hn_stories, tldr_items, ai_source_items):
    """将 6 个来源数据适配为统一 JSON 信息项。"""
    items = []
    items.extend(_github_to_items(daily_repos, SOURCE_GITHUB_DAILY, "每日热点"))
    items.extend(_github_to_items(weekly_repos, SOURCE_GITHUB_WEEKLY, "每周热点"))
    items.extend(_hn_to_items(hn_stories))
    items.extend(_tldr_to_items(tldr_items))
    items.extend(ai_source_items or [])
    return items


def write_content_json(items, output_path):
    """写出统一 JSON 文件。"""
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    payload = {
        "generated_at": datetime.now().isoformat(),
        "item_count": len(items),
        "items": items,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info("统一 JSON 已写出: %s (%d items)", output_path, len(items))


def _github_to_items(repos, source, category_suffix):
    items = []
    for repo in repos or []:
        summary = repo.get("ai_summary", "")
        original_summary = "{} | 语言: {} | Stars: {:,} | Forks: {:,} | {}".format(
            repo.get("description", ""),
            repo.get("language") or "N/A",
            repo.get("stars", 0),
            repo.get("forks", 0),
            repo.get("stars_period", ""),
        )
        items.append(make_content_item(
            source=source,
            category="{}-{}".format(CATEGORY_OPEN_SOURCE, category_suffix),
            title=repo.get("full_name", ""),
            url=repo.get("url", ""),
            original_summary=original_summary,
            chinese_summary=summary,
            backend_focus=summary,
        ))
    return items


def _hn_to_items(stories):
    items = []
    for story in stories or []:
        hn_url = "https://news.ycombinator.com/item?id={}".format(story.get("id", ""))
        url = story.get("url") or hn_url
        original_summary = "分数: {} | 评论数: {} | 作者: {}".format(
            story.get("score", 0),
            story.get("descendants", 0),
            story.get("by", ""),
        )
        summary = story.get("ai_summary", "")
        items.append(make_content_item(
            source=SOURCE_HACKER_NEWS,
            category=CATEGORY_COMMUNITY,
            title=story.get("title", ""),
            url=url,
            published_at=str(story.get("time", "")),
            original_summary=original_summary,
            chinese_summary=summary,
            backend_focus=summary,
        ))
    return items


def _tldr_to_items(tldr_items):
    items = []
    for item in tldr_items or []:
        summary = item.get("ai_summary") or item.get("summary", "")
        items.append(make_content_item(
            source=SOURCE_TLDR_AI,
            category=item.get("category") or CATEGORY_AI_NEWS,
            title=item.get("title", ""),
            url=item.get("url", ""),
            original_summary=item.get("summary", ""),
            chinese_summary=summary,
            backend_focus=summary,
        ))
    return items


def _call_content_ai_api(prompt, max_retries=10):
    """调用 GitHub Models API 进行统一内容摘要。"""
    headers = {
        "Authorization": "Bearer {}".format(GITHUB_TOKEN),
        "Content-Type": "application/json",
    }
    payload = {
        "model": AI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是专业的 AI 后端技术信息分析助手，请始终返回有效 JSON。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 6000,
    }

    for attempt in range(max_retries):
        try:
            logger.info("调用 AI API 进行统一内容摘要 (第 %d 次尝试)...", attempt + 1)
            resp = requests.post(
                "{}/chat/completions".format(AI_API_URL),
                headers=headers,
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            return json.loads(content).get("summaries", [])
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status == 429:
                wait = 60 * (attempt + 1)
                logger.warning("统一摘要 API 限流，等待 %d 秒后重试...", wait)
                time.sleep(wait)
            elif attempt < max_retries - 1:
                logger.error("统一摘要 AI API HTTP 错误 %d: %s", status, e)
                time.sleep(10)
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error("解析统一摘要 AI 响应失败: %s", e)
            if attempt < max_retries - 1:
                time.sleep(5)
        except Exception as e:
            logger.error("统一摘要 AI API 调用异常: %s", e)
            if attempt < max_retries - 1:
                time.sleep(10)

    return []
