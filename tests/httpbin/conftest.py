"""
Httpbin 测试模块的 pytest 配置
提供 class 级别的 ClientSession fixture，自动注册到 session_manager
"""

import pytest
from core.api import ClientSession
from core.client_header import HttpbinClientHeader
from core.enums import App
from core.logger import api_logger
from core.session_manager import session_manager


@pytest.fixture(scope="class", autouse=True)
def httpbin_session(request):
    """
    为测试类提供并注册 ClientSession

    - 在 class 级别自动使用，每个测试类共享一个 session
    - 自动注册到 session_manager，Flow 层可通过 App.HTTPBIN 获取
    - 测试类结束后自动清理
    """
    client_session = ClientSession(client=HttpbinClientHeader())
    session_manager.register_session(client_session, App.HTTPBIN)

    # 将 session 和 logger 注入到测试类
    request.cls.client_session = client_session
    request.cls.logger = api_logger

    yield client_session

    # teardown: 清理 session 注册
    session_manager._sessions.pop(App.HTTPBIN.value, None)
