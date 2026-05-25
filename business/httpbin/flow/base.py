from typing import Optional
from business.httpbin.apis.api import HttpbinApi
from core.api import ClientSession
from core.flow import Flow
from core.enums import App


class HttpbinFlow(Flow):
    def setup(self, client_session: Optional[ClientSession] = None, **kwargs):
        if client_session is None:
            from core.session_manager import session_manager

            client_session = session_manager.get_session(App.HTTPBIN)

        if client_session is None:
            raise ValueError(
                f"未找到 {App.HTTPBIN.value} 应用的 ClientSession，请先在测试基类中注册：session_manager.register_session(client_session, App.HTTPBIN)"
            )

        self.client_session = client_session
        self.api = HttpbinApi(self.client_session)
