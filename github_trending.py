#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Trending 爬虫 + AI 总结模块

负责爬取 GitHub Trending 每日/每周热点项目，
调用 AI 生成中文总结。
"""

import json
import logging
import re
import sys
import time

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("请先安装依赖: pip3 install requests beautifulsoup4")
    sys.exit(1)

from config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_BASE_URL,
    GITHUB_TRENDING_TOP_COUNT,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
TRENDING_URL = "https://github.com/trending"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


# =========================================================================
# 1. 爬取 GitHub Trending
# =========================================================================
def fetch_trending(since="daily", max_retries=10, count=None):
    """
    爬取 GitHub Trending 页面，返回仓库列表。

    Args:
        since: "daily" 或 "weekly"
        max_retries: 最大重试次数
        count: 获取前 N 个仓库，默认使用 GITHUB_TRENDING_TOP_COUNT 配置

    Returns:
        list[dict]: 每个 dict 包含 repo_name, owner, url, description,
                    language, stars, forks, stars_period
    """
    if count is None:
        count = GITHUB_TRENDING_TOP_COUNT

    url = "{}?since={}".format(TRENDING_URL, since)
    repos = []

    for attempt in range(max_retries):
        try:
            logger.info("正在爬取 %s (第 %d 次尝试)", url, attempt + 1)
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            break
        except requests.RequestException as e:
            logger.warning("请求失败: %s", e)
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
            else:
                logger.error("爬取 %s 失败，已达最大重试次数", url)
                return repos

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = soup.select("article.Box-row")
    logger.info("从 %s 页面解析到 %d 个仓库", since, len(articles))

    for article in articles:
        repo = _parse_article(article, since)
        if repo:
            repos.append(repo)

    # 只保留前 N 个热点仓库；如果页面实际不足 N 个，则返回实际数量
    return repos[:count]


def _parse_article(article, since):
    """解析单个 <article class='Box-row'> 元素。"""
    try:
        # 仓库名 (owner/repo)
        h2 = article.select_one("h2 a")
        if not h2:
            return None
        full_name = h2.get_text(strip=True).replace("\n", "").replace(" ", "")
        # full_name 格式: "owner/repo"
        parts = full_name.split("/")
        owner = parts[0].strip() if len(parts) >= 2 else ""
        repo_name = parts[1].strip() if len(parts) >= 2 else full_name.strip()
        repo_url = "https://github.com" + h2.get("href", "").strip()

        # 描述
        desc_tag = article.select_one("p.col-9")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # 编程语言
        lang_tag = article.select_one("[itemprop='programmingLanguage']")
        language = lang_tag.get_text(strip=True) if lang_tag else ""

        # Stars 总数
        star_link = article.select_one("a[href$='/stargazers']")
        stars = _parse_number(star_link.get_text(strip=True)) if star_link else 0

        # Forks 总数
        fork_link = article.select_one("a[href$='/forks']")
        forks = _parse_number(fork_link.get_text(strip=True)) if fork_link else 0

        # 本期新增 stars
        period_tag = article.select_one("span.d-inline-block.float-sm-right")
        stars_period = ""
        if period_tag:
            stars_period = period_tag.get_text(strip=True)

        return {
            "owner": owner,
            "repo_name": repo_name,
            "full_name": "{}/{}".format(owner, repo_name),
            "url": repo_url,
            "description": description,
            "language": language,
            "stars": stars,
            "forks": forks,
            "stars_period": stars_period,
            "since": since,
        }
    except Exception as e:
        logger.warning("解析 article 失败: %s", e)
        return None


def _parse_number(text):
    """将 '121,933' 这类字符串转为整数。"""
    try:
        return int(text.replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0


# =========================================================================
# 2. AI 总结（GitHub Models API）
# =========================================================================
def ai_summarize(repos, since_label):
    """
    调用 GitHub Models API 对一批仓库列表进行中文总结。

    Args:
        repos: 仓库列表
        since_label: "每日热点" 或 "每周热点"

    Returns:
        list[dict]: 每个 dict 在原有基础上增加 "ai_summary" 字段
    """
    if not repos:
        return repos

    if not OPENAI_API_KEY:
        logger.warning("未配置 OPENAI_API_KEY，跳过 AI 总结")
        for r in repos:
            r["ai_summary"] = "（未配置 AI Token，无法生成总结）"
        return repos

    # 将所有仓库信息一次性发给 AI，减少 API 调用次数
    repo_text_lines = []
    for i, r in enumerate(repos, 1):
        repo_text_lines.append(
            "{}. {} [{}] - Stars: {:,} | Forks: {:,} | 语言: {} | {}\n   描述: {}".format(
                i,
                r["full_name"],
                r["url"],
                r["stars"],
                r["forks"],
                r["language"] or "N/A",
                r["stars_period"],
                r["description"] or "无描述",
            )
        )
    repos_text = "\n".join(repo_text_lines)

    prompt = (
        "以下是 GitHub {} 的热门开源项目。读者是 AI 开发工程师 / 软件开发工程师，"
        "正在找能立刻在生产里用上、或者值得 star 跟进的开源工具。\n\n"
        "请为每个项目写两段输出，字段必须不同，不要把 summary 复制到 backend_focus：\n"
        "- summary（100-160 字）：\n"
        "  · 一句话定位（20 字内）：这东西是什么、给谁用\n"
        "  · 核心能力：用具体的技术特征说明它解决了什么痛点（支持的语言/协议/部署形态）\n"
        "  · 横向对比：跟主流同类方案（如 Milvus/Redis/Prometheus/Faiss/libp2p 等）"
        "比它牛在哪或它的差异化场景（什么场景下应该选它、什么场景下不该选它）\n"
        "  · 上手成本：部署难度、依赖、是否需要改现有架构\n"
        "- backend_focus（50-80 字）：\n"
        "  · 不要重复 summary 内容，直接给一个具体的「团队下一步该做什么」动作清单\n"
        "  · 例：跑哪个命令、装哪个包、配哪条环境变量、改哪个 Dockerfile、"
        "查哪条文档、跑哪个 benchmark 评估替换\n"
        "  · 如果是纯前端/纯客户端工具，backend_focus 写「与开发工作无关」\n\n"
        "禁止事项：\n"
        "- 禁止用「该项目旨在」「本工具致力于」「适合广大开发者」这类官腔\n"
        "- 禁止泛泛说「高性能」「易用」，必须有对比或具体数据（延迟/吞吐/包大小/Memory）\n"
        "- 禁止重复项目描述里已有的信息\n"
        "- 禁止编造 star 数、benchmark 数据，没在描述里看到就不要写\n"
        "- 禁止 summary 和 backend_focus 写相同或高度重叠的内容\n\n"
        "范例：\n"
        '{{"index": 1, '
        '"summary": "Rust 写的嵌入式向量数据库，单二进制 6MB，百万级 embedding 检索 P99 <5ms。'
        '比 Milvus 轻量 10 倍不需要独立部署服务，适合不想搞分布式但又需要语义搜索的 AI 开发 / 软件开发场景；'
        '缺点是单节点写入吞吐有上限，超 500 万向量建议还是上 Qdrant 或 Milvus。'
        '上手成本：cargo install 后写 30 行代码就能用，无外部依赖。", '
        '"backend_focus": "在 staging 跑一次：cargo install lance-db && git clone demo，'
        '用本团队 100 万条真实 embedding 压一遍 P99 延迟和内存，'
        '对比现有 Milvus 集群的 QPS 决定是否替换单点 embedding 检索场景。"}}\n\n'
        "请严格按以下 JSON 格式返回，不要包含 markdown 代码块或任何多余文字：\n"
        '{{"summaries": [{{"index": 1, "summary": "...", "backend_focus": "..."}}, ...]}}\n\n'
        "项目列表：\n{}"
    ).format(since_label, repos_text)

    try:
        summaries = _call_ai_api(prompt)
        if summaries:
            for item in summaries:
                idx = item.get("index", 0) - 1
                if 0 <= idx < len(repos):
                    repos[idx]["ai_summary"] = item.get("summary", "")
                    if item.get("backend_focus"):
                        repos[idx]["backend_focus"] = item.get("backend_focus", "")
    except Exception as e:
        logger.error("AI 总结失败: %s", e)

    # 确保每个 repo 都有 ai_summary 字段
    for r in repos:
        if "ai_summary" not in r:
            r["ai_summary"] = "（AI 总结生成失败）"

    return repos


def _call_ai_api(prompt, max_retries=10):
    """
    调用 OpenAI 兼容接口。

    Returns:
        list[dict] | None: 解析后的 summaries 列表
    """
    headers = {
        "Authorization": "Bearer {}".format(OPENAI_API_KEY),
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是一个资深 AI 开发工程师 / 软件开发工程师，正在给团队同事推荐值得关注的开源项目。"
                           "语气务实、直白，像技术群里聊天。请始终返回有效的 JSON 格式。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 4000,
    }

    for attempt in range(max_retries):
        try:
            logger.info("调用 AI API (第 %d 次尝试)...", attempt + 1)
            resp = requests.post(
                "{}/chat/completions".format(OPENAI_BASE_URL),
                headers=headers,
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()

            content = data["choices"][0]["message"]["content"]
            logger.info("AI 响应长度: %d 字符", len(content))

            # 尝试解析 JSON（处理可能的 markdown 代码块包裹）
            content = content.strip()
            # 用正则提取 JSON 对象，兼容 ```json ... ``` 和多余空行
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            parsed = json.loads(content)
            return parsed.get("summaries", [])

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status == 429:
                wait = 60 * (attempt + 1)
                logger.warning("API 限流，等待 %d 秒后重试...", wait)
                time.sleep(wait)
            else:
                logger.error("AI API HTTP 错误 %d: %s", status, e)
                if attempt < max_retries - 1:
                    time.sleep(10)
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error("解析 AI 响应失败: %s", e)
            if attempt < max_retries - 1:
                time.sleep(5)
        except Exception as e:
            logger.error("AI API 调用异常: %s", e)
            if attempt < max_retries - 1:
                time.sleep(10)

    return None
