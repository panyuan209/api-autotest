#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送单个失败用例的企业微信通知

Usage:
    send_failed_case_notification.py <test_app> <env> <build_num> <build_url> <case_index>

Arguments:
    test_app    - 测试应用名称 (如 httpbin)
    env         - 测试环境 (test/dev/prod)
    build_num   - 构建编号
    build_url   - 构建URL
    case_index  - 失败用例索引 (从0开始)
"""

import sys
import json
from pathlib import Path


# 应用名称映射
APP_NAMES = {
    "httpbin": "HttpBin",
}

# 状态配置
STATUS_CONFIG = {
    "failed": {"icon": "❌", "color": "warning"},
    "broken": {"icon": "💥", "color": "comment"},
    "unknown": {"icon": "⚠️", "color": "warning"},
}


def read_failed_cases_data(data_file=".failed_cases_data.tmp"):
    """读取失败用例数据文件"""
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Data file '{data_file}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading data file: {e}", file=sys.stderr)
        sys.exit(1)


def extract_case_data(content, case_index):
    """提取指定索引的失败用例JSON数据"""
    start_marker = f"<<<FAILED_CASE_{case_index}_START>>>"
    end_marker = f"<<<FAILED_CASE_{case_index}_END>>>"

    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        print(f"Error: Cannot find case {case_index} markers", file=sys.stderr)
        sys.exit(1)

    json_str = content[start_idx + len(start_marker) : end_idx].strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        sys.exit(1)


def build_markdown_content(data, app_name, env, build_num, build_url):
    """构建企业微信Markdown内容"""
    # 提取字段
    case_name = data.get("name", "未知用例")
    case_id = data.get("case_id", "")
    status = data.get("status", "unknown")
    error_msg = data.get("statusMessage", "") or data.get("error_message", "")
    error_trace = data.get("statusTrace", "") or data.get("error_trace", "")
    duration = data.get("duration", 0)
    req_id = data.get("req_id", "")  # 获取接口响应的 reqId

    # 获取状态配置
    status_cfg = STATUS_CONFIG.get(status, STATUS_CONFIG["unknown"])
    status_icon = status_cfg["icon"]
    status_color = status_cfg["color"]

    # 构建内容
    parts = [
        f"# {status_icon} 【{app_name}】用例失败详情",
        "----------",
        f"**用例名称：** {case_name}",
    ]

    if case_id:
        parts.append(f"**用例ID：** {case_id}")

    parts.extend(
        [
            f'**状态：** <font color="{status_color}">{status}</font>',
            f"**耗时：** {duration}秒",
            f"**环境：** {env}",
            f"**构建：** [#{build_num}]({build_url})",
        ]
    )

    # 添加 reqId 信息（如果有）
    if req_id:
        if req_id == "NO_RESPONSE":
            # 最后一个请求无响应，特殊提示
            parts.append(
                '**reqId：** <font color="warning">接口请求失败，无响应</font>'
            )
        else:
            parts.append(f"**reqId：** `{req_id}`")

    if error_msg:
        parts.append("----------")
        parts.append("**错误信息：**")
        # 移除反引号避免破坏markdown,限制长度
        safe_msg = error_msg.replace("`", "")[:300]
        parts.append(f'<font color="warning">{safe_msg}</font>')

    if error_trace:
        parts.append("")
        parts.append("**错误堆栈：**")
        parts.append("```")
        # 限制长度
        parts.append(error_trace[:500])
        parts.append("```")

    parts.append("----------")
    parts.append(f"[查看报告]({build_url}allure/)")

    return "\n".join(parts)


def save_wechat_message(content, case_index, output_dir="."):
    """保存企业微信消息JSON到文件"""
    message = {"msgtype": "markdown", "markdown": {"content": content}}

    output_file = Path(output_dir) / f"wechat_failed_case_{case_index}.json"

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(message, f, ensure_ascii=False, indent=2)
        return output_file
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    if len(sys.argv) != 6:
        print(__doc__)
        sys.exit(1)

    test_app = sys.argv[1]
    env = sys.argv[2]
    build_num = sys.argv[3]
    build_url = sys.argv[4]
    case_index = int(sys.argv[5])

    # 获取应用显示名称
    app_name = APP_NAMES.get(test_app, test_app)

    # 读取失败用例数据
    content = read_failed_cases_data()

    # 提取指定用例的数据
    data = extract_case_data(content, case_index)

    # 构建Markdown内容
    markdown_content = build_markdown_content(data, app_name, env, build_num, build_url)

    # 保存为JSON文件
    output_file = save_wechat_message(markdown_content, case_index)

    print(f"OK: {output_file}")


if __name__ == "__main__":
    main()
