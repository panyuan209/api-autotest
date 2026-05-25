from business.httpbin.flow.base import HttpbinFlow
import time


class MockFlow(HttpbinFlow):
    """模拟Flow，用于测试Web应用功能"""

    @classmethod
    def desc(cls):
        return "模拟Flow，返回模拟数据用于测试"

    @classmethod
    def name(cls):
        return "MockFlow"

    @classmethod
    def schema(cls):
        return cls.create_schema(
            {
                "user_name": {"type": str, "description": "用户名", "required": True},
                "age": {"type": int, "description": "年龄", "required": False},
                "is_active": {
                    "type": bool,
                    "description": "是否激活",
                    "required": False,
                },
            }
        )

    def _run(self):
        # 获取参数
        user_name = self.get_param("user_name")
        age = self.get_param("age", 18)
        is_active = self.get_param("is_active", True)

        # 模拟一些处理时间
        time.sleep(0.1)

        # 返回模拟数据
        return {
            "success": True,
            "message": f"Hello {user_name}!",
            "data": {
                "user_name": user_name,
                "age": age,
                "is_active": is_active,
                "processed_at": time.time(),
                "server": "mock_server",
            },
            "execution_info": {"flow_type": "mock", "version": "1.0.0"},
        }
