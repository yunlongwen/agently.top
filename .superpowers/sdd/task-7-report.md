## Task 7 报告

### 变更
- 新建 `sources/base.py`：定义 `SourceSpider` 抽象基类，包含抽象属性 `source_id`、`name`，抽象方法 `fetch`，以及默认属性 `display_priority`、`category`、`enabled`。
- 新建 `tests/test_sources.py`：添加 `test_source_spider_abstract` 测试，验证 `SourceSpider` 为抽象类。

### 测试命令
```bash
PYTHONPATH=. pytest tests/test_sources.py -v
```

### 测试输出
```
============================= test session starts =============================
platform win32 -- Python 3.11.6, pytest-8.3.0, pluggy-1.6.0
collected 1 item

tests/test_sources.py::test_source_spider_abstract PASSED                [100%]

============================== 1 passed in 0.04s ==============================
```

### 结果
- 状态：DONE
- 测试：1 passed
