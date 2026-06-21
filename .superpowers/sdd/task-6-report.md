# Task 6 报告

## 变更
- 新建 `sources/__init__.py`，将 `sources/` 设为 Python 包。
- 新建 `sources/rss_config.py`，实现：
  - `load_rss_config(path=None) -> dict`
  - `list_enabled_rss_sources(config) -> list[dict]`
  - `get_rss_request_options(config) -> dict`
- 扩展 `tests/test_rss_config.py`，新增 `test_load_rss_config` 测试用例。

## 测试命令
```bash
PYTHONPATH=. pytest tests/test_rss_config.py -v
```

## 测试输出
```
============================= test session starts =============================
platform win32 -- Python 3.11.6, pytest-8.3.0, pluggy-1.6.0
rootdir: D:\ai-workspace\github\agently.top\.claude\worktrees\milestone-a-part1
collecting ... collected 2 items

tests/test_rss_config.py::test_rss_config_file_exists PASSED             [ 50%]
tests/test_rss_config.py::test_load_rss_config PASSED                    [100%]

============================== 2 passed in 0.21s ==============================
```

## 状态
- 2/2 测试通过。
