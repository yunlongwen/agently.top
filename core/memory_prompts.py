# -*- coding: utf-8 -*-
"""
分层记忆系统相关的 LLM Prompt 模板。
"""


def daily_trend_extraction_prompt(source_label: str, items_text: str) -> str:
    """
    从当日某来源的资讯中提取核心主题（L1 每日趋势记忆）。
    """
    return (
        "你是 AI 资讯编辑助手。请从以下【{}】今日资讯中提取 3-5 个核心主题。\n\n"
        "输出要求：\n"
        "- topic: 主题名（5-10 字），简洁明确\n"
        "- keywords: 关键词列表（3-5 个），用于主题匹配\n"
        "- count: 涉及条目数\n"
        "- representative_urls: 代表链接（最多 2 个）\n\n"
        "请严格按以下 JSON 格式返回，不要包含 markdown 代码块或任何多余文字：\n"
        '{{"topics": [{{"topic": "...", "keywords": ["..."], "count": 1, "representative_urls": ["..."]}}]}}\n\n'
        "资讯列表：\n{}"
    ).format(source_label, items_text)


def topic_match_prompt(new_title: str, new_summary: str, topics_json: str) -> str:
    """
    判断新报道应合并到已有主题还是新建主题（L2 主题追踪记忆）。
    """
    return (
        "你是 AI 资讯去重助手。请判断以下新报道是否属于某个已有主题。\n\n"
        "已有主题：\n{}\n\n"
        "新报道标题：{}\n"
        "新报道摘要：{}\n\n"
        "输出要求：\n"
        "- action: merge（合并）或 new（新建）\n"
        "- topic_id: 若 merge，填写匹配的 topic_id；若 new，填写空字符串\n"
        "- reason: 简短理由\n\n"
        "判断标准：\n"
        "- 同一产品/模型/公司的同类更新 → merge\n"
        "- 完全不同的产品或事件 → new\n"
        "- 只有轻微关联（如都属于 AI 行业但事件不同）→ new\n\n"
        "请严格按以下 JSON 格式返回，不要包含 markdown 代码块或任何多余文字：\n"
        '{{"action": "merge|new", "topic_id": "...", "reason": "..."}}'
    ).format(topics_json, new_title, new_summary)


def memory_enhanced_summary_prompt(base_prompt: str, memory_context: str) -> str:
    """
    在原有摘要 prompt 基础上追加历史上下文。
    """
    return (
        "{}\n\n"
        "【历史上下文】\n"
        "近 3 日相关报道：\n{}\n\n"
        "注意：\n"
        "- 若本条与上述历史内容高度重复，请在 chinese_summary 首句标注「跟进报道」并说明新进展\n"
        "- 若本条是全新事件，按正常方式摘要，不要强行关联历史\n"
        "- backend_focus 仍按原要求给出后端团队可执行的建议"
    ).format(base_prompt, memory_context)


def memory_insights_prompt(active_topics_json: str) -> str:
    """
    基于活跃主题生成文章开头的「近期趋势回顾」。
    """
    return (
        "你是 AI 资讯编辑。请基于以下近期活跃主题，为每日资讯综述写一段 150 字以内的「近期趋势回顾」。\n\n"
        "要求：\n"
        "- 语言简洁，适合放在文章开头\n"
        "- 点出 2-3 个最值得关注的趋势\n"
        "- 不要提及具体日期，用「近期」「连日来」等词\n"
        "- 直接返回纯文本，不要 markdown、不要 JSON\n\n"
        "活跃主题：\n{}"
    ).format(active_topics_json)
