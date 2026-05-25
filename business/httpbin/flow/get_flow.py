from business.httpbin.flow.base import HttpbinFlow


class GetFlow(HttpbinFlow):
    @classmethod
    def desc(cls):
        return "get 请求 flow"

    @classmethod
    def name(cls):
        return "Get 请求"

    @classmethod
    def web_visible(cls):
        """标记此Flow在Web页面中可见"""
        return True

    @classmethod
    def schema(cls):
        params = {
            "test_data": {
                "type": str,
                "description": "测试数据 ",
                "required": True,
            },
        }
        return cls.create_schema(params)

    def _run(self):
        test_data = self.get_params("test_data")
        if test_data:
            query_params = {"test_data": test_data}
        else:
            query_params = {}

        headers = {"Accept": "application/json"}

        response = self.api.get(params=query_params, headers=headers)
        return response
