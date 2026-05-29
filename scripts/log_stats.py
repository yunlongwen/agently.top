#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志统计脚本 - 分析 API 访问日志

用法：
    python3 scripts/log_stats.py                      # 分析今天的日志
    python3 scripts/log_stats.py 2026-05-29           # 分析指定日期
    python3 scripts/log_stats.py --all                # 分析全部日志
    python3 scripts/log_stats.py --file /path/to.log  # 指定日志文件

日志文件默认路径：/root/logs/github-python/trending.log

输出内容：
    1. 今日访问概览（总请求、独立IP、平均耗时、错误率）
    2. 接口访问排行
    3. IP 访问排行
    4. 数据来源统计（Redis 命中 vs 磁盘降级）
    5. 错误请求列表
    6. 时段分布（按小时统计）
"""

import re
import sys
from collections import defaultdict
from datetime import datetime


# =========================================================================
# 默认配置
# =========================================================================

DEFAULT_LOG_FILE = "/root/logs/github-python/trending.log"


# =========================================================================
# 日志解析
# =========================================================================

def parse_access_log(line):
    """
    解析 [访问] 格式的日志行。

    示例：
    2026-05-29 10:32:15 [INFO] [访问] 来源IP=1.2.3.4 | 请求=GET /api/sources | 状态码=200 | 耗时=45ms | 客户端=Mozilla...

    返回 dict 或 None。
    """
    if "[访问]" not in line:
        return None

    result = {}

    # 提取时间戳
    time_match = re.match(r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})", line)
    if time_match:
        result["日期"] = time_match.group(1)
        result["时间"] = time_match.group(2)
        result["小时"] = time_match.group(2)[:2]
    else:
        return None

    # 提取字段
    ip_match = re.search(r"来源IP=([^\s|]+)", line)
    if ip_match:
        result["IP"] = ip_match.group(1).strip()

    path_match = re.search(r"请求=(\w+)\s+([^\s|]+)", line)
    if path_match:
        result["方法"] = path_match.group(1)
        result["路径"] = path_match.group(2).strip()

    status_match = re.search(r"状态码=(\d+)", line)
    if status_match:
        result["状态码"] = int(status_match.group(1))

    latency_match = re.search(r"耗时=(\d+)ms", line)
    if latency_match:
        result["耗时ms"] = int(latency_match.group(1))

    return result


def parse_data_log(line):
    """
    解析 [数据] 格式的日志行。

    示例：
    2026-05-29 10:32:15 [INFO] [数据] 来源=github-daily | 读取自=Redis缓存 | 条数=10 | 数据生成时间=...

    返回 dict 或 None。
    """
    if "[数据]" not in line:
        return None

    result = {}

    time_match = re.match(r"(\d{4}-\d{2}-\d{2})", line)
    if time_match:
        result["日期"] = time_match.group(1)

    source_match = re.search(r"来源=([^\s|]+)", line)
    if source_match:
        result["来源"] = source_match.group(1).strip()

    served_match = re.search(r"读取自=([^\s|]+)", line)
    if served_match:
        result["读取自"] = served_match.group(1).strip()

    count_match = re.search(r"条数=(\d+)", line)
    if count_match:
        result["条数"] = int(count_match.group(1))

    return result


# =========================================================================
# 统计计算
# =========================================================================

def compute_stats(access_records, data_records):
    """计算统计数据。"""
    stats = {}

    # --- 访问概览 ---
    total = len(access_records)
    stats["总请求数"] = total

    if total == 0:
        return stats

    ips = set(r.get("IP", "") for r in access_records if r.get("IP"))
    stats["独立IP数"] = len(ips)

    latencies = [r["耗时ms"] for r in access_records if "耗时ms" in r]
    if latencies:
        stats["平均耗时ms"] = int(sum(latencies) / len(latencies))
        stats["最大耗时ms"] = max(latencies)
        stats["最小耗时ms"] = min(latencies)
    else:
        stats["平均耗时ms"] = 0

    errors = [r for r in access_records if r.get("状态码", 200) >= 400]
    stats["错误请求数"] = len(errors)
    stats["错误率"] = "{:.1f}%".format(len(errors) / total * 100) if total else "0%"

    # --- 接口排行 ---
    path_counter = defaultdict(int)
    for r in access_records:
        path = r.get("路径", "未知")
        path_counter[path] += 1
    stats["接口排行"] = sorted(path_counter.items(), key=lambda x: x[1], reverse=True)[:10]

    # --- IP 排行 ---
    ip_counter = defaultdict(int)
    for r in access_records:
        ip = r.get("IP", "未知")
        ip_counter[ip] += 1
    stats["IP排行"] = sorted(ip_counter.items(), key=lambda x: x[1], reverse=True)[:10]

    # --- 时段分布（按小时） ---
    hour_counter = defaultdict(int)
    for r in access_records:
        hour = r.get("小时", "??")
        hour_counter[hour] += 1
    stats["时段分布"] = sorted(hour_counter.items())

    # --- 状态码分布 ---
    status_counter = defaultdict(int)
    for r in access_records:
        code = r.get("状态码", 0)
        status_counter[code] += 1
    stats["状态码分布"] = sorted(status_counter.items())

    # --- 数据来源统计 ---
    source_counter = defaultdict(lambda: {"Redis缓存": 0, "磁盘归档": 0, "无数据": 0, "其他": 0})
    for r in data_records:
        source = r.get("来源", "未知")
        served = r.get("读取自", "其他")
        if "Redis" in served:
            source_counter[source]["Redis缓存"] += 1
        elif "磁盘" in served:
            source_counter[source]["磁盘归档"] += 1
        elif "无数据" in served:
            source_counter[source]["无数据"] += 1
        else:
            source_counter[source]["其他"] += 1
    stats["数据来源统计"] = dict(source_counter)

    # --- 错误请求详情 ---
    stats["错误请求详情"] = errors[:20]

    return stats


# =========================================================================
# 输出格式化
# =========================================================================

def print_stats(stats, target_date):
    """格式化输出统计结果。"""
    print("")
    print("=" * 60)
    print("  日志统计报告 - {}".format(target_date or "全部"))
    print("=" * 60)

    total = stats.get("总请求数", 0)
    if total == 0:
        print("")
        print("  该时段没有任何访问记录。")
        print("")
        return

    # 概览
    print("")
    print("  [访问概览]")
    print("  总请求数:    {}".format(total))
    print("  独立IP数:    {}".format(stats.get("独立IP数", 0)))
    print("  平均耗时:    {}ms".format(stats.get("平均耗时ms", 0)))
    print("  最大耗时:    {}ms".format(stats.get("最大耗时ms", 0)))
    print("  最小耗时:    {}ms".format(stats.get("最小耗时ms", 0)))
    print("  错误请求数:  {}".format(stats.get("错误请求数", 0)))
    print("  错误率:      {}".format(stats.get("错误率", "0%")))

    # 接口排行
    print("")
    print("  [接口访问排行 Top 10]")
    for path, count in stats.get("接口排行", []):
        bar = "#" * min(count, 30)
        print("  {:40s} {:>5d}次  {}".format(path, count, bar))

    # IP 排行
    print("")
    print("  [IP 访问排行 Top 10]")
    for ip, count in stats.get("IP排行", []):
        bar = "#" * min(count, 30)
        print("  {:20s} {:>5d}次  {}".format(ip, count, bar))

    # 时段分布
    print("")
    print("  [时段分布（按小时）]")
    for hour, count in stats.get("时段分布", []):
        bar = "#" * min(count, 40)
        print("  {}:00  {:>5d}次  {}".format(hour, count, bar))

    # 状态码分布
    print("")
    print("  [状态码分布]")
    for code, count in stats.get("状态码分布", []):
        print("  {:>3d}  {:>5d}次".format(code, count))

    # 数据来源统计
    data_stats = stats.get("数据来源统计", {})
    if data_stats:
        print("")
        print("  [数据读取来源统计]")
        print("  {:15s} {:>8s} {:>8s} {:>8s}".format(
            "来源", "Redis命中", "磁盘降级", "无数据"
        ))
        print("  " + "-" * 45)
        for source, counts in sorted(data_stats.items()):
            print("  {:15s} {:>8d} {:>8d} {:>8d}".format(
                source,
                counts.get("Redis缓存", 0),
                counts.get("磁盘归档", 0),
                counts.get("无数据", 0),
            ))

    # 错误请求
    errors = stats.get("错误请求详情", [])
    if errors:
        print("")
        print("  [错误请求（前 20 条）]")
        for r in errors:
            print("  {} {} {} → 状态码={}  耗时={}ms  IP={}".format(
                r.get("日期", ""),
                r.get("时间", ""),
                r.get("路径", ""),
                r.get("状态码", "?"),
                r.get("耗时ms", "?"),
                r.get("IP", "?"),
            ))

    print("")
    print("=" * 60)
    print("")


# =========================================================================
# 主入口
# =========================================================================

def main():
    """解析命令行参数并执行统计。"""
    log_file = DEFAULT_LOG_FILE
    target_date = datetime.now().strftime("%Y-%m-%d")
    filter_all = False

    # 解析参数
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--all":
            filter_all = True
        elif arg == "--file" and i + 1 < len(args):
            i += 1
            log_file = args[i]
        elif re.match(r"\d{4}-\d{2}-\d{2}", arg):
            target_date = arg
        else:
            print("未知参数: {}".format(arg))
            print(__doc__)
            sys.exit(1)
        i += 1

    # 读取日志文件
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("日志文件不存在: {}".format(log_file))
        print("你可以用 --file 参数指定日志路径")
        sys.exit(1)
    except PermissionError:
        print("没有权限读取日志文件: {}".format(log_file))
        sys.exit(1)

    print("正在分析日志文件: {}".format(log_file))
    print("日志总行数: {}".format(len(lines)))

    # 解析并过滤
    access_records = []
    data_records = []

    for line in lines:
        # 日期过滤
        if not filter_all:
            if not line.startswith(target_date):
                continue

        access = parse_access_log(line)
        if access:
            access_records.append(access)
            continue

        data = parse_data_log(line)
        if data:
            data_records.append(data)

    print("匹配到访问记录: {} 条".format(len(access_records)))
    print("匹配到数据记录: {} 条".format(len(data_records)))

    # 计算统计
    stats = compute_stats(access_records, data_records)
    display_date = "全部" if filter_all else target_date
    print_stats(stats, display_date)


if __name__ == "__main__":
    main()
