import time
from typing import Any, Dict

import requests

from core.api import Api
from core.enums import App
from core.logger import api_logger as logger
from utils.decorator import json

__all__ = ["HttpbinApi"]


class HttpbinApi(Api):
    HOST_KEY = "host.httpbin_host"
    APP_NAME = App.HTTPBIN

    def before_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, Any],
        query_params: Dict[str, Any],
        request_params: Dict[str, Any],
    ) -> None:
        """注入请求追踪头和框架标识"""
        headers["X-Request-Source"] = "api-test-framework"
        headers["X-Request-Timestamp"] = str(time.time())

    def after_response(self, response: requests.Response) -> requests.Response:
        """记录服务端链路信息，校验异常状态"""
        server = response.headers.get("Server", "unknown")
        logger.debug(f"🔗 【响应元信息】Server: {server}")

        if response.status_code is not None and response.status_code >= 500:
            logger.warning(f"⚠️ 服务端异常: {response.status_code}")

        return response

    @json
    def post(self, **kwargs):
        """POST请求方法"""
        return super().post("/post", **kwargs)

    @json
    def get(self, **kwargs):
        """GET请求方法"""
        return super().get("/get", **kwargs)

    def put(self, **kwargs):
        """PUT请求方法"""
        return super().put("/put", **kwargs)

    def patch(self, **kwargs):
        """PATCH请求方法"""
        return super().patch("/patch", **kwargs)

    def delete(self, **kwargs):
        """DELETE请求方法"""
        return super().delete("/delete", **kwargs)
