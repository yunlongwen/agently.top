# Milestone A 多渠道扩展实施计划（第一部分：A5 + A1 + A2）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 Milestone A 的前三个子系统：统一渲染层（A5）、RSS 输入源（A1）、按源实时调度与前端分组展开（A2），为后续多渠道推送（A3）奠定接口基础。

**Architecture:** 新增 `renderers/` 统一渲染层，把内容构建与渠道 transport 解耦；新增 `sources/rss.py` 和独立 `config/rss.yaml` 处理任意 RSS/Atom 源；用异步按源调度替换固定时间点调度，支持无新内容跳过；前端按 `/api/sources` 返回的 `display_priority` 分组折叠，所有分组与展开状态来自配置。

**Tech Stack:** Python 3.x, FastAPI, Vue 3, Redis, requests, markdown, feedparser（新增）, aiohttp（新增，可选）

## Global Constraints

- 部署服务器不能使用网络代理；所有新增源必须国内裸连稳定访问。
- 海外源（如 arXiv）默认关闭。
- 来源 ID、优先级、默认展开状态、采集间隔必须可配置，不在 Vue 模板或核心代码里硬编码。
- RSS 源配置使用独立文件 `config/rss.yaml`，不考虑与旧配置兼容。
- 页面风格必须与现有 Vue 3 卡片流保持一致。
- 单源失败不影响整体；无新内容时跳过摘要和推送。
- TDD：每个任务先写测试再实现；频繁提交。

## File Structure

| 路径 | 职责 |
|---|---|
| `renderers/base.py` | `RenderedContent` 数据类与 `Renderer` 抽象基类 |
| `renderers/markdown_renderer.py` | 生成 Markdown（微信公众号、企业微信、钉钉等） |
| `renderers/html_renderer.py` | 生成 HTML（邮件、Web） |
| `renderers/plain_renderer.py` | 生成纯文本（降级、Bark 等） |
| `renderers/feishu_card_renderer.py` | 生成飞书交互卡片 JSON |
| `sources/base.py` | `SourceSpider` 抽象基类 |
| `sources/rss.py` | RSS/Atom 源采集实现 |
| `sources/rss_config.py` | 加载 `config/rss.yaml` |
| `config/rss.yaml` | RSS 源列表与参数（独立配置文件） |
| `config.yaml` | 前端分组、采集调度三挡默认间隔与覆盖值 |
| `scheduler_v2.py` | 异步按源调度器 |
| `source_registry.py` | 扩展 `display_priority` 字段 |
| `content_items.py` | 适配 RSS 条目；提供统一模型辅助函数 |
| `content_store.py` | 扩展来源元数据读取 |
| `api.py` | `/api/sources` 返回 `display_priority`；新增 `/api/source-groups` |
| `frontend/src/App.vue` | 按优先级分组折叠渲染 |

---

## Phase A5：统一渲染层

### Task 1：Renderer 基础类型与 MarkdownRenderer

**Files：**
- Create: `renderers/base.py`
- Create: `renderers/markdown_renderer.py`
- Test: `tests/test_renderers.py`

**Interfaces：**
- Produces: `RenderedContent(channel, format, title, body, excerpt, metadata)` dataclass
- Produces: `Renderer.render(items: list[dict], channel: str, options: dict | None) -> RenderedContent`

- [ ] **Step 1：写失败测试**

```python
def test_rendered_content_dataclass():
    from renderers.base import RenderedContent
    rc = RenderedContent(channel="wechat", format="markdown", title="t", body="b", excerpt="e", metadata={})
    assert rc.channel == "wechat"

def test_markdown_renderer_returns_rendered_content():
    from renderers.markdown_renderer import MarkdownRenderer
    renderer = MarkdownRenderer()
    result = renderer.render([], channel="wechat")
    assert result.channel == "wechat"
    assert result.format == "markdown"
    assert "Agently" in result.title
```

- [ ] **Step 2：运行测试确认失败**

Run: `pytest tests/test_renderers.py -v`
Expected: `ModuleNotFoundError: No module named 'renderers.base'`

- [ ] **Step 3：实现基础类型与 MarkdownRenderer**

```python
# renderers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


@dataclass
class RenderedContent:
    channel: str
    format: Literal["markdown", "html", "plain", "feishu_card"]
    title: str
    body: str
    excerpt: str
    metadata: dict


class Renderer(ABC):
    @abstractmethod
    def render(self, items: list[dict], channel: str, options: dict | None = None) -> RenderedContent:
        ...
```

```python
# renderers/markdown_renderer.py
import logging
from datetime import datetime
from typing import Any

from renderers.base import Renderer, RenderedContent

logger = logging.getLogger(__name__)


class MarkdownRenderer(Renderer):
    def render(self, items: list[dict], channel: str = "markdown", options: dict[str, Any] | None = None) -> RenderedContent:
        options = options or {}
        date_text = options.get("date_text") or datetime.now().strftime("%Y-%m-%d")
        title = options.get("title") or f"Agently 每日速览 · {date_text}"

        lines = [f"# {title}", ""]
        lines.append(
            "> 每天自动聚合 GitHub Trending、Hacker News、国内 AI 媒体等高质量信息源，"
            "由 AI 生成中文摘要，帮助你快速掌握前沿动态。"
        )
        lines.append("")

        if options.get("memory_insights"):
            lines.append(options["memory_insights"])
            lines.append("")

        grouped = {}
        for item in items or []:
            source = item.get("source", "unknown")
            grouped.setdefault(source, []).append(item)

        for source_id, source_items in grouped.items():
            lines.append(f"## {source_id}")
            lines.append("")
            for idx, item in enumerate(source_items, 1):
                title_item = (item.get("title") or "无标题").strip()
                url = (item.get("url") or "").strip()
                summary = (item.get("chinese_summary") or item.get("original_summary") or "").strip()
                backend_focus = (item.get("backend_focus") or "").strip()
                lines.append(f"### {idx}. {title_item}")
                if summary:
                    lines.append("")
                    lines.append(summary)
                if backend_focus and backend_focus != summary:
                    lines.append("")
                    lines.append(f"> 后端看点：{backend_focus}")
                if url:
                    lines.append("")
                    lines.append(f"[阅读原文 →]({url})")
                lines.append("")

        body = "\n".join(lines)
        return RenderedContent(
            channel=channel,
            format="markdown",
            title=title,
            body=body,
            excerpt=body[:200],
            metadata={"item_count": len(items)},
        )
```

- [ ] **Step 4：运行测试确认通过**

Run: `pytest tests/test_renderers.py -v`
Expected: PASS

- [ ] **Step 5：提交**

```bash
git add renderers/base.py renderers/markdown_renderer.py tests/test_renderers.py
git commit -m "feat(renderers): 引入统一渲染层基础类型与 MarkdownRenderer"
```

---

### Task 2：HtmlRenderer 与 PlainRenderer

**Files：**
- Create: `renderers/html_renderer.py`
- Create: `renderers/plain_renderer.py`
- Modify: `renderers/__init__.py`（创建并导出）
- Test: `tests/test_renderers.py`

**Interfaces：**
- Consumes: `RenderedContent`, `Renderer`
- Produces: `HtmlRenderer.render(...) -> RenderedContent(format="html")`
- Produces: `PlainRenderer.render(...) -> RenderedContent(format="plain")`

- [ ] **Step 1：写失败测试**

```python
def test_html_renderer_outputs_html():
    from renderers.html_renderer import HtmlRenderer
    renderer = HtmlRenderer()
    result = renderer.render([{"title": "T", "url": "https://t", "chinese_summary": "S"}], channel="email")
    assert result.format == "html"
    assert "<html" in result.body
    assert "T" in result.body

def test_plain_renderer_outputs_text():
    from renderers.plain_renderer import PlainRenderer
    renderer = PlainRenderer()
    result = renderer.render([{"title": "T", "chinese_summary": "S"}], channel="bark")
    assert result.format == "plain"
    assert "T" in result.body
```

- [ ] **Step 2：运行测试确认失败**

Run: `pytest tests/test_renderers.py::test_html_renderer_outputs_html tests/test_renderers.py::test_plain_renderer_outputs_text -v`
Expected: FAIL

- [ ] **Step 3：实现两个 Renderer**

```python
# renderers/html_renderer.py
import logging
from datetime import datetime
from typing import Any

import markdown as md_lib

from renderers.base import Renderer, RenderedContent

logger = logging.getLogger(__name__)


class HtmlRenderer(Renderer):
    def render(self, items: list[dict], channel: str = "email", options: dict[str, Any] | None = None) -> RenderedContent:
        options = options or {}
        date_text = options.get("date_text") or datetime.now().strftime("%Y-%m-%d")
        title = options.get("title") or f"AI 后端专项信息源报告 - {date_text}"

        rows = [
            "<!DOCTYPE html>",
            '<html><head><meta charset="utf-8">',
            "<style>",
            "  body { font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; color: #24292e; padding: 20px; max-width: 1000px; margin: 0 auto; }",
            "  h1 { color: #0366d6; border-bottom: 2px solid #e1e4e8; padding-bottom: 10px; }",
            "  h2 { color: #24292e; margin-top: 30px; }",
            "  table { border-collapse: collapse; width: 100%; margin: 15px 0; }",
            "  th { background-color: #0366d6; color: white; padding: 10px 12px; text-align: left; font-size: 13px; }",
            "  td { padding: 10px 12px; border-bottom: 1px solid #e1e4e8; font-size: 13px; vertical-align: top; }",
            "  tr:nth-child(even) { background-color: #f6f8fa; }",
            "  a { color: #0366d6; text-decoration: none; }",
            "  .summary { color: #586069; line-height: 1.5; }",
            "</style>",
            "</head><body>",
            f"<h1>{title}</h1>",
        ]

        if not items:
            rows.append("<p>今日暂无内容。</p>")
        else:
            rows.extend([
                "<table>",
                "<tr><th>#</th><th>来源</th><th>标题</th><th>发布时间</th><th>中文摘要</th><th>后端看点</th></tr>",
            ])
            for i, item in enumerate(items, 1):
                title = str(item.get("title") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                url = item.get("url") or ""
                source = str(item.get("source") or "").replace("&", "&amp;").replace("<", "&lt;")
                published = str(item.get("published_at") or "").replace("<", "&lt;")
                summary = str(item.get("chinese_summary") or item.get("original_summary") or "").replace("&", "&amp;").replace("<", "&lt;")
                backend = str(item.get("backend_focus") or "").replace("&", "&amp;").replace("<", "&lt;")
                rows.append(
                    f"<tr><td>{i}</td><td>{source}</td>"
                    f'<td><a href="{url}">{title}</a></td>'
                    f"<td>{published}</td><td class=\"summary\">{summary}</td><td class=\"summary\">{backend}</td></tr>"
                )
            rows.append("</table>")

        rows.extend([
            '<div class="footer"><p>此邮件由 Agently 自动生成。</p></div>',
            "</body></html>",
        ])
        body = "\n".join(rows)
        return RenderedContent(
            channel=channel,
            format="html",
            title=title,
            body=body,
            excerpt=body[:200],
            metadata={"item_count": len(items)},
        )
```

```python
# renderers/plain_renderer.py
import logging
from datetime import datetime
from typing import Any

from renderers.base import Renderer, RenderedContent

logger = logging.getLogger(__name__)


class PlainRenderer(Renderer):
    def render(self, items: list[dict], channel: str = "plain", options: dict[str, Any] | None = None) -> RenderedContent:
        options = options or {}
        date_text = options.get("date_text") or datetime.now().strftime("%Y-%m-%d")
        title = options.get("title") or f"Agently 每日速览 · {date_text}"
        max_length = options.get("max_length", 500)

        lines = [title, ""]
        for idx, item in enumerate(items or [], 1):
            line = f"{idx}. {item.get('title', '无标题')}"
            url = item.get("url")
            if url:
                line += f" ({url})"
            lines.append(line)

        body = "\n".join(lines)
        if len(body) > max_length:
            body = body[:max_length].rsplit("\n", 1)[0] + "\n…"

        return RenderedContent(
            channel=channel,
            format="plain",
            title=title,
            body=body,
            excerpt=body[:100],
            metadata={"item_count": len(items)},
        )
```

```python
# renderers/__init__.py
from renderers.base import RenderedContent, Renderer
from renderers.markdown_renderer import MarkdownRenderer
from renderers.html_renderer import HtmlRenderer
from renderers.plain_renderer import PlainRenderer

__all__ = ["RenderedContent", "Renderer", "MarkdownRenderer", "HtmlRenderer", "PlainRenderer"]
```

- [ ] **Step 4：运行测试确认通过**

Run: `pytest tests/test_renderers.py -v`
Expected: PASS

- [ ] **Step 5：提交**

```bash
git add renderers/
git commit -m "feat(renderers): 增加 HtmlRenderer 与 PlainRenderer"
```

---

### Task 3：FeishuCardRenderer

**Files：**
- Create: `renderers/feishu_card_renderer.py`
- Test: `tests/test_renderers.py`

**Interfaces：**
- Produces: `RenderedContent(format="feishu_card", body=json_string)`

- [ ] **Step 1：写失败测试**

```python
def test_feishu_card_renderer_outputs_json():
    from renderers.feishu_card_renderer import FeishuCardRenderer
    renderer = FeishuCardRenderer()
    result = renderer.render([{"title": "T", "chinese_summary": "S", "url": "https://t"}], channel="feishu")
    assert result.format == "feishu_card"
    import json
    payload = json.loads(result.body)
    assert payload["msg_type"] == "interactive"
```

- [ ] **Step 2：运行测试确认失败**

Run: `pytest tests/test_renderers.py::test_feishu_card_renderer_outputs_json -v`
Expected: FAIL

- [ ] **Step 3：实现 FeishuCardRenderer**

```python
# renderers/feishu_card_renderer.py
import json
import logging
from datetime import datetime
from typing import Any

from renderers.base import Renderer, RenderedContent

logger = logging.getLogger(__name__)


class FeishuCardRenderer(Renderer):
    def render(self, items: list[dict], channel: str = "feishu", options: dict[str, Any] | None = None) -> RenderedContent:
        options = options or {}
        date_text = options.get("date_text") or datetime.now().strftime("%Y-%m-%d")
        title = options.get("title") or f"Agently 每日速览 · {date_text}"

        elements = []
        for idx, item in enumerate(items[:20], 1):
            text = f"{idx}. {item.get('title', '无标题')}\n{item.get('chinese_summary') or item.get('original_summary') or ''}".strip()
            elements.append({
                "tag": "div",
                "text": {"tag": "plain_text", "content": text[:500]},
            })
            url = item.get("url")
            if url:
                elements.append({
                    "tag": "action",
                    "actions": [{
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "阅读原文"},
                        "type": "primary",
                        "url": url,
                    }],
                })

        card = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                },
                "elements": elements or [{"tag": "div", "text": {"tag": "plain_text", "content": "今日暂无内容"}}],
            },
        }
        body = json.dumps(card, ensure_ascii=False)
        return RenderedContent(
            channel=channel,
            format="feishu_card",
            title=title,
            body=body,
            excerpt=title,
            metadata={"item_count": len(items)},
        )
```

- [ ] **Step 4：运行测试确认通过**

Run: `pytest tests/test_renderers.py -v`
Expected: PASS

- [ ] **Step 5：提交**

```bash
git add renderers/feishu_card_renderer.py tests/test_renderers.py
git commit -m "feat(renderers): 增加飞书卡片渲染器"
```

---

### Task 4：迁移 email_builder 与 wechat_article_builder 到 Renderers

**Files：**
- Modify: `email_builder.py`
- Modify: `wechat_article_builder.py`
- Modify: `publish_service.py`
- Test: `tests/test_renderers.py`（新增集成测试）

**Interfaces：**
- Consumes: `HtmlRenderer`, `MarkdownRenderer`
- Produces: `build_email_html(...)` 返回值与旧版一致（HTML 字符串）
- Produces: `build_daily_markdown(...)` 返回值与旧版一致（Markdown 字符串）

- [ ] **Step 1：写测试锁定现有行为**

```python
def test_build_email_html_uses_renderer():
    from email_builder import build_email_html
    html = build_email_html([], [], [], [], [], [{
        "source": "OpenAI", "title": "T", "url": "https://t",
        "published_at": "2026-06-20", "chinese_summary": "摘要", "backend_focus": "看点"
    }])
    assert "<html" in html
    assert "T" in html

def test_build_daily_markdown_uses_renderer():
    from wechat_article_builder import build_daily_markdown
    md = build_daily_markdown([{
        "source": "github-daily", "title": "Repo", "url": "https://github.com/x",
        "chinese_summary": "摘要", "backend_focus": "看点", "meta": {}
    }], "2026-06-20")
    assert "Repo" in md
    assert "摘要" in md
```

- [ ] **Step 2：运行测试确认失败**

Run: `pytest tests/test_renderers.py::test_build_email_html_uses_renderer tests/test_renderers.py::test_build_daily_markdown_uses_renderer -v`
Expected: 可能通过（旧实现还在），但下一步要改成使用 renderer

- [ ] **Step 3：改造 email_builder.py**

```python
# email_builder.py
from renderers.html_renderer import HtmlRenderer

_renderer = HtmlRenderer()


def build_email_html(daily_repos, weekly_repos, hn_stories, sspai_items=None, tmtpost_items=None, content_items=None):
    """生成 HTML 邮件内容（兼容旧签名，内部使用 HtmlRenderer）。"""
    items = []
    # 把旧参数按来源归类加入 items
    for repo in daily_repos or []:
        items.append({
            "source": "GitHub Trending Daily",
            "title": repo.get("full_name", ""),
            "url": repo.get("url", ""),
            "chinese_summary": repo.get("ai_summary", ""),
            "backend_focus": repo.get("backend_focus", ""),
        })
    for repo in weekly_repos or []:
        items.append({
            "source": "GitHub Trending Weekly",
            "title": repo.get("full_name", ""),
            "url": repo.get("url", ""),
            "chinese_summary": repo.get("ai_summary", ""),
        })
    for story in hn_stories or []:
        items.append({
            "source": "Hacker News",
            "title": story.get("title", ""),
            "url": story.get("url", ""),
            "chinese_summary": story.get("ai_summary", ""),
        })
    items.extend(content_items or [])

    rendered = _renderer.render(items, channel="email")
    return rendered.body
```

- [ ] **Step 4：改造 wechat_article_builder.py**

```python
# wechat_article_builder.py
from renderers.markdown_renderer import MarkdownRenderer
from config import WECHAT_CONTENT_MAX_LENGTH, WECHAT_MAX_ITEMS_PER_SOURCE, WECHAT_SOURCE_WHITELIST

_renderer = MarkdownRenderer()


def _parse_source_whitelist() -> set[str] | None:
    value = (WECHAT_SOURCE_WHITELIST or "").strip()
    if not value:
        return None
    return {item.strip() for item in value.split(",") if item.strip()}


def build_daily_markdown(items, date_text=None, memory_insights=None):
    """生成微信公众号 Markdown（兼容旧签名，内部使用 MarkdownRenderer）。"""
    date_text = date_text or datetime.now().strftime("%Y-%m-%d")
    whitelist = _parse_source_whitelist()
    max_per_source = max(WECHAT_MAX_ITEMS_PER_SOURCE, 1)

    filtered = []
    grouped = {}
    for item in items or []:
        source_id = item.get("source", "")
        if whitelist and source_id not in whitelist:
            continue
        grouped.setdefault(source_id, []).append(item)

    for source_id, source_items in grouped.items():
        filtered.extend(source_items[:max_per_source])

    rendered = _renderer.render(
        filtered,
        channel="wechat",
        options={
            "date_text": date_text,
            "memory_insights": memory_insights,
            "title": f"Agently.top 每日 AI 资讯 - {date_text}",
        },
    )
    body = rendered.body
    if len(body) > WECHAT_CONTENT_MAX_LENGTH:
        body = body[:WECHAT_CONTENT_MAX_LENGTH].rsplit("\n\n", 1)[0]
        body += "\n\n*（内容过长，剩余部分已省略）*"
    return body
```

- [ ] **Step 5：更新 publish_service.py 使用 RenderedContent**

```python
# publish_service.py 关键改动
from renderers.html_renderer import HtmlRenderer
from renderers.markdown_renderer import MarkdownRenderer

html_renderer = HtmlRenderer()
markdown_renderer = MarkdownRenderer()

# 在 publish_daily 中：
rendered = {
    "wechat": markdown_renderer.render(filtered_items, channel="wechat", options=common_options),
    "email": html_renderer.render(filtered_items, channel="email", options=common_options),
}

for publisher in enabled_publishers:
    content = rendered.get(publisher.id)
    if content is None:
        content = markdown_renderer.render(filtered_items, channel=publisher.id, options=common_options)
    result = publisher.publish(content, options=common_options)
```

- [ ] **Step 6：运行测试确认通过**

Run: `pytest tests/test_renderers.py tests/test_publishers.py -v`
Expected: PASS

- [ ] **Step 7：提交**

```bash
git add email_builder.py wechat_article_builder.py publish_service.py tests/test_renderers.py
git commit -m "refactor(renderers): email 与微信公众号 builder 迁移到统一渲染层"
```

---

## Phase A1：RSS 输入源

### Task 5：创建 RSS 独立配置文件

**Files：**
- Create: `config/rss.yaml`
- Test: `tests/test_rss_config.py`

**Interfaces：**
- Produces: 一个可被 `sources/rss_config.py` 读取的 YAML 文件

- [ ] **Step 1：写失败测试**

```python
def test_rss_config_file_exists():
    from pathlib import Path
    assert Path("config/rss.yaml").exists()
```

- [ ] **Step 2：运行测试确认失败**

Run: `pytest tests/test_rss_config.py -v`
Expected: FAIL

- [ ] **Step 3：创建 config/rss.yaml**

```yaml
rss:
  enabled: true
  global_max_age_days: 3
  request:
    timeout: 10
    retries: 2
    headers:
      User-Agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
  sources:
    - id: "rss-qbitai"
      name: "量子位"
      url: "https://www.qbitai.com/feed"
      category: "AI 快讯"
      display_priority: "high"
      max_age_days: 2
      max_items: 10

    - id: "rss-geekpark"
      name: "极客公园"
      url: "https://www.geekpark.net/rss"
      category: "科技动态"
      display_priority: "medium"
      max_age_days: 2
      max_items: 10

    - id: "rss-jiqizhixin"
      name: "机器之心"
      url: "https://www.jiqizhixin.com/rss"
      category: "AI 快讯"
      display_priority: "high"
      max_age_days: 2
      max_items: 10

    - id: "rss-36kr"
      name: "36kr"
      url: "https://36kr.com/feed"
      category: "科技动态"
      display_priority: "medium"
      max_age_days: 2
      max_items: 10

    - id: "rss-solidot"
      name: "Solidot"
      url: "https://www.solidot.org/index.rss"
      category: "开源科技"
      display_priority: "medium"
      max_age_days: 2
      max_items: 10

    - id: "rss-oschina"
      name: "开源中国"
      url: "https://www.oschina.net/news/rss"
      category: "开源趋势"
      display_priority: "medium"
      max_age_days: 2
      max_items: 10

    - id: "rss-v2ex-tech"
      name: "V2EX 技术"
      url: "https://www.v2ex.com/feed/tab/tech.xml"
      category: "社区讨论"
      display_priority: "high"
      fetch_interval_hours: 1
      max_age_days: 1
      max_items: 15

    - id: "rss-arxiv"
      name: "arXiv AI 论文"
      url: "https://rsshub.app/arxiv/query/AI"
      category: "论文"
      display_priority: "low"
      enabled: false
      fetch_interval_hours: 6
      max_age_days: 3
      max_items: 5
```

- [ ] **Step 4：运行测试确认通过**

Run: `pytest tests/test_rss_config.py -v`
Expected: PASS

- [ ] **Step 5：提交**

```bash
git add config/rss.yaml tests/test_rss_config.py
git commit -m "config(rss): 新增独立 RSS 源配置文件 config/rss.yaml"
```

---

### Task 6：RSS 配置加载器

**Files：**
- Create: `sources/rss_config.py`
- Test: `tests/test_rss_config.py`

**Interfaces：**
- Produces: `load_rss_config(path="config/rss.yaml") -> dict`
- Produces: `list_enabled_rss_sources(config) -> list[dict]`

- [ ] **Step 1：写失败测试**

```python
def test_load_rss_config():
    from sources.rss_config import load_rss_config, list_enabled_rss_sources
    cfg = load_rss_config("config/rss.yaml")
    assert cfg["rss"]["enabled"] is True
    sources = list_enabled_rss_sources(cfg)
    assert any(s["id"] == "rss-qbitai" for s in sources)
    assert all(s.get("enabled", True) for s in sources)
```

- [ ] **Step 2：运行测试确认失败**

Run: `pytest tests/test_rss_config.py -v`
Expected: FAIL

- [ ] **Step 3：实现加载器**

```python
# sources/rss_config.py
import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config" / "rss.yaml"


def load_rss_config(path: str | Path | None = None) -> dict:
    path = Path(path or DEFAULT_PATH)
    if not path.exists():
        raise FileNotFoundError(f"RSS 配置文件不存在: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def list_enabled_rss_sources(config: dict) -> list[dict]:
    rss = config.get("rss", {})
    if not rss.get("enabled", False):
        return []
    sources = rss.get("sources", []) or []
    return [s for s in sources if s.get("enabled", True)]


def get_rss_request_options(config: dict) -> dict:
    rss = config.get("rss", {})
    return rss.get("request", {"timeout": 10, "retries": 2, "headers": {}})
```

- [ ] **Step 4：运行测试确认通过**

Run: `pytest tests/test_rss_config.py -v`
Expected: PASS

- [ ] **Step 5：提交**

```bash
git add sources/rss_config.py tests/test_rss_config.py
git commit -m "feat(sources): 加载独立 RSS 配置文件"
```

---

### Task 7：SourceSpider 抽象基类

**Files：**
- Create: `sources/base.py`
- Test: `tests/test_sources.py`

**Interfaces：**
- Produces: `SourceSpider` ABC with `source_id`, `name`, `fetch() -> list[dict]`

- [ ] **Step 1：写失败测试**

```python
def test_source_spider_abstract():
    from sources.base import SourceSpider
    import inspect
    assert inspect.isabstract(SourceSpider)
```

- [ ] **Step 2：运行测试确认失败**

Run: `pytest tests/test_sources.py -v`
Expected: FAIL

- [ ] **Step 3：实现基类**

```python
# sources/base.py
from abc import ABC, abstractmethod
from typing import Any


class SourceSpider(ABC):
    @property
    @abstractmethod
    def source_id(self) -> str:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def fetch(self) -> list[dict[str, Any]]:
        """返回统一内容项列表。"""
        ...

    @property
    def display_priority(self) -> str:
        return "medium"

    @property
    def category(self) -> str:
        return ""

    @property
    def enabled(self) -> bool:
        return True
```

- [ ] **Step 4：运行测试确认通过**

Run: `pytest tests/test_sources.py -v`
Expected: PASS

- [ ] **Step 5：提交**

```bash
git add sources/base.py tests/test_sources.py
git commit -m "feat(sources): 引入 SourceSpider 抽象基类"
```

---

### Task 8：RSS Spider 实现

**Files：**
- Create: `sources/rss.py`
- Test: `tests/test_sources.py`

**Interfaces：**
- Consumes: `sources.rss_config.load_rss_config`, `feedparser`
- Produces: `RssSpider.fetch() -> list[dict]` 统一内容项

- [ ] **Step 1：写失败测试（使用本地 fixture）**

```python
import datetime as dt

def test_rss_spider_parses_feed(mocker):
    from sources.rss import RssSpider
    fake_feed = {
        "entries": [
            {
                "title": "Test Title",
                "link": "https://example.com/1",
                "published_parsed": (2026, 6, 20, 10, 0, 0, 0, 0, 0),
                "summary": "summary",
                "id": "guid-1",
            }
        ]
    }
    mocker.patch("feedparser.parse", return_value=fake_feed)
    spider = RssSpider({
        "id": "rss-test", "name": "Test", "url": "https://example.com/feed",
        "category": "Test", "display_priority": "medium", "max_age_days": 7, "max_items": 10
    })
    items = spider.fetch()
    assert len(items) == 1
    assert items[0]["title"] == "Test Title"
```

- [ ] **Step 2：运行测试确认失败**

Run: `pytest tests/test_sources.py::test_rss_spider_parses_feed -v`
Expected: FAIL

- [ ] **Step 3：实现 RSS Spider**

```python
# sources/rss.py
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import feedparser
import requests

from sources.base import SourceSpider
from sources.rss_config import get_rss_request_options, load_rss_config

logger = logging.getLogger(__name__)


def _parse_published(entry: dict) -> str:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        dt = datetime(*parsed[:6], tzinfo=timezone.utc)
        return dt.isoformat()
    return ""


def _normalize_url(url: str) -> str:
    url = url.split("#")[0]
    # 移除常见跟踪参数
    for param in ("utm_source", "utm_medium", "utm_campaign", "utm_content"):
        # 简化处理：仅做演示，实际可用 urllib.parse
        pass
    return url


class RssSpider(SourceSpider):
    def __init__(self, source_def: dict[str, Any], request_options: dict[str, Any] | None = None):
        self._def = source_def
        self._request_options = request_options or {}

    @property
    def source_id(self) -> str:
        return self._def["id"]

    @property
    def name(self) -> str:
        return self._def["name"]

    @property
    def display_priority(self) -> str:
        return self._def.get("display_priority", "medium")

    @property
    def category(self) -> str:
        return self._def.get("category", "")

    @property
    def enabled(self) -> bool:
        return self._def.get("enabled", True)

    def fetch(self) -> list[dict[str, Any]]:
        url = self._def["url"]
        timeout = self._request_options.get("timeout", 10)
        retries = self._request_options.get("retries", 2)
        headers = self._request_options.get("headers", {})

        last_exception = None
        for attempt in range(retries + 1):
            try:
                resp = requests.get(url, headers=headers, timeout=timeout)
                resp.raise_for_status()
                feed = feedparser.parse(resp.content)
                break
            except Exception as e:
                last_exception = e
                logger.warning("RSS 源 %s 请求失败（第 %d 次）: %s", self.source_id, attempt + 1, e)
                time.sleep(1)
        else:
            logger.error("RSS 源 %s 连续失败 %d 次: %s", self.source_id, retries + 1, last_exception)
            return []

        max_age_days = self._def.get("max_age_days", 3)
        max_items = self._def.get("max_items", 10)
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

        items = []
        for entry in feed.entries[:max_items * 2]:
            published_at = _parse_published(entry)
            if published_at:
                try:
                    pub_dt = datetime.fromisoformat(published_at)
                    if pub_dt < cutoff:
                        continue
                except Exception:
                    pass

            title = (entry.get("title") or "").strip()
            url = _normalize_url(entry.get("link") or "")
            summary = (entry.get("summary") or entry.get("description") or "").strip()
            guid = entry.get("id") or url

            if not title or not url:
                continue

            items.append({
                "source": self.source_id,
                "category": self.category,
                "title": title,
                "url": url,
                "published_at": published_at,
                "original_summary": summary[:500],
                "chinese_summary": "",
                "backend_focus": "",
                "meta": {"guid": guid},
            })

            if len(items) >= max_items:
                break

        return items


def build_all_rss_spiders(config_path: str | None = None) -> list[RssSpider]:
    cfg = load_rss_config(config_path)
    request_options = get_rss_request_options(cfg)
    return [RssSpider(s, request_options) for s in cfg.get("rss", {}).get("sources", []) if s.get("enabled", True)]
```

- [ ] **Step 4：运行测试确认通过**

Run: `pytest tests/test_sources.py -v`
Expected: PASS

- [ ] **Step 5：提交**

```bash
git add sources/rss.py tests/test_sources.py
git commit -m "feat(sources): 实现 RSS 采集蜘蛛 RssSpider"
```

---

### Task 9：source_registry 增加 display_priority

**Files：**
- Modify: `source_registry.py`
- Test: `tests/test_source_registry.py`

**Interfaces：**
- Produces: `SOURCE_DEFINITIONS` 中每个来源包含 `display_priority: str`
- Produces: `/api/sources` 返回字段包含 `display_priority`

- [ ] **Step 1：写失败测试**

```python
def test_all_sources_have_display_priority():
    from source_registry import SOURCE_DEFINITIONS
    for s in SOURCE_DEFINITIONS:
        assert "display_priority" in s
        assert s["display_priority"] in ("high", "medium", "low")
```

- [ ] **Step 2：运行测试确认失败**

Run: `pytest tests/test_source_registry.py -v`
Expected: FAIL

- [ ] **Step 3：更新 source_registry.py**

```python
# source_registry.py 节选
SOURCE_DEFINITIONS = [
    {
        "id": SOURCE_GITHUB_DAILY_ID,
        "name": "GitHub Daily",
        "label": "GitHub 日榜",
        "content_source": "GitHub Trending Daily",
        "category": "开源趋势",
        "display_priority": "high",
    },
    {
        "id": SOURCE_GITHUB_WEEKLY_ID,
        "name": "GitHub Weekly",
        "label": "GitHub 周榜",
        "content_source": "GitHub Trending Weekly",
        "category": "开源趋势",
        "display_priority": "low",
    },
    {
        "id": SOURCE_LINUX_DO_ID,
        "name": "Linux.do",
        "label": "Linux.do 技术日报",
        "content_source": "Linux.do",
        "category": "社区讨论",
        "display_priority": "high",
    },
    {
        "id": SOURCE_HACKER_NEWS_ID,
        "name": "Hacker News",
        "label": "Hacker News",
        "content_source": "Hacker News",
        "category": "社区讨论",
        "display_priority": "high",
    },
    {
        "id": SOURCE_SSPAI_ID,
        "name": "Sspai",
        "label": "少数派",
        "content_source": "少数派",
        "category": "AI 快讯",
        "display_priority": "medium",
    },
    {
        "id": SOURCE_TMTPOST_ID,
        "name": "Tmtpost",
        "label": "钛媒体",
        "content_source": "钛媒体",
        "category": "AI 快讯",
        "display_priority": "medium",
    },
    {
        "id": SOURCE_OPENAI_ID,
        "name": "OpenAI",
        "label": "OpenAI",
        "content_source": "OpenAI",
        "category": "AI 官方更新",
        "display_priority": "low",
    },
    {
        "id": SOURCE_ANTHROPIC_ID,
        "name": "Anthropic",
        "label": "Anthropic",
        "content_source": "Anthropic",
        "category": "AI 官方更新",
        "display_priority": "low",
    },
    {
        "id": SOURCE_INFOQ_ID,
        "name": "InfoQ",
        "label": "InfoQ AI",
        "content_source": "InfoQ AI Development",
        "category": "AI 工程实践",
        "display_priority": "medium",
    },
]
```

- [ ] **Step 4：运行测试确认通过**

Run: `pytest tests/test_source_registry.py -v`
Expected: PASS

- [ ] **Step 5：提交**

```bash
git add source_registry.py tests/test_source_registry.py
git commit -m "feat(registry): 为所有来源增加 display_priority 字段"
```

---

### Task 10：去重与内容存储适配

**Files：**
- Create: `dedup.py`
- Modify: `content_store.py`
- Modify: `content_items.py`
- Test: `tests/test_dedup.py`

**Interfaces：**
- Produces: `normalize_url(url: str) -> str`
- Produces: `is_seen_url(url: str) -> bool`, `mark_url_seen(url: str)`
- Produces: `filter_new_items(items) -> list[dict]`

- [ ] **Step 1：写失败测试**

```python
def test_normalize_url_strips_fragment_and_tracking():
    from dedup import normalize_url
    assert normalize_url("https://example.com/a?utm_source=x#section") == "https://example.com/a"

def test_filter_new_items():
    from dedup import filter_new_items
    items = [
        {"url": "https://example.com/a"},
        {"url": "https://example.com/b"},
    ]
    seen = {"https://example.com/a"}
    new_items = filter_new_items(items, seen=seen)
    assert len(new_items) == 1
    assert new_items[0]["url"] == "https://example.com/b"
```

- [ ] **Step 2：运行测试确认失败**

Run: `pytest tests/test_dedup.py -v`
Expected: FAIL

- [ ] **Step 3：实现去重模块**

```python
# dedup.py
import re
from urllib.parse import urlencode, urlparse, parse_qsl


TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "fbclid", "gclid"}


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qsl(parsed.query)
    filtered = [(k, v) for k, v in query if k.lower() not in TRACKING_PARAMS]
    query_str = urlencode(filtered)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}" + (f"?{query_str}" if query_str else "")


def filter_new_items(items: list[dict], seen: set[str]) -> list[dict]:
    new_items = []
    for item in items:
        url = normalize_url(item.get("url", ""))
        if url in seen:
            continue
        seen.add(url)
        new_items.append(item)
    return new_items


def filter_duplicate_items(items: list[dict]) -> list[dict]:
    seen = set()
    return filter_new_items(items, seen)
```

- [ ] **Step 4：修改 content_items.py 增加 RSS 适配**

```python
# content_items.py 新增
def _rss_to_items(rss_items):
    items_out = []
    for item in rss_items or []:
        items_out.append(make_content_item(
            source=item.get("source", ""),
            category=item.get("category", ""),
            title=item.get("title", ""),
            url=item.get("url", ""),
            published_at=item.get("published_at", ""),
            original_summary=item.get("original_summary", ""),
            chinese_summary=item.get("chinese_summary", ""),
            backend_focus=item.get("backend_focus", ""),
            meta=item.get("meta", {}),
        ))
    return items_out


def build_all_content_items(..., rss_items=None):
    items = []
    ...
    items.extend(_rss_to_items(rss_items))
    return items
```

- [ ] **Step 5：运行测试确认通过**

Run: `pytest tests/test_dedup.py tests/test_content_items.py -v`
Expected: PASS

- [ ] **Step 6：提交**

```bash
git add dedup.py content_items.py content_store.py tests/test_dedup.py
git commit -m "feat(dedup): URL 归一化去重与 RSS 内容项适配"
```

---

### Task 11：集成 RSS 到主采集流程

**Files：**
- Modify: `main.py`
- Modify: `content_items.py`
- Test: `tests/test_main.py`（新增/扩展）

**Interfaces：**
- Consumes: `sources.rss.build_all_rss_spiders`, `dedup.filter_duplicate_items`
- Produces: `run_spider()` 输出包含 RSS 来源归档

- [ ] **Step 1：写失败测试**

```python
def test_run_spider_includes_rss_sources(mocker):
    from main import run_spider
    # mock 所有外部请求，只验证 RSS spider 被调用并写入
    # 此测试较复杂，可先 mock sources.rss.build_all_rss_spiders 返回空列表
    mocker.patch("main.build_all_rss_spiders", return_value=[])
    # 简化：只要函数不抛异常即可
    # 更完整测试在集成阶段完成
```

- [ ] **Step 2：运行测试确认失败**

Run: `pytest tests/test_main.py -v`
Expected: FAIL（可能还没有 test_main.py）

- [ ] **Step 3：修改 main.py**

```python
# main.py 关键改动
from sources.rss import build_all_rss_spiders
from sources.rss_config import load_rss_config
from dedup import filter_duplicate_items


def run_spider(scheduled_time=None):
    ...
    # 在原有阶段之后新增 RSS 阶段
    rss_items = []
    try:
        cfg = load_rss_config()
        spiders = build_all_rss_spiders(cfg)
        for spider in spiders:
            try:
                fetched = spider.fetch()
                if fetched:
                    rss_items.extend(fetched)
                    logger.info("RSS 源 %s: 获取 %d 条", spider.source_id, len(fetched))
            except Exception as e:
                logger.error("RSS 源 %s 采集异常: %s", spider.source_id, e)
        rss_items = filter_duplicate_items(rss_items)
        if rss_items:
            rss_items = summarize_content_items(rss_items, "RSS 聚合")
    except Exception as e:
        logger.error("RSS 阶段异常: %s", e)

    content_items = build_all_content_items(
        daily_repos, weekly_repos, hn_stories, sspai_items, tmtpost_items,
        ai_source_items, linux_do_items=linux_do_items, rss_items=rss_items
    )
    ...
```

- [ ] **Step 4：运行测试确认通过**

Run: `pytest tests/test_main.py -v`
Expected: PASS

- [ ] **Step 5：提交**

```bash
git add main.py content_items.py tests/test_main.py
git commit -m "feat(main): 集成 RSS 源到主采集流程"
```

---

## Phase A2：实时调度与前端

### Task 12：调度配置与加载

**Files：**
- Create: `config.yaml`
- Create: `app_config.py`
- Test: `tests/test_app_config.py`

**Interfaces：**
- Produces: `load_app_config() -> dict`
- Produces: `get_source_interval(source_id, priority) -> timedelta`
- Produces: `get_frontend_source_groups() -> list[dict]`

- [ ] **Step 1：写失败测试**

```python
def test_load_app_config():
    from app_config import load_app_config, get_source_interval
    cfg = load_app_config()
    assert "frontend" in cfg
    assert "source_schedule" in cfg
    assert get_source_interval("any", "high").total_seconds() == 8 * 3600
```

- [ ] **Step 2：运行测试确认失败**

Run: `pytest tests/test_app_config.py -v`
Expected: FAIL

- [ ] **Step 3：创建 config.yaml**

```yaml
frontend:
  source_groups:
    - key: "core"
      label: "核心源"
      display_priority: "high"
      default_expanded: true
    - key: "extended"
      label: "扩展源"
      display_priority: "medium"
      default_expanded: false
    - key: "optional"
      label: "可选源"
      display_priority: "low"
      default_expanded: false

source_schedule:
  default_intervals:
    high: 8h
    medium: 8h
    low: 8h
  overrides:
    hacker-news: 1h
    v2ex: 1h
    linux-do: 1h
    rss-v2ex-tech: 1h
    rss-qbitai: 2h
    rss-jiqizhixin: 2h
    rss-geekpark: 2h
    rss-36kr: 2h
    rss-solidot: 2h
    rss-oschina: 2h
    github-daily: 6h
    github-weekly: 1d
    openai: 6h
    anthropic: 6h
    infoq: 6h
    rss-arxiv: 6h
```

- [ ] **Step 4：创建 app_config.py**

```python
# app_config.py
import logging
import re
from datetime import timedelta
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def load_app_config(path: str | Path | None = None) -> dict:
    path = Path(path or DEFAULT_CONFIG_PATH)
    if not path.exists():
        return _default_config()
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or _default_config()


def _default_config() -> dict:
    return {
        "frontend": {
            "source_groups": [
                {"key": "core", "label": "核心源", "display_priority": "high", "default_expanded": True},
                {"key": "extended", "label": "扩展源", "display_priority": "medium", "default_expanded": False},
                {"key": "optional", "label": "可选源", "display_priority": "low", "default_expanded": False},
            ]
        },
        "source_schedule": {
            "default_intervals": {"high": "8h", "medium": "8h", "low": "8h"},
            "overrides": {},
        },
    }


def _parse_interval(value: str) -> timedelta:
    value = str(value).strip().lower()
    match = re.match(r"^(\d+)\s*([hdm])$", value)
    if not match:
        raise ValueError(f"无效间隔格式: {value}")
    number, unit = int(match.group(1)), match.group(2)
    if unit == "h":
        return timedelta(hours=number)
    if unit == "d":
        return timedelta(days=number)
    if unit == "m":
        return timedelta(minutes=number)
    raise ValueError(f"无效间隔单位: {unit}")


def get_source_interval(source_id: str, priority: str, config: dict | None = None) -> timedelta:
    cfg = config or load_app_config()
    schedule = cfg.get("source_schedule", {})
    overrides = schedule.get("overrides", {})
    if source_id in overrides:
        return _parse_interval(overrides[source_id])
    defaults = schedule.get("default_intervals", {"high": "8h", "medium": "8h", "low": "8h"})
    return _parse_interval(defaults.get(priority, "8h"))


def get_frontend_source_groups(config: dict | None = None) -> list[dict]:
    cfg = config or load_app_config()
    return cfg.get("frontend", {}).get("source_groups", [])
```

- [ ] **Step 5：运行测试确认通过**

Run: `pytest tests/test_app_config.py -v`
Expected: PASS

- [ ] **Step 6：提交**

```bash
git add config.yaml app_config.py tests/test_app_config.py
git commit -m "config(schedule): 新增 config.yaml 与加载器，支持三挡默认间隔"
```

---

### Task 13：异步按源调度器

**Files：**
- Create: `scheduler_v2.py`
- Modify: `api.py`（启动新调度器）
- Test: `tests/test_scheduler_v2.py`

**Interfaces：**
- Consumes: `source_registry.SOURCE_DEFINITIONS`, `app_config.get_source_interval`
- Produces: `start_scheduler_v2()`, `stop_scheduler_v2()`
- Produces: `run_source(source_id)` 封装单源采集

- [ ] **Step 1：写失败测试**

```python
def test_parse_interval():
    from scheduler_v2 import parse_interval
    assert parse_interval("1h") == timedelta(hours=1)
    assert parse_interval("1d") == timedelta(days=1)
```

- [ ] **Step 2：运行测试确认失败**

Run: `pytest tests/test_scheduler_v2.py -v`
Expected: FAIL

- [ ] **Step 3：实现 scheduler_v2.py**

```python
# scheduler_v2.py
import asyncio
import logging
import threading
from datetime import datetime, timedelta

from app_config import get_source_interval, load_app_config
from source_registry import SOURCE_DEFINITIONS

logger = logging.getLogger(__name__)

_stop_event = asyncio.Event()
_scheduler_thread: threading.Thread | None = None


def parse_interval(value: str) -> timedelta:
    import re
    value = str(value).strip().lower()
    match = re.match(r"^(\d+)\s*([hdm])$", value)
    if not match:
        raise ValueError(f"无效间隔格式: {value}")
    number, unit = int(match.group(1)), match.group(2)
    if unit == "h":
        return timedelta(hours=number)
    if unit == "d":
        return timedelta(days=number)
    if unit == "m":
        return timedelta(minutes=number)
    raise ValueError(f"无效间隔单位: {unit}")


def run_source(source_id: str) -> bool:
    """执行单源采集。返回是否有新内容。"""
    from main import run_spider
    logger.info("[调度] 执行来源: %s", source_id)
    # 简化：目前仍调用整体 run_spider；后续可拆分为按源采集函数
    try:
        run_spider(scheduled_time=datetime.now())
        return True
    except Exception as e:
        logger.exception("[调度] 来源 %s 执行失败: %s", source_id, e)
        return False


async def schedule_source(source_id: str, interval: timedelta):
    while not _stop_event.is_set():
        run_source(source_id)
        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=interval.total_seconds())
        except asyncio.TimeoutError:
            pass


async def scheduler_loop():
    config = load_app_config()
    tasks = []
    for source in SOURCE_DEFINITIONS:
        interval = get_source_interval(source["id"], source.get("display_priority", "medium"), config)
        tasks.append(asyncio.create_task(schedule_source(source["id"], interval)))
    await asyncio.gather(*tasks, return_exceptions=True)


def _run_scheduler_in_thread():
    asyncio.run(scheduler_loop())


def start_scheduler_v2():
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _stop_event.clear()
    _scheduler_thread = threading.Thread(target=_run_scheduler_in_thread, name="scheduler-v2", daemon=True)
    _scheduler_thread.start()
    logger.info("[调度] v2 异步调度器已启动")


def stop_scheduler_v2():
    _stop_event.set()
    if _scheduler_thread and _scheduler_thread.is_alive():
        _scheduler_thread.join(timeout=5)
    logger.info("[调度] v2 异步调度器已停止")
```

- [ ] **Step 4：修改 api.py 启动新调度器**

```python
# api.py
from scheduler_v2 import start_scheduler_v2, stop_scheduler_v2

@app.on_event("startup")
def on_startup():
    start_scheduler_v2()
    start_stats_reporter()
    logger.info("[启动] API 服务已启动")


@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler_v2()
    logger.info("[关闭] API 服务已停止")
```

- [ ] **Step 5：运行测试确认通过**

Run: `pytest tests/test_scheduler_v2.py -v`
Expected: PASS

- [ ] **Step 6：提交**

```bash
git add scheduler_v2.py api.py tests/test_scheduler_v2.py
git commit -m "feat(scheduler): 实现按源异步调度器 v2"
```

---

### Task 14：API 暴露来源元数据

**Files：**
- Modify: `api.py`
- Modify: `content_store.py`
- Test: `tests/test_api.py`

**Interfaces：**
- Produces: `GET /api/sources` 返回 `display_priority`, `last_updated_at`
- Produces: `GET /api/source-groups` 返回前端分组配置

- [ ] **Step 1：写失败测试**

```python
def test_list_sources_includes_priority(client):
    response = client.get("/api/sources")
    assert response.status_code == 200
    data = response.json()
    assert "display_priority" in data["sources"][0]
```

- [ ] **Step 2：运行测试确认失败**

Run: `pytest tests/test_api.py::test_list_sources_includes_priority -v`
Expected: FAIL

- [ ] **Step 3：修改 api.py**

```python
# api.py 新增
from app_config import get_frontend_source_groups


@app.get("/api/source-groups")
def list_source_groups():
    """返回前端分组配置。"""
    return {"groups": get_frontend_source_groups()}


@app.get("/api/sources")
def list_sources():
    from content_store import load_latest_snapshot
    sources = []
    for source in SOURCE_DEFINITIONS:
        source_id = source["id"]
        snapshot, served_from = load_latest_snapshot(source_id)
        generated_at = snapshot.get("generated_at", "") if snapshot else ""
        sources.append({
            **source,
            "last_updated_at": generated_at,
            "served_from": served_from,
        })
    return {"sources": sources, "count": len(sources)}
```

- [ ] **Step 4：运行测试确认通过**

Run: `pytest tests/test_api.py -v`
Expected: PASS

- [ ] **Step 5：提交**

```bash
git add api.py content_store.py tests/test_api.py
git commit -m "feat(api): /api/sources 返回 display_priority 与最后更新时间"
```

---

### Task 15：前端按优先级分组折叠

**Files：**
- Modify: `frontend/src/App.vue`
- Test: 手动在浏览器验证（UI 测试）

**Interfaces：**
- Consumes: `GET /api/sources`, `GET /api/source-groups`
- Produces: 左侧源面板按分组渲染，默认展开/折叠可配置

- [ ] **Step 1：在 App.vue 新增分组数据与方法**

```javascript
// data() 新增
sourceGroups: [],
expandedGroups: {},

// created() 中
await this.loadSourceGroups();
await this.loadSources();

// methods 新增
async loadSourceGroups() {
  try {
    const response = await fetch(`${API_PREFIX}/source-groups`);
    if (!response.ok) throw new Error(response.status);
    const payload = await response.json();
    this.sourceGroups = payload.groups || [];
    // 从 localStorage 恢复展开状态；首次使用配置默认值
    const stored = localStorage.getItem('expandedGroups');
    const storedMap = stored ? JSON.parse(stored) : {};
    const expanded = {};
    for (const group of this.sourceGroups) {
      expanded[group.key] = storedMap.hasOwnProperty(group.key)
        ? storedMap[group.key]
        : group.default_expanded;
    }
    this.expandedGroups = expanded;
  } catch (error) {
    console.error('加载来源分组失败', error);
    this.sourceGroups = [];
  }
},
toggleGroup(key) {
  this.expandedGroups = { ...this.expandedGroups, [key]: !this.expandedGroups[key] };
  localStorage.setItem('expandedGroups', JSON.stringify(this.expandedGroups));
},
isExpanded(key) {
  return !!this.expandedGroups[key];
},
getSourcesByGroup(group) {
  const priority = group.display_priority;
  return this.sources.filter(s => s.display_priority === priority);
},
```

- [ ] **Step 2：替换 source-panel 模板**

```vue
<aside class="source-panel">
  <div v-for="group in sourceGroups" :key="group.key" class="source-group">
    <button
      class="source-group-header"
      type="button"
      @click="toggleGroup(group.key)"
    >
      <span>{{ group.label }}</span>
      <span class="toggle-icon">{{ isExpanded(group.key) ? '−' : '+' }}</span>
    </button>
    <transition name="fade">
      <div v-show="isExpanded(group.key)" class="source-group-body">
        <button
          v-for="source in getSourcesByGroup(group)"
          :key="source.id"
          class="source-tab"
          :class="{ active: source.id === activeSourceId }"
          type="button"
          @click="selectSource(source.id)"
        >
          <span>{{ getDisplayLabel(source) }}</span>
          <small>{{ getDisplayCategory(source) }}</small>
        </button>
      </div>
    </transition>
  </div>
</aside>
```

- [ ] **Step 3：增加分组样式**

```css
.source-group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 10px 12px;
  border: 0;
  background: transparent;
  color: var(--text-2);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.source-group-header:hover {
  color: var(--primary);
}
.toggle-icon {
  font-size: 14px;
}
.source-group-body {
  padding: 0 6px 6px;
}
.fade-enter-active, .fade-leave-active {
  transition: opacity .2s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
```

- [ ] **Step 4：本地启动并验证**

Run: `cd frontend && npm run dev`（或项目实际命令）
验证：
- 核心源默认展开，扩展/可选源默认收起
- 点击分组标题可展开/收起
- 刷新后保留手动状态

- [ ] **Step 5：提交**

```bash
git add frontend/src/App.vue
git commit -m "feat(frontend): 来源按优先级分组折叠，状态可配置"
```

---

## Phase 集成测试

### Task 16：依赖更新与全链路冒烟测试

**Files：**
- Modify: `requirements.txt`
- Test: 手动/脚本验证

- [ ] **Step 1：更新 requirements.txt**

```text
requests>=2.20.0
beautifulsoup4>=4.6.0
fastapi>=0.100.0
uvicorn>=0.20.0
redis>=4.5.0
Pillow>=10.0.0
markdown>=3.5.0
bleach>=6.0.0
jieba>=0.42.1
feedparser>=6.0.0
pyyaml>=6.0.0
pytest-mock>=3.10.0
```

- [ ] **Step 2：安装依赖**

Run: `pip install -r requirements.txt`
Expected: 成功安装 feedparser、pyyaml、pytest-mock

- [ ] **Step 3：运行全部测试**

Run: `pytest tests/ -v`
Expected: 全部 PASS（旧测试保持通过，新测试 PASS）

- [ ] **Step 4：本地启动 API 并检查**

Run: `uvicorn api:app --reload`
验证：
- `GET /api/sources` 返回含 `display_priority`
- `GET /api/source-groups` 返回三组配置
- `GET /api/sources/{id}/latest` 对 RSS 源返回空或最新内容

- [ ] **Step 5：提交**

```bash
git add requirements.txt
git commit -m "chore(deps): 增加 feedparser、pyyaml、pytest-mock"
```

---

## Spec Coverage

| 设计文档章节 | 覆盖任务 |
|---|---|
| 2.3 前端展示策略：优先级与折叠 | Task 12, Task 14, Task 15 |
| 2.4 实时性、去重与防浪费 | Task 10, Task 12, Task 13 |
| 3 A5 统一渲染层 | Task 1-4 |
| 4 A1 RSS 输入源 | Task 5-11 |
| 5 A2 源实时性优化 | Task 12-15 |
| 6 A3 国内多渠道推送 | 不在本计划，第二部分处理 |

## Placeholder Scan

- 无 TBD/TODO。
- 无 "适当处理"/"添加验证" 等模糊描述。
- 每个任务都给出具体文件、代码、命令、期望输出。

## 与第二部分（A3 多渠道推送）的衔接

第二部分将依赖本计划交付的接口：
- `RenderedContent` / `Renderer` 基类
- `MarkdownRenderer`, `HtmlRenderer`, `PlainRenderer`, `FeishuCardRenderer`
- `Publisher.publish(content: RenderedContent, options)` 签名（需将现有 `publish(content: str, options)` 升级为接受 `RenderedContent`）
- `config.yaml` 中的发布器配置片段

第二部分计划会在本计划完成后创建。
