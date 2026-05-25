"""
测试结果数据收集模块

用于从 Allure 生成的测试报告中提取测试结果统计数据，
为企微通知提供简洁的测试结果描述。
"""

import json
import re
from pathlib import Path


def get_test_result_summary(report_dir="output/report"):
    """
    从 Allure 报告中获取测试结果汇总数据

    Args:
        report_dir (str): Allure 报告目录路径，默认为 "output/report"

    Returns:
        dict: 包含测试结果统计的字典，包含以下字段：
            - total: 总用例数
            - passed: 通过用例数
            - failed: 失败用例数
            - broken: 故障用例数
            - skipped: 跳过用例数
            - success_rate: 成功率(%)
    """
    try:
        # 构建 summary.json 文件路径
        summary_file = Path(report_dir) / "widgets" / "summary.json"

        # 检查文件是否存在
        if not summary_file.exists():
            print(f"警告: 测试结果文件不存在: {summary_file}")
            return _get_default_summary()

        # 读取并解析 JSON 文件
        with open(summary_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 提取统计数据
        statistic = data.get("statistic", {})

        total = statistic.get("total", 0)
        passed = statistic.get("passed", 0)
        failed = statistic.get("failed", 0)
        broken = statistic.get("broken", 0)
        skipped = statistic.get("skipped", 0)

        # 计算成功率
        success_rate = round((passed / total * 100) if total > 0 else 0, 1)

        result = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "broken": broken,
            "skipped": skipped,
            "success_rate": success_rate,
        }

        # print(f"测试结果统计: {result} %")
        return result

    except Exception as e:
        print(f"获取测试结果失败: {str(e)}")
        return _get_default_summary()


def _get_default_summary():
    """返回默认的测试结果汇总数据"""
    return {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "broken": 0,
        "skipped": 0,
        "success_rate": 0.0,
    }


def _extract_req_ids_from_text(text: str) -> list[str]:
    """从文本中提取所有 reqId"""
    if not text:
        return []
    pattern = r'["\']reqId["\']\s*:\s*["\']([^"\']+)["\']'
    return re.findall(pattern, text)


def _get_req_id_for_failed_case(
    error_message: str, error_trace: str, attachment_path: str
) -> str:
    """
    获取失败用例对应的 reqId

    提取策略：
    1. 优先从错误信息中提取（断言失败时 pytest 会打印实际响应）
    2. 从日志附件中提取，检测最后一个请求是否有响应

    Returns:
        str: reqId / "NO_RESPONSE"（接口无响应） / ""（未找到）
    """
    # 策略1：从错误信息/堆栈中提取
    error_text = f"{error_message}\n{error_trace}"
    req_ids = _extract_req_ids_from_text(error_text)
    if req_ids:
        return req_ids[-1]

    # 策略2：从日志附件中提取
    if not attachment_path:
        return ""

    try:
        attachment_file = Path(attachment_path)
        if not attachment_file.exists():
            return ""

        log_content = attachment_file.read_text(encoding="utf-8")
        if not log_content:
            return ""

        # 找最后一个 HTTP 请求的位置
        # 格式: POST_9b2f208a | 🌐 【HTTP请求】POST http://xxx
        request_matches = list(re.finditer(r"🌐\s*【HTTP请求】", log_content))
        if not request_matches:
            # 没有请求记录，直接取最后一个 reqId
            req_ids = _extract_req_ids_from_text(log_content)
            return req_ids[-1] if req_ids else ""

        # 取最后一个请求之后的日志内容
        log_after_last_request = log_content[request_matches[-1].start() :]

        # 检查是否有响应（📄 【响应内容】或 📋 【解密后响应JSON】）
        has_response = bool(
            re.search(r"【响应内容】|【解密后响应JSON】", log_after_last_request)
        )
        if not has_response:
            return "NO_RESPONSE"

        # 从响应中提取 reqId
        req_ids = _extract_req_ids_from_text(log_after_last_request)
        return req_ids[0] if req_ids else ""

    except Exception as e:
        print(f"警告: 提取reqId失败 {attachment_path}: {e}")
        return ""


def format_test_result_desc(summary_data):
    """
    格式化测试结果描述，用于企微通知

    Args:
        summary_data (dict): 测试结果统计数据

    Returns:
        str: 格式化的测试结果描述
    """
    if not summary_data or summary_data["total"] == 0:
        return "无测试数据"

    total = summary_data["total"]
    passed = summary_data["passed"]
    failed = summary_data["failed"]
    broken = summary_data["broken"]
    skipped = summary_data["skipped"]

    # 构建描述组件
    desc_parts = [f"共{total}"]

    # 添加成功数量
    if passed > 0:
        desc_parts.append(f"｜成功{passed}")

    # 添加失败数量（如果有）
    if failed > 0 or broken > 0:
        desc_parts.append(f"｜失败{failed + broken}")

    # 添加跳过数量（如果有）
    if skipped > 0:
        desc_parts.append(f"｜跳过{skipped}")

    # 拼接描述
    desc = "".join(desc_parts)

    # # 确保不超过15个字符
    # if len(desc) > 15:
    #     if skipped > 0 and len(desc) > 15:
    #         # 如果有跳过且描述过长，需要省略跳过
    #         desc = f"共{total}｜成功{passed}"
    #         if failed > 0 or broken > 0:
    #             desc += f"｜失败{failed + broken}"

    return desc


def get_failed_test_cases(report_dir="output/report"):
    """
    从 Allure 报告中获取所有失败的测试用例详细信息

    只包含 failed 和 broken 状态的用例，不包含 skipped（跳过）的用例

    Args:
        report_dir (str): Allure 报告目录路径，默认为 "output/report"

    Returns:
        list[dict]: 失败用例列表，每个用例包含以下字段：
            - name: 用例名称
            - case_id: 用例ID
            - status: 状态(failed/broken)
            - error_message: 错误信息
            - error_trace: 错误堆栈(简化版)
            - full_name: 完整路径
            - duration: 执行时长(秒)
            - req_id: 失败接口的 reqId（用于研发排查问题）
    """
    failed_cases = []
    # 用于去重：记录每个用例的最后一次执行结果
    # key: historyId, value: case_data
    case_history_map = {}

    # 附件目录路径
    attachments_dir = Path(report_dir) / "data" / "attachments"

    try:
        # 构建测试用例数据目录路径
        test_cases_dir = Path(report_dir) / "data" / "test-cases"

        # 检查目录是否存在
        if not test_cases_dir.exists():
            print(f"警告: 测试用例数据目录不存在: {test_cases_dir}")
            return failed_cases

        # 遍历所有测试用例 JSON 文件
        for case_file in test_cases_dir.glob("*.json"):
            try:
                with open(case_file, "r", encoding="utf-8") as f:
                    case_data = json.load(f)

                # 获取用例的唯一标识（historyId）
                history_id = case_data.get("historyId", "")
                if not history_id:
                    # 如果没有historyId，使用fullName作为标识
                    history_id = case_data.get("fullName", case_file.name)

                # 获取用例执行时间（用于判断哪次是最新的）
                time_info = case_data.get("time", {})
                start_time = time_info.get("start", 0)

                # 如果这个用例之前没见过，或者这次执行时间更晚，就更新记录
                if history_id not in case_history_map or start_time > case_history_map[
                    history_id
                ].get("time", {}).get("start", 0):
                    case_history_map[history_id] = case_data

            except Exception as e:
                print(f"警告: 解析用例文件失败 {case_file}: {str(e)}")
                continue

        # 从去重后的用例中提取失败的用例
        for history_id, case_data in case_history_map.items():
            try:
                # 只处理失败的用例（failed/broken），跳过 passed 和 skipped
                status = case_data.get("status", "")
                if status in ["failed", "broken"]:
                    # 提取用例ID（从labels中的tag字段）
                    case_id = ""
                    for label in case_data.get("labels", []):
                        if label.get("name") == "tag" and "用例ID:" in label.get(
                            "value", ""
                        ):
                            case_id = (
                                label.get("value", "").replace("用例ID:", "").strip()
                            )
                            break

                    # 提取错误信息
                    error_message = case_data.get("statusMessage", "未知错误")
                    error_trace = case_data.get("statusTrace", "")

                    # 简化错误堆栈，只保留关键行
                    simplified_trace = _simplify_error_trace(error_trace)

                    # 计算执行时长（毫秒转秒）
                    duration_ms = case_data.get("time", {}).get("duration", 0)
                    duration_sec = round(duration_ms / 1000, 2)

                    # 提取 reqId：优先从错误信息中提取，备选从日志附件提取
                    attachment_path = ""
                    test_stage = case_data.get("testStage", {})
                    attachments = test_stage.get("attachments", [])
                    if attachments:
                        attachment = attachments[0]
                        attachment_source = attachment.get("source", "")
                        if attachment_source:
                            attachment_path = str(attachments_dir / attachment_source)

                    req_id = _get_req_id_for_failed_case(
                        error_message=error_message,
                        error_trace=error_trace,
                        attachment_path=attachment_path,
                    )

                    failed_case = {
                        "name": case_data.get("name", "未知用例"),
                        "case_id": case_id,
                        "status": status,
                        "error_message": error_message,
                        "error_trace": simplified_trace,
                        "full_name": case_data.get("fullName", ""),
                        "duration": duration_sec,
                        "req_id": req_id,
                    }

                    failed_cases.append(failed_case)

            except Exception as e:
                print(f"警告: 处理用例数据失败: {str(e)}")
                continue

        return failed_cases

    except Exception as e:
        print(f"获取失败用例列表失败: {str(e)}")
        return failed_cases


def _simplify_error_trace(trace: str, max_lines: int = 3) -> str:
    """
    简化错误堆栈信息，只保留最关键的几行

    Args:
        trace: 完整的错误堆栈
        max_lines: 最多保留的行数

    Returns:
        简化后的错误堆栈
    """
    if not trace:
        return ""

    lines = trace.split("\n")

    # 只保留包含关键信息的行
    key_lines = []
    for line in lines:
        line = line.strip()
        if line and (
            line.startswith("E ")  # pytest 错误行
            or "assert" in line.lower()  # 断言相关
            or ".py:" in line  # 文件位置
        ):
            key_lines.append(line)
            if len(key_lines) >= max_lines:
                break

    return "\n".join(key_lines) if key_lines else trace[:200]


def format_failed_cases_message(failed_cases: list[dict]) -> str:
    """
    格式化失败用例信息为企微通知消息

    Args:
        failed_cases: 失败用例列表

    Returns:
        格式化的失败用例消息
    """
    if not failed_cases:
        return ""

    # 按状态分组
    status_map = {
        "failed": "❌ 失败",
        "broken": "💔 故障",
        "skipped": "⏭️ 跳过",
    }

    messages = []
    messages.append(f"\n\n{'=' * 40}")
    messages.append(f"📋 失败用例详情（共{len(failed_cases)}个）")
    messages.append(f"{'=' * 40}\n")

    for idx, case in enumerate(failed_cases, 1):
        status_icon = status_map.get(case["status"], "⚠️ 异常")

        messages.append(f"{idx}. {status_icon} {case['name']}")

        if case["case_id"]:
            messages.append(f"   📝 用例ID: {case['case_id']}")

        messages.append(f"   🔍 状态: {case['status']}")
        messages.append(f"   ⏱️ 耗时: {case['duration']}秒")
        messages.append(f"   💬 错误: {case['error_message']}")

        if case["error_trace"]:
            # 错误堆栈每行缩进
            trace_lines = case["error_trace"].split("\n")
            for trace_line in trace_lines:
                messages.append(f"      {trace_line}")

        messages.append("")  # 空行分隔

    return "\n".join(messages)


def main():
    """
    主函数，用于命令行测试
    """
    # 获取测试结果
    summary = get_test_result_summary()

    # 获取描述
    desc = format_test_result_desc(summary)

    # 打印描述（供 CI 捕获 - 第一行）
    print(desc)

    has_failures = summary.get("failed", 0) + summary.get("broken", 0) > 0

    if has_failures:
        failed_cases = get_failed_test_cases()

        # 如果有失败用例，打印失败详情（供企微通知使用）
        if failed_cases:
            # 输出失败用例数量
            print(f"<<<FAILED_CASES_COUNT:{len(failed_cases)}>>>")

            # 输出每个失败用例的详情（用特殊分隔符）
            for idx, case in enumerate(failed_cases):
                print(f"<<<FAILED_CASE_{idx}_START>>>")
                print(json.dumps(case, ensure_ascii=False))
                print(f"<<<FAILED_CASE_{idx}_END>>>")

    return desc


if __name__ == "__main__":
    main()
