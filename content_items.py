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

from config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

logger = logging.getLogger(__name__)

SOURCE_GITHUB_DAILY = "GitHub Trending Daily"
SOURCE_GITHUB_WEEKLY = "GitHub Trending Weekly"
SOURCE_HACKER_NEWS = "Hacker News"
SOURCE_LINUX_DO = "Linux.do"
SOURCE_SSPAI = "少数派"
SOURCE_TMTPOST = "钛媒体"
SOURCE_OPENAI = "OpenAI"
SOURCE_ANTHROPIC = "Anthropic"
SOURCE_INFOQ_AI = "InfoQ AI Development"

CATEGORY_OPEN_SOURCE = "开源趋势"
CATEGORY_COMMUNITY = "社区讨论"
CATEGORY_AI_NEWS = "AI 快讯"
CATEGORY_OFFICIAL_AI = "AI 官方更新"
CATEGORY_AI_ENGINEERING = "AI 工程实践"


def make_content_item(source, category, title, url, published_at="", original_summary="",
                      chinese_summary="", backend_focus="", meta=None):
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
        "meta": meta if meta is not None else {},
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

    if not OPENAI_API_KEY:
        logger.warning("未配置 OPENAI_API_KEY，跳过 %s AI 摘要", section_label)
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
        "以下是【{}】官方渠道的最新内容。这些是 AI 厂商一手发布，"
        "读者是后端 / 平台 / AI 工程师，正在评估要不要跟进。\n\n"
        "请为每条生成：\n"
        "- chinese_summary（100-160 字）：\n"
        "  · 第一句先讲这次更新/公告的核心事实（产品名 + 动作 + 关键能力变化）\n"
        "  · 第二句说清楚它相对此前的差异点（新参数、新模型、新能力、新限制）\n"
        "  · 第三句说清楚对已有系统的兼容性影响（旧功能是否被替代、是否需要迁移）\n"
        "- backend_focus（50-80 字）：\n"
        "  · 给后端团队一条具体可执行的事：升级到哪个 API/SDK 版本、修改哪个配置、"
        "    删除哪段兼容代码、关注哪个 deprecation 时间线\n"
        "  · 如果只是营销/概念发布，直接写「营销大于实质，无需行动」并说明理由\n\n"
        "写作要求：\n"
        "- 区分「真正改变能力/接口的更新」和「产品包装/概念营销」"
        "，后者直说「营销大于实质」\n"
        "- 涉及具体 API/SDK/参数时直接给字段名（如 response_format、Tool Use、"
        "MCP、context window、max_tokens）\n"
        "- 涉及模型版本号直接照抄（如 Claude Opus 4.5、GPT-5.4、GLM-5.2）\n"
        "- 涉及定价/限流/区域可用性变化必须写出来\n"
        "- 如果内容跟工程无关（纯品牌故事、招聘、公益），"
        "chinese_summary 写「与后端工程无关」，backend_focus 写「无」\n\n"
        "范例：\n"
        '{{"index": 1, "chinese_summary": "OpenAI 正式发布 Structured Outputs，'
        'Chat Completions 接口新增 strict 模式，能保证返回内容严格符合调用方传入的 JSON Schema，'
        '解决了之前 function calling 偶尔格式跑偏的问题。这是 JSON 模式从「软约束」升级为「硬约束」，'
        '调用方可以移除客户端的格式容错逻辑。"'
        ', "backend_focus": "升级方式：请求体加 response_format 字段并设 strict=true。'
        '依赖重试兜底的服务可以下线那段 retry 逻辑。预计 6 个月内旧模式被标记 deprecated。"}}\n\n'
        "请严格按以下 JSON 格式返回，不要包含 markdown 代码块或任何多余文字：\n"
        '{{"summaries": [{{"index": 1, "chinese_summary": "...", "backend_focus": "..."}}, ...]}}\n\n'
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


def build_all_content_items(daily_repos, weekly_repos, hn_stories, sspai_items, tmtpost_items, ai_source_items, linux_do_items=None):
    """将多个来源数据适配为统一 JSON 信息项。"""
    items = []
    items.extend(_github_to_items(daily_repos, SOURCE_GITHUB_DAILY, "每日热点"))
    items.extend(_github_to_items(weekly_repos, SOURCE_GITHUB_WEEKLY, "每周热点"))
    items.extend(_hn_to_items(hn_stories))
    items.extend(_linux_do_to_items(linux_do_items))
    items.extend(_sspai_to_items(sspai_items))
    items.extend(_tmtpost_to_items(tmtpost_items))
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
        meta = {
            "language": repo.get("language") or "",
            "stars": repo.get("stars", 0),
            "forks": repo.get("forks", 0),
            "stars_period": repo.get("stars_period", ""),
        }
        items.append(make_content_item(
            source=source,
            category="{}-{}".format(CATEGORY_OPEN_SOURCE, category_suffix),
            title=repo.get("full_name", ""),
            url=repo.get("url", ""),
            original_summary=original_summary,
            chinese_summary=summary,
            backend_focus=repo.get("backend_focus") or summary,
            meta=meta,
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
        meta = {
            "score": story.get("score", 0),
            "comments": story.get("descendants", 0),
            "hn_url": hn_url,
        }
        items.append(make_content_item(
            source=SOURCE_HACKER_NEWS,
            category=CATEGORY_COMMUNITY,
            title=story.get("title", ""),
            url=url,
            published_at=str(story.get("time", "")),
            original_summary=original_summary,
            chinese_summary=summary,
            backend_focus=summary,
            meta=meta,
        ))
    return items


def _linux_do_to_items(linux_do_items):
    items = []
    for item in linux_do_items or []:
        section_title = item.get("section_title", "")
        section_summary = item.get("section_summary", "")
        reply_count = item.get("reply_count", 0)
        original_summary = "分组: {} | 回复数: {} | {}".format(
            section_title,
            reply_count,
            section_summary,
        )
        summary = item.get("ai_summary") or section_summary
        meta = {
            "reply_count": reply_count,
            "section_title": section_title,
            "daily_url": item.get("daily_url", ""),
            "daily_title": item.get("daily_title", ""),
            "daily_headline": item.get("daily_headline", ""),
        }
        items.append(make_content_item(
            source=SOURCE_LINUX_DO,
            category=CATEGORY_COMMUNITY,
            title=item.get("title", ""),
            url=item.get("url", ""),
            published_at=item.get("published_at", ""),
            original_summary=original_summary,
            chinese_summary=summary,
            backend_focus=item.get("backend_focus") or summary,
            meta=meta,
        ))
    return items


def _sspai_to_items(items):
    items_out = []
    for item in items or []:
        chinese_summary = item.get("chinese_summary", "")
        backend_focus = item.get("backend_focus", "")
        meta = {
            "feed_url": item.get("url", ""),
        }
        items_out.append(make_content_item(
            source=SOURCE_SSPAI,
            category=CATEGORY_AI_NEWS,
            title=item.get("title", ""),
            url=item.get("url", ""),
            published_at=item.get("published_at", ""),
            original_summary=item.get("summary", ""),
            chinese_summary=chinese_summary,
            backend_focus=backend_focus,
            meta=meta,
        ))
    return items_out


def _tmtpost_to_items(items):
    items_out = []
    for item in items or []:
        chinese_summary = item.get("chinese_summary", "")
        backend_focus = item.get("backend_focus", "")
        meta = {}
        if item.get("author"):
            meta["author"] = item["author"]
        if item.get("category"):
            meta["category_raw"] = item["category"]
        items_out.append(make_content_item(
            source=SOURCE_TMTPOST,
            category=CATEGORY_AI_NEWS,
            title=item.get("title", ""),
            url=item.get("url", ""),
            published_at=item.get("published_at", ""),
            original_summary=item.get("summary", ""),
            chinese_summary=chinese_summary,
            backend_focus=backend_focus,
            meta=meta,
        ))
    return items_out


def _call_content_ai_api(prompt, max_retries=10):
    """调用 OpenAI 兼容接口进行统一内容摘要。"""
    headers = {
        "Authorization": "Bearer {}".format(OPENAI_API_KEY),
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是一个关注 AI 基础设施动态的后端架构师。"
                           "你帮团队判断哪些官方更新会影响现有系统，哪些是营销噪音。"
                           "请始终返回有效 JSON。",
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
                "{}/chat/completions".format(OPENAI_BASE_URL),
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
