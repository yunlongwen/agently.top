# -*- coding: utf-8 -*-
"""
分层记忆服务。

提供三层记忆能力：
- L1 每日趋势记忆：每天各来源的核心主题
- L2 主题追踪记忆：跨天同一主题的演变轨迹
- L3 编辑决策记忆：每日选稿/去重/合并决策

存储采用 Redis + 磁盘双写，不引入外部向量数据库。
"""

import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from config import (
    MEMORY_CONTEXT_MAX_TOPICS,
    MEMORY_DAILY_TTL_DAYS,
    MEMORY_EDITORIAL_TTL_DAYS,
    MEMORY_ENABLED,
    MEMORY_LLM_ENABLED,
    MEMORY_OUTPUT_DIR,
    MEMORY_TOPIC_TTL_DAYS,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    REDIS_KEY_PREFIX,
)
from memory_prompts import (
    daily_trend_extraction_prompt,
    memory_insights_prompt,
    topic_match_prompt,
)
from redis_client import get_redis_client

logger = logging.getLogger(__name__)


class MemoryService:
    """分层记忆服务。"""

    def __init__(
        self,
        output_dir: str | None = None,
        redis_client=None,
        enabled: bool = True,
    ):
        self._enabled = enabled and MEMORY_ENABLED
        self._output_dir = Path(output_dir or MEMORY_OUTPUT_DIR)
        self._redis = redis_client
        self._redis_tried = redis_client is not None
        self._llm_enabled = MEMORY_LLM_ENABLED

    def _get_redis(self):
        """获取 Redis client，失败或不可用时返回 None 并缓存。"""
        if self._redis is not None:
            return self._redis
        if self._redis_tried:
            return None
        self._redis_tried = True
        try:
            self._redis = get_redis_client()
        except Exception as e:
            logger.debug("Redis 不可用，记忆服务使用磁盘模式: %s", e)
            self._redis = None
        return self._redis

    @property
    def enabled(self) -> bool:
        return self._enabled

    # ------------------------------------------------------------------
    # 公共入口
    # ------------------------------------------------------------------

    def build_context(self, items: list[dict], days: int = 3) -> str:
        """
        为当前 items 构建历史上下文文本，用于注入摘要 prompt。

        返回近 N 天与当前 items 最相关的主题概述。
        """
        if not self._enabled:
            return ""

        try:
            active_topics = self._load_active_topics(days=days)
            if not active_topics:
                return ""

            # 提取当前 items 的关键词（简单分词）
            current_keywords = self._extract_keywords(items)
            scored = []
            for topic in active_topics:
                score = self._jaccard_similarity(
                    set(current_keywords),
                    set(topic.get("keywords", [])),
                )
                scored.append((score, topic))

            scored.sort(key=lambda x: x[0], reverse=True)
            top_topics = [t for _, t in scored[:MEMORY_CONTEXT_MAX_TOPICS] if _ > 0]
            if not top_topics:
                return ""

            lines = []
            for topic in top_topics:
                evolution = topic.get("evolution", [])
                latest = evolution[-1] if evolution else {}
                summary = latest.get("summary", "") or topic.get("topic", "")
                lines.append(
                    "- {}：{}（涉及来源：{}）".format(
                        topic.get("topic", ""),
                        summary[:80],
                        ", ".join(topic.get("source_ids", [])),
                    )
                )
            return "\n".join(lines)
        except Exception as e:
            logger.warning("构建记忆上下文失败: %s", e)
            return ""

    def save_daily_memory(self, items: list[dict], date_text: str | None = None) -> dict[str, Any]:
        """
        保存每日趋势记忆（L1）。

        按来源分组，为每个来源生成主题列表。
        """
        result = {"saved": [], "errors": []}
        if not self._enabled:
            return result

        date_text = date_text or datetime.now().strftime("%Y-%m-%d")

        # 按来源分组
        grouped: dict[str, list[dict]] = {}
        for item in items or []:
            source_id = item.get("source", "")
            if not source_id:
                continue
            grouped.setdefault(source_id, []).append(item)

        for source_id, source_items in grouped.items():
            try:
                topics = self._extract_daily_topics(source_id, source_items)
                memory = {
                    "date": date_text,
                    "source_id": source_id,
                    "topics": topics,
                }
                self._write_memory(
                    key=f"memory:daily:{date_text}:{source_id}",
                    file_name=f"daily/{date_text}.json",
                    data=memory,
                    ttl_days=MEMORY_DAILY_TTL_DAYS,
                    merge_key=source_id,
                )
                result["saved"].append(source_id)
            except Exception as e:
                logger.warning("保存来源 %s 的每日记忆失败: %s", source_id, e)
                result["errors"].append(f"{source_id}: {e}")

        return result

    def update_topic_memory(
        self,
        items: list[dict],
        daily_memories: dict[str, Any] | None = None,
        date_text: str | None = None,
    ) -> dict[str, Any]:
        """
        更新主题追踪记忆（L2）。

        把当日 items 合并到已有主题，或创建新主题。
        """
        result = {"merged": 0, "created": 0, "errors": []}
        if not self._enabled:
            return result

        date_text = date_text or datetime.now().strftime("%Y-%m-%d")

        # 加载活跃主题
        active_topics = self._load_active_topics(days=30)
        topic_map = {t["topic_id"]: t for t in active_topics}

        for item in items or []:
            try:
                title = item.get("title", "")
                summary = item.get("chinese_summary") or item.get("original_summary", "")
                url = item.get("url", "")
                source_id = item.get("source", "")

                matched_topic_id = self._match_topic(
                    title=title,
                    summary=summary,
                    active_topics=active_topics,
                )

                if matched_topic_id and matched_topic_id in topic_map:
                    topic = topic_map[matched_topic_id]
                    topic["last_seen"] = date_text
                    topic["source_ids"] = list(set(topic.get("source_ids", []) + [source_id]))
                    topic["evolution"].append({
                        "date": date_text,
                        "summary": summary[:200],
                        "urls": [url] if url else [],
                    })
                    # 状态保持 active
                    topic["status"] = "active"
                    result["merged"] += 1
                else:
                    topic_id = self._generate_topic_id(title)
                    new_topic = {
                        "topic_id": topic_id,
                        "topic": self._generate_topic_name(title, summary),
                        "keywords": self._extract_keywords([item])[:5],
                        "first_seen": date_text,
                        "last_seen": date_text,
                        "source_ids": [source_id] if source_id else [],
                        "evolution": [{
                            "date": date_text,
                            "summary": summary[:200],
                            "urls": [url] if url else [],
                        }],
                        "status": "active",
                    }
                    topic_map[topic_id] = new_topic
                    active_topics.append(new_topic)
                    result["created"] += 1

            except Exception as e:
                logger.warning("更新主题记忆失败: %s", e)
                result["errors"].append(str(e))

        # 保存所有主题
        for topic in active_topics:
            try:
                self._write_memory(
                    key=f"memory:topic:{topic['topic_id']}",
                    file_name=f"topics/{topic['topic_id']}.json",
                    data=topic,
                    ttl_days=MEMORY_TOPIC_TTL_DAYS,
                )
            except Exception as e:
                logger.warning("保存主题 %s 失败: %s", topic.get("topic_id"), e)
                result["errors"].append(str(e))

        # 更新索引
        try:
            self._update_topic_index(active_topics)
        except Exception as e:
            logger.warning("更新主题索引失败: %s", e)
            result["errors"].append(str(e))

        return result

    def save_editorial_memory(
        self,
        decisions: list[dict],
        date_text: str | None = None,
    ) -> dict[str, Any]:
        """
        保存编辑决策记忆（L3）。
        """
        result = {"saved": False, "errors": []}
        if not self._enabled:
            return result

        date_text = date_text or datetime.now().strftime("%Y-%m-%d")
        memory = {"date": date_text, "decisions": decisions or []}

        try:
            self._write_memory(
                key=f"memory:editorial:{date_text}",
                file_name=f"editorial/{date_text}.json",
                data=memory,
                ttl_days=MEMORY_EDITORIAL_TTL_DAYS,
            )
            result["saved"] = True
        except Exception as e:
            logger.warning("保存编辑决策记忆失败: %s", e)
            result["errors"].append(str(e))

        return result

    def build_memory_insights(self, days: int = 3) -> str:
        """
        为微信公众号文章生成「近期趋势回顾」段落。

        返回空字符串表示没有可展示的趋势。
        """
        if not self._enabled:
            return ""

        try:
            active_topics = self._load_active_topics(days=days)
            # 只保留跨天或近 2 天活跃的主题
            filtered = [
                t for t in active_topics
                if len(t.get("evolution", [])) >= 2
                or t.get("last_seen") == datetime.now().strftime("%Y-%m-%d")
            ]
            if not filtered:
                return ""

            # 按 evolution 长度排序，取最活跃的 3 个
            filtered.sort(key=lambda t: len(t.get("evolution", [])), reverse=True)
            top_topics = filtered[:3]

            # 用 LLM 生成回顾文本
            if OPENAI_API_KEY:
                return self._generate_insights_with_llm(top_topics)

            # 降级：简单拼接
            lines = ["**近期趋势回顾**："]
            for topic in top_topics:
                evolution = topic.get("evolution", [])
                latest = evolution[-1] if evolution else {}
                lines.append(
                    "- {}：{}".format(
                        topic.get("topic", ""),
                        latest.get("summary", "")[:60],
                    )
                )
            return "\n".join(lines)
        except Exception as e:
            logger.warning("生成记忆洞察失败: %s", e)
            return ""

    # ------------------------------------------------------------------
    # 内部方法：主题提取与匹配
    # ------------------------------------------------------------------

    def _extract_daily_topics(self, source_id: str, items: list[dict]) -> list[dict]:
        """为单个来源的 items 提取每日主题。"""
        if not items:
            return []

        # 构建 item 文本
        item_lines = []
        for i, item in enumerate(items, 1):
            summary = item.get("chinese_summary") or item.get("original_summary", "")
            item_lines.append(
                "{}. 标题：{}\n   摘要：{}".format(
                    i,
                    item.get("title", ""),
                    summary[:200],
                )
            )

        if OPENAI_API_KEY:
            try:
                prompt = daily_trend_extraction_prompt(source_id, "\n\n".join(item_lines))
                result = self._call_memory_llm(prompt)
                topics = result.get("topics", [])
                # 清理字段
                cleaned = []
                for t in topics:
                    cleaned.append({
                        "topic": str(t.get("topic", ""))[:20],
                        "keywords": [str(k).strip() for k in t.get("keywords", [])[:5]],
                        "count": int(t.get("count", 1)),
                        "representative_urls": t.get("representative_urls", [])[:2],
                    })
                return cleaned
            except Exception as e:
                logger.warning("LLM 提取每日主题失败: %s", e)

        # 降级：按关键词简单聚类
        return self._fallback_topic_extraction(items)

    def _fallback_topic_extraction(self, items: list[dict]) -> list[dict]:
        """无 LLM 时的主题提取降级。"""
        keywords_counter: dict[str, int] = {}
        url_map: dict[str, str] = {}
        for item in items:
            kws = self._extract_keywords([item])
            for kw in kws:
                keywords_counter[kw] = keywords_counter.get(kw, 0) + 1
                if kw not in url_map and item.get("url"):
                    url_map[kw] = item["url"]

        # 取出现频次最高的 5 个词作为主题
        top = sorted(keywords_counter.items(), key=lambda x: x[1], reverse=True)[:5]
        topics = []
        for kw, count in top:
            topics.append({
                "topic": kw,
                "keywords": [kw],
                "count": count,
                "representative_urls": [url_map.get(kw, "")] if url_map.get(kw) else [],
            })
        return topics

    def _match_topic(
        self,
        title: str,
        summary: str,
        active_topics: list[dict],
    ) -> str | None:
        """判断新报道属于哪个已有主题，返回 topic_id 或 None。"""
        if not active_topics:
            return None

        # 先用本地关键词相似度快速筛选候选
        candidate_keywords = self._extract_keywords([{"title": title, "chinese_summary": summary}])
        candidates = []
        for topic in active_topics:
            score = self._jaccard_similarity(
                set(candidate_keywords),
                set(topic.get("keywords", [])),
            )
            if score >= 0.15:
                candidates.append((score, topic))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_topic = candidates[0]

        # 高分直接合并
        if best_score >= 0.25:
            return best_topic.get("topic_id")

        # LLM 二次确认（可选）
        if self._llm_enabled and OPENAI_API_KEY and best_score >= 0.15:
            try:
                topics_json = json.dumps(
                    [{"topic_id": t["topic_id"], "topic": t["topic"], "keywords": t.get("keywords", [])}
                     for _, t in candidates[:3]],
                    ensure_ascii=False,
                )
                prompt = topic_match_prompt(title, summary[:300], topics_json)
                result = self._call_memory_llm(prompt)
                if result.get("action") == "merge":
                    return result.get("topic_id") or best_topic.get("topic_id")
            except Exception as e:
                logger.warning("LLM 主题匹配失败: %s", e)

        return None

    # ------------------------------------------------------------------
    # 内部方法：存储读写
    # ------------------------------------------------------------------

    def _write_memory(
        self,
        key: str,
        file_name: str,
        data: dict,
        ttl_days: int,
        merge_key: str | None = None,
    ) -> None:
        """双写 Redis 和磁盘。"""
        # 磁盘写入
        file_path = self._output_dir / file_name
        file_path.parent.mkdir(parents=True, exist_ok=True)

        existing_data: dict | None = None
        if merge_key and file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except Exception:
                existing_data = None

        if existing_data and isinstance(existing_data, dict) and "topics" in existing_data:
            # 合并同一天的多个来源主题
            merged_topics = list(existing_data.get("topics", []))
            if isinstance(data.get("topics"), list):
                merged_topics.extend(data["topics"])
            existing_data["topics"] = merged_topics
            data = existing_data

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Redis 写入
        redis_client = self._get_redis()
        if redis_client:
            full_key = f"{REDIS_KEY_PREFIX}:{key}"
            redis_client.set(
                full_key,
                json.dumps(data, ensure_ascii=False),
                ex=timedelta(days=ttl_days),
            )

    def _load_memory(self, key: str, file_name: str) -> dict | None:
        """先读 Redis，失败降级磁盘。"""
        redis_client = self._get_redis()
        if redis_client:
            try:
                full_key = f"{REDIS_KEY_PREFIX}:{key}"
                data = redis_client.get(full_key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.debug("从 Redis 读取记忆失败: %s", e)

        file_path = self._output_dir / file_name
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.debug("从磁盘读取记忆失败: %s", e)

        return None

    def _load_active_topics(self, days: int = 30) -> list[dict]:
        """加载所有活跃主题。"""
        topics = []

        # 优先从索引加载
        index = self._load_memory("memory:index:topics", "index.json")
        if index and isinstance(index.get("topics"), list):
            for topic_id in index["topics"]:
                topic = self._load_memory(
                    f"memory:topic:{topic_id}",
                    f"topics/{topic_id}.json",
                )
                if topic:
                    topics.append(topic)
            return topics

        # 索引不存在时，扫描磁盘
        topics_dir = self._output_dir / "topics"
        if not topics_dir.exists():
            return []

        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        for file_path in topics_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    topic = json.load(f)
                if topic.get("last_seen", "") >= cutoff:
                    topics.append(topic)
            except Exception:
                continue

        return topics

    def _update_topic_index(self, active_topics: list[dict]) -> None:
        """更新主题索引。"""
        index = {
            "updated_at": datetime.now().isoformat(),
            "topics": [t["topic_id"] for t in active_topics],
        }
        self._write_memory(
            key="memory:index:topics",
            file_name="index.json",
            data=index,
            ttl_days=MEMORY_TOPIC_TTL_DAYS,
        )

    # ------------------------------------------------------------------
    # 内部方法：LLM 调用
    # ------------------------------------------------------------------

    def _call_memory_llm(self, prompt: str, max_retries: int = 3) -> dict:
        """调用 OpenAI 兼容接口，返回解析后的 JSON dict。"""
        if not OPENAI_API_KEY:
            raise RuntimeError("未配置 OPENAI_API_KEY")

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": OPENAI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "你是 AI 资讯编辑助手。请始终返回有效 JSON，不要包含 markdown 代码块。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 2000,
        }

        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    f"{OPENAI_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120,
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"].strip()
                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
                return json.loads(content)
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response is not None else 0
                if status == 429:
                    wait = 60 * (attempt + 1)
                    logger.warning("记忆 LLM 限流，等待 %d 秒后重试...", wait)
                    time.sleep(wait)
                elif attempt < max_retries - 1:
                    time.sleep(10)
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logger.warning("解析记忆 LLM 响应失败: %s", e)
                if attempt < max_retries - 1:
                    time.sleep(5)
            except Exception as e:
                logger.warning("记忆 LLM 调用异常: %s", e)
                if attempt < max_retries - 1:
                    time.sleep(10)

        raise RuntimeError("记忆 LLM 调用失败")

    def _generate_insights_with_llm(self, topics: list[dict]) -> str:
        """用 LLM 生成趋势回顾段落。"""
        topics_json = json.dumps(
            [
                {
                    "topic": t.get("topic", ""),
                    "keywords": t.get("keywords", []),
                    "days": len(t.get("evolution", [])),
                }
                for t in topics
            ],
            ensure_ascii=False,
        )
        prompt = memory_insights_prompt(topics_json)
        try:
            result = self._call_memory_llm(prompt)
            text = result.get("text", "") if isinstance(result, dict) else str(result)
            # 如果 LLM 返回了字符串而不是 dict
            if not text and isinstance(result, str):
                text = result
            return text.strip()[:300]
        except Exception:
            # 降级为简单拼接
            lines = ["**近期趋势回顾**："]
            for topic in topics:
                evolution = topic.get("evolution", [])
                latest = evolution[-1] if evolution else {}
                lines.append(
                    "- {}：{}".format(
                        topic.get("topic", ""),
                        latest.get("summary", "")[:60],
                    )
                )
            return "\n".join(lines)

    # ------------------------------------------------------------------
    # 内部方法：工具函数
    # ------------------------------------------------------------------

    @staticmethod
    def _item_hash(item: dict) -> str:
        """生成条目去重哈希。"""
        text = "{}|{}|{}".format(
            item.get("source", ""),
            item.get("title", ""),
            item.get("url", ""),
        )
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _generate_topic_id(title: str) -> str:
        """基于标题生成稳定 topic_id。"""
        return hashlib.sha256(title.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def _generate_topic_name(title: str, summary: str) -> str:
        """生成主题名：优先用标题中的核心名词。"""
        # 简单做法：取标题前 12 个字符
        name = title.strip()[:12]
        if not name:
            name = summary.strip()[:12]
        return name or "未命名主题"

    @staticmethod
    def _extract_keywords(items: list[dict]) -> list[str]:
        """从 items 中提取关键词。优先使用 jieba 分词，未安装时使用正则降级。"""
        text = " ".join(
            "{} {}".format(
                item.get("title", ""),
                item.get("chinese_summary") or item.get("original_summary", ""),
            )
            for item in items
        )

        # 优先使用 jieba 进行中文分词
        try:
            import jieba
            words = list(jieba.cut(text))
        except ImportError:
            # 降级：正则提取英文组合与中文连续字符
            words = re.findall(
                r"[A-Za-z][A-Za-z0-9]*(?:[-][A-Za-z0-9]+)*|[一-鿿]{2,}",
                text,
            )
            words += re.findall(r"[A-Za-z]+\d+(?:\.\d+)?", text)

        # 简单过滤常见停用词与过短词
        stopwords = {
            "the", "and", "for", "with", "this", "that", "from", "https",
            "http", "www", "com", "一个", "可以", "已经", "成为", "通过",
            "进行", "使用", "包括", "需要", "表示", "不会", "没有", "以及",
            "我们", "你们", "他们", "因为", "所以", "但是", "如果", "这些",
            "什么", "还是", "或者", "以及", "对于", "关于", "由于", "随着",
        }
        filtered = []
        for word in words:
            word = word.strip()
            if not word:
                continue
            if len(word) < 2:
                continue
            if word.lower() in stopwords:
                continue
            filtered.append(word)

        # 去重并保留顺序
        seen = set()
        result = []
        for word in filtered:
            key = word.lower() if word.isascii() else word
            if key not in seen:
                seen.add(key)
                result.append(word)
        return result

    @staticmethod
    def _jaccard_similarity(a: set, b: set) -> float:
        """计算 Jaccard 相似度。"""
        if not a and not b:
            return 0.0
        intersection = len(a & b)
        union = len(a | b)
        return intersection / union if union else 0.0
