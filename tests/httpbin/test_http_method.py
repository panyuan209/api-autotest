import allure
import pytest
from business.httpbin.flow.get_flow import GetFlow
from business.httpbin.flow.post_flow import PostFlow
from tests.httpbin.httpbin_test import HttpbinTest
from utils.decorator import JsonResult


class TestHttpMethod(HttpbinTest):
    def test_get(self):
        """GET请求测试"""
        with allure.step("GET请求"):
            get_res = GetFlow(
                params={"test_data": "test_value"},
            ).run()

            assert get_res.extract("args.test_data") == "test_value"

    @pytest.mark.parametrize("post_data", ["test_post_data", "another_post_data "])
    def test_post(self, post_data):
        """POST请求测试"""
        with allure.step("POST请求"):
            post_res: JsonResult = PostFlow(
                params={"post_data": post_data},
            ).run()

            assert post_res.extract("json.post_data") == post_data
            assert post_res.extract("json.created_at") is not None
            assert post_res.extract("json.source") == "api_test"
