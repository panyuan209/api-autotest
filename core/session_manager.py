from typing import Dict, Optional, Any
from core.api import ClientSession
from core.client_header import ClientHeader
from core.logger import api_logger as logger
from core.enums import App


class ClientSessionManager:
    """
    ClientSession 管理器
    """

    _instance: Optional["ClientSessionManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ClientSessionManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # 防止重复初始化
        if hasattr(self, "initialized"):
            return
        self.initialized = True
        self._sessions: Dict[str, ClientSession] = {}
        logger.debug("🔧 ClientSessionManager 初始化完成")

    @classmethod
    def get_instance(cls) -> "ClientSessionManager":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_session(
        self, client_session: ClientSession, app_name: App = App.HTTPBIN
    ) -> None:
        """
        注册 ClientSession

        Args:
            client_session: ClientSession 实例
            app_name: 应用名称，默认为 "httpbin"
        """
        self._sessions[app_name.value] = client_session
        logger.debug(f"📱 注册 ClientSession: {app_name.value}")

    def get_session(self, app_name: App = App.HTTPBIN) -> Optional[ClientSession]:
        """
        获取指定应用的 ClientSession

        Args:
            app_name: 应用名称

        Returns:
            ClientSession 实例，如果不存在返回 None
        """
        return self._sessions.get(app_name.value)

    def create_and_register_session(
        self, client_header: ClientHeader, app_name: App = App.HTTPBIN, **kwargs: Any
    ) -> ClientSession:
        """
        创建并注册 ClientSession

        Args:
            client_header: 客户端头部配置
            app_name: 应用名称
            **kwargs: ClientSession 的其他参数

        Returns:
            创建的 ClientSession 实例
        """
        client_session = ClientSession(client_header, **kwargs)
        self.register_session(client_session, app_name)
        return client_session

    def clear_sessions(self) -> None:
        """清空所有注册的 ClientSession"""
        self._sessions.clear()
        logger.debug("🧹 清空所有 ClientSession")

    def list_sessions(self) -> Dict[str, ClientSession]:
        """列出所有注册的 ClientSession"""
        return self._sessions.copy()

    def has_session(self, app_name: App = App.HTTPBIN) -> bool:
        """检查是否存在指定的 ClientSession"""
        return app_name.value in self._sessions


# 创建全局实例，方便使用
session_manager = ClientSessionManager.get_instance()
