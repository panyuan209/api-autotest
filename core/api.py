import json
import time
import requests
from typing import Optional, Dict, Any
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from core.client_header import ClientHeader
from core.config import ConfigLoader
from core.enums import App
from core.logger import api_logger as logger, LogFormatter
from core.exceptions import ApiRequestError
from core.auth_manager import global_auth_manager


class ClientSession:
    """
    客户端会话管理类

    功能：
    1. 管理HTTP请求会话的生命周期
    2. 配置连接池和重试策略
    3. 统一的会话资源管理

    特性：
    - 自动重试机制（对5xx错误进行重试）
    - 连接池复用（提高性能）
    - 资源自动清理（防止内存泄漏）
    """

    def __init__(
        self,
        client: ClientHeader,
        session: requests.Session = requests.session(),
        retry_config: Optional[Dict[str, Any]] = None,
        pool_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化客户端会话

        Args:
            client: 客户端头部管理器，负责生成请求头
            session: 可选的requests.Session实例，如果为None则创建新实例
            retry_config: 重试策略配置
                - total: 最大重试次数（默认3次）
                - backoff_factor: 退避因子（默认0.3）
                - status_forcelist: 需要重试的状态码列表
            pool_config: 连接池配置
                - pool_connections: 连接池大小（默认10）
                - pool_maxsize: 最大连接数（默认20）
                - max_retries: 最大重试次数（默认3）
                - pool_block: 连接池是否阻塞（默认False）
        """
        self.client = client
        self.session = session if session else requests.session()

        # === 连接池配置 ===
        # 设置默认连接池参数，优化网络性能
        if pool_config is None:
            pool_config = {
                "pool_connections": 20,  # 连接池大小：同时保持的连接数
                "pool_maxsize": 40,  # 最大连接数：单个主机的最大连接数
                "max_retries": 5,  # 最大重试次数
                "pool_block": False,  # 非阻塞模式：连接池满时不阻塞
            }

        # === 重试策略配置 ===
        if retry_config is None:
            retry_config = {
                "total": 3,  # 总重试次数
                "backoff_factor": 0.5,  # 退避因子：重试间隔 = backoff_factor * (2 ^ retry_count)
                "status_forcelist": [500, 502, 503, 504, 429],  # 服务器错误时自动重试
            }

        # 应用重试策略和连接池配置
        retry_strategy = Retry(**retry_config)
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            **{k: v for k, v in pool_config.items() if k != "max_retries"},
        )

        # 为HTTP和HTTPS协议应用适配器
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def __del__(self):
        """
        析构函数：自动清理会话资源

        确保在对象销毁时正确关闭HTTP连接，防止资源泄漏
        """
        if hasattr(self, "session"):  # 防御性检查，确保session属性存在
            self.session.close()


class PerformanceMonitor:
    """
    API请求性能监控类

    功能：
    1. 记录每个请求的性能指标（响应时间、状态码、响应大小等）
    2. 提供性能统计分析（平均响应时间、慢请求识别）
    3. 支持多进程环境（通过worker_id区分不同进程）

    用途：
    - 性能调优：识别慢接口和性能瓶颈
    - 监控告警：检测异常响应时间
    - 测试报告：生成性能统计数据
    """

    def __init__(self, worker_id: str = "master"):
        """
        初始化性能监控器

        Args:
            worker_id: 工作进程标识，用于多进程环境下区分不同的测试进程
        """
        self.metrics = []  # 性能指标数据列表
        self.worker_id = worker_id  # 进程标识

    def record_request(
        self,
        url: str,
        method: str,
        duration: float,
        status_code: int,
        response_size: int,
    ):
        """
        记录单次请求的性能指标

        Args:
            url: 请求URL
            method: HTTP方法（GET, POST等）
            duration: 请求耗时（秒）
            status_code: HTTP状态码
            response_size: 响应体大小（字节）
        """
        # 构建性能指标记录
        metric = {
            "url": url,
            "method": method,
            "duration": duration,
            "status_code": status_code,
            "response_size": response_size,
            "timestamp": time.time(),
            "worker_id": self.worker_id,
        }
        self.metrics.append(metric)

        # 实时输出性能日志，便于监控
        status_icon = (
            "✅"
            if 200 <= status_code < 300
            else "⚠️"
            if 400 <= status_code < 500
            else "❌"
        )
        logger.info(
            f"📊 【性能监控】{method} {url} | {duration:.3f}s | {status_icon}{status_code} | {response_size}B"
        )

    def get_average_response_time(self) -> float:
        """获取平均响应时间"""
        if not self.metrics:
            return 0.0
        return sum(m["duration"] for m in self.metrics) / len(self.metrics)

    def get_slow_requests(self, threshold: float = 2.0) -> list:
        """获取慢请求列表"""
        return [m for m in self.metrics if m["duration"] > threshold]


class Api:
    """
    接口类，用于管理API请求
    """

    # 主机地址的键名，需要在子类中定义
    HOST_KEY: str | None = None
    # 应用名称，需要在子类中定义（如果需要认证的话）
    APP_NAME = None

    def __init_subclass__(cls, **kwargs):
        """
        在子类定义时验证 HOST_KEY 是否已定义

        确保所有 Api 子类在导入时就具备必要的配置，
        而不是等到运行时实例化时才报错。
        """
        super().__init_subclass__(**kwargs)
        if cls.HOST_KEY is None:
            raise ValueError(
                f"{cls.__name__} 必须定义 HOST_KEY 属性，"
                f'例如: HOST_KEY = "host.your_app_host"'
            )

    def __init__(self, client_session: ClientSession):
        """
        初始化客户端会话和其他属性
        :param client_session: 客户端会话对象
        """
        self.client_session: ClientSession = client_session
        self.client: ClientHeader = self.client_session.client
        self.session: requests.Session = self.client_session.session
        self.config: ConfigLoader | None = ConfigLoader.get_instance()
        self.performance_monitor = PerformanceMonitor()

        # HOST_KEY 已在 __init_subclass__ 中验证，此处获取主机地址
        assert self.HOST_KEY is not None  # 由 __init_subclass__ 保证
        self.host = self.config.get(self.HOST_KEY) if self.config else None
        if self.host is None:
            raise ValueError(f"未能从配置中获取主机地址，HOST_KEY: {self.HOST_KEY}")

        if self.APP_NAME is not None:
            self.app_name = (
                self.APP_NAME.value
                if hasattr(self.APP_NAME, "value")
                else str(self.APP_NAME)
            )
        else:
            self.app_name = None

    # ──────────── 内部辅助方法 ────────────

    def _apply_authentication(
        self,
        url: str,
        method: str,
        headers: Dict[str, Any],
        query_params: Dict[str, Any],
        params: Dict[str, Any],
    ) -> None:
        """执行认证并将认证信息应用到请求的各个组成部分"""
        from core.auth_manager import AuthLocation

        try:
            logger.debug(f"🔐 【认证开始】为应用 [{self.app_name}] 进行认证处理")

            request_components = {
                "url": url,
                "method": method,
                "headers": headers.copy(),
                "params": query_params.copy(),
                "body_params": {
                    k: v for k, v in params.items() if k not in ("headers", "params")
                },
            }

            auth_result = global_auth_manager.auth_for_app(
                session=self.session,
                app_name=self.app_name,
                **request_components,
            )

            if not auth_result.success:
                logger.warning(
                    f"⚠️ 应用 {self.app_name} 认证失败: "
                    f"{auth_result.error_message}，继续无认证请求"
                )
                return

            # 安全解包（success=True 时 location/field_name/field_value 保证非空）
            location = auth_result.location
            field_name = auth_result.field_name or ""
            field_value = auth_result.field_value or ""
            if not location or not field_name:
                return

            logger.debug(f"✅ 【认证成功】｜ 应用 [{self.app_name}] 认证成功")
            logger.debug(
                f"🔐 【认证位置】｜ 认证信息已应用到 {location.value}: {field_name}"
            )

            if location == AuthLocation.HEADERS:
                headers[field_name] = field_value
            elif location == AuthLocation.PARAMS:
                if field_name != "multiple":
                    query_params[field_name] = field_value
                elif isinstance(field_value, dict):
                    query_params.update(field_value)
            else:
                body_type = location.value
                target = params.get(body_type)
                if target is not None and isinstance(target, dict):
                    if (
                        field_name in target
                        and isinstance(target[field_name], dict)
                        and isinstance(field_value, dict)
                    ):
                        target[field_name].update(field_value)
                    else:
                        target[field_name] = field_value
                elif target is not None:
                    params[body_type] = field_value
                else:
                    logger.warning(
                        f"⚠️ 无法应用认证信息到 {body_type}：参数不存在或为空"
                    )

        except Exception as e:
            logger.warning(f"❌ 认证自动管理异常: {e}，继续进行无认证请求")

    @staticmethod
    def _build_request_params(
        params: Dict[str, Any],
        headers: Dict[str, Any],
        query_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """构建传给 requests 的最终参数字典"""
        final: Dict[str, Any] = {
            "headers": headers,
            "timeout": params.get("timeout", 30),
        }
        if query_params:
            final["params"] = query_params

        excluded = {"headers", "params", "timeout"}
        for key, value in params.items():
            if key in excluded:
                continue
            if key in ("raw", "xml", "form", "binary"):
                final["data"] = value
                if key == "xml" and "Content-Type" not in headers:
                    headers["Content-Type"] = "application/xml"
                elif key == "form" and "Content-Type" not in headers:
                    headers["Content-Type"] = "application/x-www-form-urlencoded"
            else:
                final[key] = value
        return final

    # ──────────── 请求/响应生命周期钩子 ────────────

    def before_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, Any],
        query_params: Dict[str, Any],
        request_params: Dict[str, Any],
    ) -> None:
        """
        请求发出前的钩子，子类可重写。

        典型用途：加密请求体、生成签名、注入额外 header 等。
        所有字典参数均为引用，原地修改即可生效。

        Args:
            method: HTTP 方法 (get/post/put/delete/patch)
            url: 完整请求 URL
            headers: 请求头字典（可原地修改）
            query_params: URL 查询参数字典（可原地修改）
            request_params: 即将传给 requests 的最终参数字典（可原地修改）
        """
        pass

    def after_response(self, response: requests.Response) -> requests.Response:
        """
        收到响应后的钩子，子类可重写。

        典型用途：解密响应体、格式转换、注入额外校验等。

        Args:
            response: 原始 HTTP 响应对象

        Returns:
            处理后的响应对象（可返回原对象或新对象）
        """
        return response

    # ──────────── 请求执行 ────────────

    def do_request(self, method, path, **params):
        """
        执行请求的入口方法，构造完整URL后调用内部方法发起请求
        :param method: 请求方法
        :param path: 请求路径
        :param params: 请求参数
        :return: 响应对象
        """
        url = self.host + path
        return self._do_request(method, url, **params)

    def _do_request(self, method, url, **params):
        """
        内部方法，发起实际的请求

        请求生命周期：
        1. 参数提取 + Headers 合并
        2. 认证管理（_apply_authentication）
        3. 构建最终请求参数（_build_request_params）
        4. before_request 钩子（子类可重写）
        5. 执行 HTTP 请求
        6. after_response 钩子（子类可重写）
        7. 日志 + 性能监控 + 错误处理
        """
        logger.generate_request_id(f"{method.upper()}")

        # 1. 参数提取 + Headers 合并
        auth = params.pop("auth", True)
        request_headers = {**self.client.headers(), **params.get("headers", {})}
        query_params = params.get("params", {})

        # 2. 认证管理
        if self.app_name and auth:
            self._apply_authentication(
                url, method, request_headers, query_params, params
            )

        # 3. 构建最终请求参数
        final_request_params = self._build_request_params(
            params, request_headers, query_params
        )

        # 4. before_request 钩子（子类可重写，用于加密/签名等定制逻辑）
        self.before_request(
            method, url, request_headers, query_params, final_request_params
        )

        # 5. 执行 HTTP 请求
        if not hasattr(self.session, method):
            raise RuntimeError(f"不支持的请求方法: {method}")
        rq = getattr(self.session, method)

        logger.info("═" * 50)
        logger.info(f"🌐 【HTTP请求】{method.upper()} {url}")
        logger.info("─" * 50)
        logger.labeled(
            "请求头",
            LogFormatter.format_headers(final_request_params.get("headers", {})),
            icon="📋",
        )

        actual_query_params = final_request_params.get("params", query_params)
        if actual_query_params:
            logger.labeled(
                "查询参数", LogFormatter.format_params(actual_query_params), icon="📊"
            )

        excluded_keys = {"headers", "params", "timeout"}
        body_params = {k: v for k, v in params.items() if k not in excluded_keys}
        if body_params:
            logger.json_log(body_params, "请求体")

        start_time = time.time()

        try:
            resp = rq(url, **final_request_params)
            duration = time.time() - start_time

            response_size = len(resp.content) if resp.content else 0
            self.performance_monitor.record_request(
                url=url,
                method=method.upper(),
                duration=duration,
                status_code=resp.status_code,
                response_size=response_size,
            )

            logger.info("─" * 50)
            logger.labeled("响应状态", resp.status_code, icon="📬")
            logger.timing("响应时间", duration)
            logger.labeled("响应大小", f"{response_size} bytes", icon="📊")
            logger.labeled(
                "响应内容", LogFormatter.format_response_body(resp.text), icon="📄"
            )
            logger.info("═" * 50)
            logger.info(f"🏁 【请求完成】{url}")
            logger.info("═" * 50 + "\n")
            logger.clear_request_id()

            # 6. after_response 钩子（子类可重写，用于解密/转换等定制逻辑）
            resp = self.after_response(resp)

            if not resp.ok:
                raise ApiRequestError(
                    f"API request failed with status {resp.status_code}",
                    status_code=resp.status_code,
                    response_body=resp.text,
                )

            return resp

        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            logger.error("─" * 100)
            logger.labeled("请求失败", url, "error", "💥")
            logger.timing("失败时间", duration, "error")
            logger.labeled("错误信息", str(e), "error", "❌")
            logger.error("═" * 100 + "\n")
            logger.clear_request_id()
            raise ApiRequestError(f"Request failed: {str(e)}")

    def get(self, path, **params):
        """
        GET请求的快捷方法
        :param path: 请求路径
        :param params: 请求参数
        :return: 响应对象
        """
        return self.do_request("get", path, **params)

    def post(self, path, **params):
        """
        POST请求的快捷方法
        :param path: 请求路径
        :param params: 请求参数
        :return: 响应对象
        """
        return self.do_request("post", path, **params)

    def put(self, path, **params):
        """
        PUT请求的快捷方法
        :param path: 请求路径
        :param params: 请求参数
        :return: 响应对象
        """
        return self.do_request("put", path, **params)

    def delete(self, path, **params):
        """
        DELETE请求的快捷方法
        :param path: 请求路径
        :param params: 请求参数
        :return: 响应对象
        """
        return self.do_request("delete", path, **params)

    def patch(self, path, **params):
        """
        PATCH请求的快捷方法
        :param path: 请求路径
        :param params: 请求参数
        :return: 响应对象
        """
        return self.do_request("patch", path, **params)

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        return {
            "total_requests": len(self.performance_monitor.metrics),
            "average_response_time": self.performance_monitor.get_average_response_time(),
            "slow_requests": self.performance_monitor.get_slow_requests(),
        }
