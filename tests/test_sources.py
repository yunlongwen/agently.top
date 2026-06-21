def test_source_spider_abstract():
    from sources.base import SourceSpider
    import inspect
    assert inspect.isabstract(SourceSpider)
