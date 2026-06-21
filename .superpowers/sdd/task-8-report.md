# Task 8 报告：RSS Spider 实现

## 变更文件

1. `sources/rss.py`（新建）
   - 实现 `RssSpider`，继承自 `SourceSpider`
   - 包含属性 `source_id`、`name`、`display_priority`、`category`、`enabled`
   - `fetch()` 使用 `requests` 请求 RSS URL（带重试），`feedparser` 解析，按 `max_age_days` 和 `max_items` 过滤，返回标准化内容项
   - 辅助函数 `_parse_published`、`_normalize_url`
   - `build_all_rss_spiders(config_path=None) -> list[RssSpider]` 工厂函数

2. `requirements.txt`
   - 新增 `feedparser>=6.0.0`

3. `tests/test_sources.py`
   - 新增 `test_rss_spider_parses_feed`，使用 `unittest.mock.patch` 模拟 `requests.get` 和 `feedparser.parse`

## 测试命令

```bash
PYTHONPATH=. pytest tests/test_sources.py -v
```

## 测试输出

```
============================= test session starts =============================
platform win32 -- Python 3.11.6, pytest-8.3.0, pluggy-1.6.0 -- D:\Program Files\Python311\python.exe
cachedir: .pytest_cache
rootdir: D:\ai-workspace\github\agently.top\.claude\worktrees\milestone-a-part1
plugins: anyio-4.11.0, asyncio-0.24.0
asyncio: mode=Mode.STRICT, default_loop_scope=None
collecting ... collected 2 items

tests/test_sources.py::test_source_spider_abstract PASSED                [ 50%]
tests/test_sources.py::test_rss_spider_parses_feed PASSED                [100%]

============================== 2 passed in 0.47s ==============================
```

## 提交

- 提交信息：`feat(sources): 实现 RSS 采集蜘蛛 RssSpider`
