"""
Httpbin 测试基类

注意：ClientSession 的创建和注册已由 tests/httpbin/conftest.py 中的
httpbin_session fixture 自动处理（autouse, scope="class"）。

测试类无需再手动 setup_class，可以直接编写测试用例。
如果需要显式继承基类（例如用于类型提示或共享辅助方法），可以继承此类。
"""


class HttpbinTest:
    """Httpbin 测试标记基类（可选继承）"""

    pass
