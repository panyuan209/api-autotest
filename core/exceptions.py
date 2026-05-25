"""
统一异常处理模块
提供框架级别的异常定义和处理机制
"""

from typing import Optional, Dict, Any


class ApiTestException(Exception):
    """API测试框架基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        return (
            f"[{self.error_code}] {self.message}" if self.error_code else self.message
        )


class ConfigurationError(ApiTestException):
    """配置相关异常"""

    pass


class ApiRequestError(ApiTestException):
    """API请求相关异常"""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.response_body = response_body


class FlowExecutionError(ApiTestException):
    """Flow执行异常"""

    pass


class ValidationError(ApiTestException):
    """参数验证异常"""

    pass


class DataFactoryError(ApiTestException):
    """测试数据工厂异常"""

    pass


class DatabaseError(ApiTestException):
    """数据库操作异常"""

    pass


def handle_api_exception(func):
    """API异常处理装饰器"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ApiTestException:
            # 框架异常直接抛出
            raise
        except Exception as e:
            raise ApiTestException(f"Unexpected error in {func.__name__}: {str(e)}")

    return wrapper
