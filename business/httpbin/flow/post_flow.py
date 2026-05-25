from business.httpbin.flow.base import HttpbinFlow
import time


class PostFlow(HttpbinFlow):
    """基础POST请求Flow"""

    @classmethod
    def desc(cls):
        return "post 请求 flow"

    @classmethod
    def name(cls):
        return "PostFlow"

    @classmethod
    def web_visible(cls):
        """标记此Flow在Web页面中可见"""
        return True

    @classmethod
    def schema(cls):
        return cls.create_schema(
            {
                "post_data": {"type": str, "description": "帖子内容", "required": True},
            }
        )

    def _run(self):
        # 获取业务参数
        post_data = self.get_params("post_data")

        # 构建请求体
        request_body = {
            "post_data": post_data,
            "created_at": time.time(),
            "source": "api_test",
        }

        # 构建请求头
        headers = {"Content-Type": "application/json", "X-Post-Type": "create"}

        # 发送POST请求
        response = self.api.post(json=request_body, headers=headers)
        return response
