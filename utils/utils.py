import os
import datetime

import jmespath

from core.enums import ProjectPath


def get_worker_id():
    """
    获取当前进程的 worker id
    :return: worker id
    """
    return os.environ.get("PYTEST_XDIST_WORKER", "master")


def get_current_time(fmt: str = "datetime") -> str:
    """
    获取当前时间的标准化格式字符串

    Args:
        fmt (str): 时间格式类型
            - "datetime": 完整日期时间格式 "2024-11-22 18:12:33"（默认）
            - "date": 仅日期格式 "2024-11-22"
            - "time": 仅时间格式 "18:12:33"
            - 或者直接传入自定义格式字符串，如 "%Y/%m/%d"

    Returns:
        str: 格式化后的时间字符串
    """
    format_mapping = {
        "datetime": "%Y-%m-%d %H:%M:%S",
        "date": "%Y-%m-%d",
        "time": "%H:%M:%S",
    }

    # 如果是预定义的格式类型，则使用映射；否则直接作为格式字符串使用
    time_format = format_mapping.get(fmt, fmt)
    return datetime.datetime.now().strftime(time_format)


def get_future_time(
    days: int = 0, hours: int = 0, minutes: int = 0, fmt: str = "datetime"
) -> str:
    """
    获取未来某个时间点的标准化格式字符串

    Args:
        days (int): 增加的天数，默认 0
        hours (int): 增加的小时数，默认 0
        minutes (int): 增加的分钟数，默认 0
        fmt (str): 时间格式类型
            - "datetime": 完整日期时间格式 "2024-11-22 18:12:33"（默认）
            - "date": 仅日期格式 "2024-11-22"
            - "time": 仅时间格式 "18:12:33"
            - 或者直接传入自定义格式字符串，如 "%Y/%m/%d"

    Returns:
        str: 格式化后的时间字符串

    Examples:
        >>> get_future_time(days=7)  # 7天后
        '2024-11-29 18:12:33'
        >>> get_future_time(days=30, fmt="date")  # 30天后的日期
        '2024-12-22'
    """
    format_mapping = {
        "datetime": "%Y-%m-%d %H:%M:%S",
        "date": "%Y-%m-%d",
        "time": "%H:%M:%S",
    }

    future_time = datetime.datetime.now() + datetime.timedelta(
        days=days, hours=hours, minutes=minutes
    )
    time_format = format_mapping.get(fmt, fmt)
    return future_time.strftime(time_format)


def merge_worker_logs():
    """合并所有worker进程的日志文件到主日志文件中"""
    from datetime import datetime
    import glob
    import shutil

    date_str = datetime.now().strftime("%Y-%m-%d")
    log_dir = ProjectPath.LOG_PATH.value
    main_log_file = f"{log_dir}/{date_str}.log"

    # 查找所有worker日志文件
    worker_log_pattern = f"{log_dir}/{date_str}_*.log"
    worker_log_files = glob.glob(worker_log_pattern)

    if not worker_log_files:
        return

    try:
        # 以追加模式打开主日志文件
        with open(main_log_file, "a", encoding="utf-8") as main_file:
            main_file.write(f"\n{'=' * 80}\n")
            main_file.write(
                f"合并worker进程日志 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            main_file.write(f"{'=' * 80}\n")

            for worker_log_file in sorted(worker_log_files):
                worker_name = (
                    os.path.basename(worker_log_file)
                    .replace(f"{date_str}_", "")
                    .replace(".log", "")
                )
                main_file.write(f"\n--- Worker: {worker_name} ---\n")

                with open(worker_log_file, "r", encoding="utf-8") as worker_file:
                    shutil.copyfileobj(worker_file, main_file)

                # 删除worker日志文件
                os.remove(worker_log_file)
                # 延迟导入避免循环依赖
                # try:
                #     from core.logger import api_logger as logger

                #     logger.info(f"已合并并删除worker日志文件: {worker_log_file}")
                # except ImportError:
                #     print(f"已合并并删除worker日志文件: {worker_log_file}")
        # try:
        #     from core.logger import api_logger as logger

        #     logger.info(f"所有worker日志已合并到: {main_log_file}")
        # except ImportError:
        #     print(f"所有worker日志已合并到: {main_log_file}")

    except Exception as e:
        try:
            from core.logger import api_logger as logger

            logger.error(f"合并worker日志失败: {e}")
        except ImportError:
            print(f"合并worker日志失败: {e}")


def extract_case_logs_by_blocks(case_id):
    """通过分块方式提取指定用例的完整日志"""
    from datetime import datetime
    import glob

    date_str = datetime.now().strftime("%Y-%m-%d")
    log_dir = ProjectPath.LOG_PATH.value

    # 查找所有可能的日志文件
    log_files = []

    # 主进程日志文件
    main_log_file = f"{log_dir}/{date_str}.log"
    if os.path.exists(main_log_file):
        log_files.append(main_log_file)

    # worker进程日志文件
    worker_log_pattern = f"{log_dir}/{date_str}_*.log"
    worker_log_files = glob.glob(worker_log_pattern)
    log_files.extend(worker_log_files)

    if not log_files:
        return None

    all_case_logs = {}  # 用于存储按时间排序的日志

    try:
        for log_file in log_files:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

                i = 0
                while i < len(lines):
                    line = lines[i]
                    # 找到包含目标用例ID的行
                    if case_id in line:
                        # 提取时间戳用于排序
                        timestamp = extract_timestamp_from_log_line(line)
                        case_block = [line.strip()]
                        i += 1

                        # 收集该用例块的所有日志
                        while i < len(lines):
                            next_line = lines[i]
                            # 如果遇到新的用例ID，停止收集
                            if "case_" in next_line and case_id not in next_line:
                                break
                            case_block.append(next_line.strip())
                            i += 1

                        # 存储到字典中，按时间戳排序
                        if timestamp:
                            all_case_logs[timestamp] = case_block
                    else:
                        i += 1

        # 按时间戳排序并合并所有日志块
        if all_case_logs:
            sorted_logs = []
            for timestamp in sorted(all_case_logs.keys()):
                sorted_logs.extend(all_case_logs[timestamp])
            return "\n".join(sorted_logs)

    except Exception as e:
        try:
            from core.logger import api_logger as logger

            logger.error(f"分块提取日志失败: {e}")
        except ImportError:
            print(f"分块提取日志失败: {e}")
        return None

    return None


def extract_timestamp_from_log_line(line):
    """从日志行中提取时间戳"""
    import re

    # 匹配日志格式中的时间戳 YYYY-MM-DD HH:mm:ss.SSS
    timestamp_pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})"
    match = re.search(timestamp_pattern, line)
    if match:
        return match.group(1)
    return None


def extract_json_field(response_data, path):
    """统一的 json 字段提取方法"""
    return jmespath.search(expression=path, data=response_data)


def generate_timestamp(timestamp_type="milliseconds"):
    """
    生成时间戳的通用函数

    Args:
        timestamp_type (str): 时间戳类型
            - "seconds": 秒级时间戳
            - "milliseconds": 毫秒级时间戳（默认）
            - "microseconds": 微秒级时间戳

    Returns:
        str: 时间戳字符串
    """
    import time

    if timestamp_type == "seconds":
        return str(int(time.time()))
    elif timestamp_type == "milliseconds":
        return str(int(time.time() * 1000))
    elif timestamp_type == "microseconds":
        return str(int(time.time() * 1000000))
    else:
        raise ValueError(f"不支持的时间戳类型: {timestamp_type}")


def get_current_host(app: str = "httpbin") -> str:
    """获取当前环境的主机地址（不包含协议部分，用于 Host 请求头）"""
    from core.config import ConfigLoader

    try:
        config = ConfigLoader.get_instance()
        host = config.get(f"host.{app}_host")
        # 去掉协议部分，只保留域名
        if host:
            host = host.replace("http://", "").replace("https://", "")
        return host
    except Exception:
        from core.logger import api_logger as logger

        return logger.error("获取主机地址失败")


def get_current_env() -> str:
    """获取当前运行环境"""
    from core.config import ConfigLoader

    try:
        config = ConfigLoader.get_instance()
        env = config.get_env()
        return env
    except Exception:
        from core.logger import api_logger as logger

        return logger.error("获取运行环境失败")
