import os
import json
from datetime import datetime
from loguru import logger
from contextvars import ContextVar
from core.enums import ProjectPath
from typing import Dict, Any


class LogFormatter:
    """日志格式化工具类"""

    # 日志级别对应的图标和颜色
    LEVEL_ICONS = {
        "DEBUG": "🔍",
        "INFO": "📝",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "CRITICAL": "💥",
    }

    # 功能模块图标
    MODULE_ICONS = {
        "framework": "🏗️",
        "config": "⚙️",
        "auth": "🔐",
        "request": "🌐",
        "response": "📬",
        "flow": "🔄",
        "performance": "📊",
        "validation": "✅",
        "error": "💥",
    }

    @staticmethod
    def format_json(data: Any, indent: int = 2) -> str:
        """格式化JSON数据"""
        if isinstance(data, (dict, list)):
            return json.dumps(data, ensure_ascii=False, indent=indent)
        return str(data)

    @staticmethod
    def format_headers(headers: Dict[str, str]) -> str:
        """格式化请求头"""
        if not headers:
            return "无"

        formatted = []
        for key, value in headers.items():
            # 敏感信息脱敏
            if key.lower() in ["authorization", "cookie", "x-api-key"]:
                if len(value) > 20:
                    value = f"{value[:10]}...{value[-6:]}"
                else:
                    value = f"{value[:6]}..."
            formatted.append(f"    {key}: {value}")
        return "\n" + "\n".join(formatted)

    @staticmethod
    def format_params(params: Dict[str, Any]) -> str:
        """格式化请求参数"""
        if not params:
            return "无"

        formatted = []
        for key, value in params.items():
            # 敏感信息脱敏
            if key.lower() in ["password", "secret", "key"]:
                if isinstance(value, str) and len(value) > 10:
                    value = f"{value[:4]}...{value[-3:]}"
                else:
                    value = "***"
            formatted.append(f"    {key}: {value}")
        return "\n" + "\n".join(formatted)

    @staticmethod
    def format_response_body(body: str, max_length: int = 1000) -> str:
        """格式化响应体"""
        if not body:
            return "空响应"

        # 处理bytes类型
        if isinstance(body, bytes):
            try:
                body = body.decode("utf-8")
            except UnicodeDecodeError:
                body = body.decode("utf-8", errors="replace")

        body_str = str(body)

        # 尝试格式化JSON，如果失败就直接返回原内容
        try:
            data = json.loads(body_str)
            formatted = json.dumps(data, ensure_ascii=False, indent=2)
            if len(formatted) > max_length:
                return f"{formatted[:max_length]}...\n[响应体过长，已截断]"
            return formatted
        except (json.JSONDecodeError, TypeError):
            # 非JSON响应，直接返回
            if len(body_str) > max_length:
                return f"{body_str[:max_length]}...\n[响应体过长，已截断]"
            return body_str


class ApiLogger:
    def __init__(self):
        self.log_level = self._get_log_level_from_config()
        self.logger = logger

        # 获取worker_id来创建独立的日志文件
        from utils.utils import get_worker_id

        self.worker_id = get_worker_id()

        # 为每个进程创建独立的日志文件
        date_str = datetime.now().strftime("%Y-%m-%d")
        if self.worker_id == "master":
            self.log_file = f"{ProjectPath.LOG_PATH.value}/{date_str}.log"
        else:
            self.log_file = (
                f"{ProjectPath.LOG_PATH.value}/{date_str}_{self.worker_id}.log"
            )

        # 使用 ContextVar 来存储当前上下文的用例信息
        self._case_name = ContextVar("case_name", default="N/A")
        self._case_id = ContextVar("case_id", default="N/A")
        self._request_id = ContextVar("request_id", default="N/A")
        # 缓存绑定的日志记录器
        self._bound_logger = None

        os.makedirs(ProjectPath.LOG_PATH.value, exist_ok=True)

        # 初始化logger配置
        self._setup_handlers()

    def _setup_handlers(self):
        """设置日志handlers"""
        self.logger.remove()

        import sys
        import os as os_module

        # 在pytest-xdist并发环境中，使用特殊的日志处理
        if "PYTEST_XDIST_WORKER" in os_module.environ:
            # 在worker进程中，直接输出到stderr，这样pytest会收集并显示
            self.logger.add(
                sink=sys.stderr,
                level=self.log_level,
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <3} | {extra[case_name]: <3} | {extra[case_id]: <3} | {extra[request_id]: <3} | {message}",
                colorize=False,
                enqueue=False,
            )
        else:
            # 在普通环境中使用彩色输出
            self.logger.add(
                sink=sys.stdout,
                level=self.log_level,
                format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <3}</level> | "
                "<cyan>{extra[case_name]: <3}</cyan> | "
                "<blue>{extra[case_id]: <3}</blue> | "
                "<magenta>{extra[request_id]: <3}</magenta> | "
                "<level>{message}</level>",
                colorize=True,
            )

        # 配置文件日志格式 - 只有在非 Web 应用模式下才写入文件
        # Web 应用模式通过环境变量 WEB_APP_MODE=true 来标识
        if not os.getenv("WEB_APP_MODE"):
            try:
                self.logger.add(
                    sink=self.log_file,
                    level=self.log_level,
                    rotation="00:00",
                    retention="10 days",
                    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <3} | {extra[case_name]: <3} | {extra[case_id]: <3} | {extra[request_id]: <3} | {message}",
                    encoding="utf-8",
                    enqueue=False,
                )
            except (OSError, PermissionError) as e:
                # 如果无法写入文件（如只读文件系统），只使用控制台日志
                print(f"Warning: Could not setup file logging: {e}")
                print("Falling back to console-only logging")

    def set_config_log_level(self):
        """应用配置文件中的日志级别"""
        try:
            config_log_level = self._get_log_level_from_config()
            if config_log_level != self.log_level:
                self.log_level = config_log_level
                # 重新设置handlers
                self._setup_handlers()
                self.info(f"日志级别: {self.log_level}")
        except Exception as e:
            self.warning(f"应用配置日志级别失败: {e}")

    def _get_log_level_from_config(self):
        """从配置文件中读取日志级别"""
        try:
            from core.config import ConfigLoader

            config = ConfigLoader.get_instance()
            log_level = config.get("logging.level", "INFO").upper()
            return log_level
        except Exception:
            return "INFO"

    def bind(self, case_name=None, case_id=None, request_id=None):
        """绑定用例名称和用例ID到当前上下文"""
        if case_name is not None:
            self._case_name.set(case_name)
        if case_id is not None:
            self._case_id.set(case_id)
        if request_id is not None:
            self._request_id.set(request_id)

        # 每次都重新绑定最新的上下文信息
        bound_logger = self.logger.bind(
            case_name=self._case_name.get(),
            case_id=self._case_id.get(),
            request_id=self._request_id.get(),
        )
        return bound_logger

    def debug(self, message):
        self.bind().debug(message)

    def info(self, message):
        self.bind().info(message)

    def error(self, message):
        self.bind().error(message)

    def warning(self, message):
        self.bind().warning(message)

    # ========== 日志格式化辅助方法 ==========

    def section(self, title: str, level: str = "info", width: int = 50):
        """创建分割线日志"""
        getattr(self, level)("=" * width)
        getattr(self, level)(f"🌟 【{title}】")
        getattr(self, level)("=" * width)

    def subsection(self, title: str, level: str = "info", width: int = 50):
        """创建子分割线日志"""
        getattr(self, level)("─" * width)
        getattr(self, level)(f"📝 【{title}】")
        getattr(self, level)("─" * width)

    def labeled(self, label: str, content: Any, level: str = "info", icon: str = "📋"):
        """创建带标签的日志"""
        if isinstance(content, (dict, list)):
            content = LogFormatter.format_json(content)
        getattr(self, level)(f"{icon} 【{label}】{content}")

    def json_log(self, content: Any, label: str, level: str = "info"):
        """输出格式化的JSON日志"""
        formatted = LogFormatter.format_json(content)
        if label:
            getattr(self, level)(f"📋 【{label}】\n{formatted}")
        else:
            getattr(self, level)(formatted)

    def timing(self, label: str, duration: float, level: str = "info"):
        """输出计时日志"""
        getattr(self, level)(f"⏱️ 【{label}】{duration:.3f}s")

    def status(self, label: str, status: str, level: str = "info"):
        """输出状态日志"""
        status_icons = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
            "start": "🚀",
            "end": "🏁",
        }
        icon = status_icons.get(status.lower(), "📌")
        getattr(self, level)(f"{icon} 【{label}】{status}")

    def progress(
        self, current: int, total: int, label: str = "进度", level: str = "info"
    ):
        """输出进度日志"""
        percentage = (current / total) * 100 if total > 0 else 0
        getattr(self, level)(f"📊 【{label}】{current}/{total} ({percentage:.1f}%)")

    def set_case_info(self, case_name, case_id):
        """设置用例名称和用例ID"""
        self._case_name.set(case_name)
        self._case_id.set(case_id)

    def clear_case_info(self):
        """清空用例名称和用例ID"""
        self._case_name.set("N/A")
        self._case_id.set("N/A")

    def set_request_id(self, request_id):
        """设置当前请求ID"""
        self._request_id.set(request_id)

    def clear_request_id(self):
        """清空请求ID"""
        self._request_id.set("N/A")

    def generate_request_id(self, prefix: str = "req") -> str:
        """生成唯一的请求ID"""
        import uuid

        request_id = f"{prefix}_{uuid.uuid4().hex[:8]}"
        self.set_request_id(request_id)
        return request_id

    def case_context(self, case_name, case_id):
        """上下文管理器，用于临时设置用例名称和用例ID"""
        return self.CaseContext(self, case_name, case_id)

    class CaseContext:
        def __init__(self, logger, case_name, case_id):
            self.logger = logger
            self.case_name = case_name
            self.case_id = case_id
            self.original_case_name = None
            self.original_case_id = None

        def __enter__(self):
            # 保存原始值
            self.original_case_name = self.logger._case_name.get()
            self.original_case_id = self.logger._case_id.get()
            # 设置新值
            self.logger.set_case_info(self.case_name, self.case_id)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            # 恢复原始值
            self.logger.set_case_info(self.original_case_name, self.original_case_id)


def get_logger(worker_id="master"):
    """根据worker_id获取对应的logger实例"""
    return ApiLogger()


# 全局单例
api_logger = ApiLogger()
