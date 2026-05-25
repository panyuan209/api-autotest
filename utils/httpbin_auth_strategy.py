import random
from typing import Optional
from core.auth_manager import AuthStrategy, AuthResult, AuthLocation
from core.logger import api_logger as logger
from core.config import ConfigLoader


class HttpbinAuthStrategy(AuthStrategy):
    """
    HTTPBin认证策略类
    """

    def get_auth(self, **kwargs) -> Optional[str]:
        """
        获取HTTPBin的认证信息
        支持从配置文件或参数中获取token

        优先级：
        1. 用户在headers中手动设置的Authorization
        2. 传入的token参数
        3. 配置文件中的默认token
        """
        self.config = ConfigLoader.get_instance()

        # 随机生成 Bearer Token
        auth = "".join(
            random.choice("0123456789abcdefghijklmnopqrstuvwxyz") for _ in range(36)
        )

        return f"Bearer {auth}"

    def save_auth_to_session(self, session, auth: str):
        """
        将认证信息保存到session中

        对于HTTPBin的Basic Auth，将认证信息设置到session的headers中
        """
        if session and auth:
            setattr(session, "httpbin_auth", auth)
            logger.debug("💾 【认证保存】将 HttpBin 认证信息保存到 session 中")

    def get_session_auth(self, session) -> Optional[str]:
        """
        从session中获取已保存的认证信息
        """
        if not session:
            return None

        return getattr(session, "httpbin_auth", None)

    def apply_auth(self, session=None, auth=None, **kwargs) -> AuthResult:
        """
        返回认证信息应该如何应用到请求中的指导信息
        不再直接修改参数，而是返回认证结果对象
        """
        if not auth:
            return AuthResult.failure_result("没有找到认证信息，无法应用认证")

        logger.debug(f"📋 【认证应用】准备返回认证信息应用: {auth[:20]}...")

        # 返回认证信息应该如何应用的指导
        return AuthResult.success_result(
            location=AuthLocation.HEADERS, field_name="Authorization", field_value=auth
        )
