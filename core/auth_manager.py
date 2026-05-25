from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, Union
from core.enums import App
from core.logger import api_logger as logger
from dataclasses import dataclass
from enum import Enum


class AuthLocation(Enum):
    """认证字段应用位置枚举"""

    HEADERS = "headers"
    PARAMS = "params"
    DATA = "data"
    JSON = "json"
    FILES = "files"
    RAW = "raw"
    XML = "xml"
    FORM = "form"
    BINARY = "binary"


@dataclass
class AuthResult:
    """
    认证结果对象

    包含认证是否成功、认证字段的位置、字段名和字段值等信息
    使API模块能够清晰地知道如何应用认证信息
    """

    success: bool  # 认证是否成功
    location: Optional[AuthLocation] = AuthLocation.HEADERS  # 认证字段应该放在哪里
    field_name: Optional[str] = ""  # 认证字段名
    field_value: Optional[str] = ""  # 认证字段值
    error_message: Union[dict, str] = ""  # 认证失败时的错误信息

    @classmethod
    def success_result(
        cls, location: AuthLocation, field_name: str, field_value: str
    ) -> "AuthResult":
        """创建成功的认证结果"""
        return cls(
            success=True,
            location=location,
            field_name=field_name,
            field_value=field_value,
        )

    @classmethod
    def failure_result(cls, error_message: str) -> "AuthResult":
        """创建失败的认证结果"""
        return cls(success=False, error_message=error_message)

    def apply_to_params(self, params: Dict[str, Any]) -> bool:
        """
        将认证信息应用到请求参数中

        Args:
            params: 请求参数字典

        Returns:
            bool: 是否成功应用
        """
        if not self.success:
            return False

        if not all([self.location, self.field_name, self.field_value]):
            return False

        location_key = self.location.value

        # 确保目标位置存在
        if location_key not in params:
            params[location_key] = {}

        # 应用认证字段
        params[location_key][self.field_name] = self.field_value
        return True


class AuthStrategy(ABC):
    """
    认证策略抽象基类

    定义了认证的核心接口，所有具体的认证策略都应该继承此类。
    提供了完整的认证流程：获取认证 -> 认证缓存 -> 应用认证
    """

    @abstractmethod
    def get_auth(self, **kwargs) -> Optional[str]:
        """
        获取认证信息
        :param kwargs: 任意关键字参数，由子类自定义实现
        :return:
        """
        pass

    @abstractmethod
    def get_session_auth(self, session) -> Optional[str]:
        """
        从 session 中获取已保存的 auth 字段
        :param session: requests.Session对象
        :return:
        """
        pass

    @abstractmethod
    def save_auth_to_session(self, session, auth: str):
        """
        将auth保存到session中
        :param session: requests.Session对象
        :param auth:
        """
        pass

    @abstractmethod
    def apply_auth(self, session=None, auth=None, **kwargs) -> AuthResult:
        """
        应用认证信息，返回认证结果对象

        :param session: requests.Session对象，用于auth缓存
        :param auth: 认证信息
        :param kwargs: 请求相关的参数，由子类自定义处理
                      例如: headers, params, data, json, files 等
        :return: AuthResult对象，包含认证是否成功及如何应用认证信息
        """
        pass

    def auth(self, session=None, **kwargs) -> AuthResult:
        """
        确保认证可用的完整认证流程

        这是认证策略的核心方法，提供了完整的认证生命周期管理：
        1. 优先从session获取已缓存的auth（避免重复认证）
        2. 可选的有效性验证，如果子类重写了_is_auth_valid且返回False则尝试刷新
        3. 如果缓存中无auth，则调用具体策略的get_auth方法获取新auth
        4. 将获取到的auth保存到session中以供后续复用
        5. 将auth应用到当前请求的参数中

        Args:
            session: requests.Session对象，用于auth缓存
            **kwargs: 请求相关参数，包括headers、params、data等

        Returns:
            AuthResult: 认证结果对象，包含认证是否成功及如何应用认证信息

        Raises:
            Exception: 认证过程中的各种异常都会被捕获并记录
        """
        try:
            # 步骤1：尝试从session获取已有 auth（session复用机制）
            auth = self.get_session_auth(session) if session else None

            # 步骤2：可选的有效性验证（只有在子类重写了验证逻辑时才会执行复杂验证）
            if auth:
                # 检查是否需要有效性验证（通过检查是否重写了默认方法）
                auth_valid = self._is_auth_valid(session)
                if not auth_valid:
                    logger.info("现有认证信息验证失败，尝试刷新")
                    if self._refresh_auth(session, **kwargs):
                        auth = self.get_session_auth(session)
                    else:
                        logger.warning("认证刷新失败，将重新获取")
                        auth = None

            # 步骤3：如果没有有效的 auth，获取新 auth 并保存
            if not auth:
                logger.info(
                    "🔄 【认证获取】Session中未找到有效认证信息，开始自动获取认证"
                )
                auth = self.get_auth(**kwargs)
                if auth and session:
                    # 步骤4：将新认证信息保存到session中
                    self.save_auth_to_session(session, auth)
            else:
                logger.debug("🎯 【认证缓存】使用session中的已有认证信息")

            # 步骤5：应用认证信息到请求中
            if auth:
                return self.apply_auth(session=session, auth=auth, **kwargs)
            else:
                logger.warning("未能获取到认证信息，认证失败")
                return AuthResult.failure_result("未能获取到认证信息")
        except Exception as e:
            logger.error(f"Auth 确保过程异常: {e}")
            return AuthResult.failure_result(f"认证过程异常: {e}")

    def _is_auth_valid(self, session=None) -> bool:
        """
        检查当前认证是否有效（可选功能，默认总是返回True）

        子类可以重写此方法来实现具体的有效性验证逻辑，比如：
        - JWT token过期检查
        - API Key格式验证
        - 权限范围检查等

        Args:
            session: requests.Session对象，用于检查auth缓存

        Returns:
            bool: 是否有有效的认证，默认返回True（跳过验证）
        """
        # 默认实现：总是返回True，表示不进行有效性验证
        # 子类可以根据需要重写此方法
        return True

    def _refresh_auth(self, session=None, **kwargs) -> bool:
        """
        刷新认证信息（可选功能，默认不支持刷新）

        如果当前认证无效或需要更新，重新获取并保存新的认证信息。
        适用于需要动态更新认证信息的场景。

        子类可以重写此方法来实现具体的刷新逻辑。

        Args:
            session: requests.Session对象，用于auth缓存
            **kwargs: 请求相关参数，包括headers、params、data等

        Returns:
            bool: 是否成功刷新认证，默认返回False（不支持刷新）
        """
        # 默认实现：不支持刷新，返回False
        # 子类可以根据需要重写此方法
        logger.debug("当前认证策略不支持自动刷新")
        return False

    def _clear_session_auth(self, session):
        """
        清除session中的认证信息（可选功能，提供通用实现）

        Args:
            session: requests.Session对象
        """
        # 基础实现：删除可能存在的认证属性
        auth_attrs = ["auth", "token", "access_token", "httpbin_auth"]
        for attr in auth_attrs:
            if hasattr(session, attr):
                delattr(session, attr)
                logger.info(f"成功清理 session 中的认证属性：{attr}")


class AuthManager:
    def __init__(self):
        """初始化管理器，创建空的策略字典"""
        self.strategies: Dict[str, AuthStrategy] = {}
        self._initialize_strategies()

    def _initialize_strategies(self):
        """延迟初始化策略，避免循环导入"""

        from utils.httpbin_auth_strategy import HttpbinAuthStrategy

        self.strategies[App.HTTPBIN.value] = HttpbinAuthStrategy()

    def auth_for_app(self, app_name: str, session=None, **kwargs) -> AuthResult:
        """
        Args:
            app_name: 应用名称，用于查找对应的认证策略
            session: requests.Session对象，用于token缓存
            **kwargs: 请求相关参数，会传递给认证策略处理
                     包括headers、params、data、json等
        Returns:
            AuthResult: 认证结果对象，包含认证是否成功及如何应用认证信息
        """
        strategy = self.strategies.get(app_name)

        if not strategy:
            error_msg = f"未找到应用 {app_name} 的认证策略"
            logger.error(error_msg)
            return AuthResult.failure_result(error_msg)

        try:
            return strategy.auth(session=session, **kwargs)
        except Exception as e:
            error_msg = f"应用 {app_name} 的 auth 失败: {e}"
            logger.error(error_msg)
            return AuthResult.failure_result(error_msg)


global_auth_manager = AuthManager()
