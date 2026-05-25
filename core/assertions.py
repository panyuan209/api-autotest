import json
from typing import Any, Optional
from requests import Response

from core.logger import api_logger as logger


class APIAssert:
    """API断言类"""

    @staticmethod
    def status_code(response: Response, expected: int, message: Optional[str] = None):
        """断言状态码"""
        actual = response.status_code
        if actual != expected:
            error_msg = message or f"期望状态码 {expected}，实际获得 {actual}"
            logger.error(f"状态码断言失败: {error_msg}")
            logger.error(f"响应内容: {response.text}")
            raise AssertionError(error_msg)
        logger.info(f"✅ 状态码断言通过: {actual}")

    @staticmethod
    def response_time(
        response: Response, max_time: float, message: Optional[str] = None
    ):
        """断言响应时间"""
        actual_time = response.elapsed.total_seconds()
        if actual_time > max_time:
            error_msg = (
                message or f"响应时间 {actual_time:.2f}秒 超过了最大限制 {max_time}秒"
            )
            logger.error(f"响应时间断言失败: {error_msg}")
            raise AssertionError(error_msg)
        logger.info(f"✓ 响应时间断言通过: {actual_time:.2f}秒 <= {max_time}秒")

    @staticmethod
    def json_value(
        response: Response, path: str, expected: Any, message: Optional[str] = None
    ):
        """断言JSON路径值"""
        try:
            from glom import glom

            response_json = response.json()
            actual = glom(response_json, path)
            if actual != expected:
                error_msg = (
                    message or f"期望 {path} 的值为 {expected}，实际获得 {actual}"
                )
                logger.error(f"JSON值断言失败: {error_msg}")
                raise AssertionError(error_msg)
            logger.info(f"✓ JSON值断言通过: {path} = {actual}")
        except json.JSONDecodeError:
            error_msg = message or "响应不是有效的JSON格式"
            logger.error(f"JSON值断言失败: {error_msg}")
            raise AssertionError(error_msg)
        except Exception as e:
            error_msg = message or f"JSON路径 {path} 断言失败: {str(e)}"
            logger.error(f"JSON值断言失败: {error_msg}")
            raise AssertionError(error_msg)

    @staticmethod
    def contains_text(response: Response, text: str, message: Optional[str] = None):
        """断言响应包含指定文本"""
        if text not in response.text:
            error_msg = message or f"响应中未找到期望的文本: {text}"
            logger.error(f"文本包含断言失败: {error_msg}")
            logger.error(f"响应内容: {response.text}")
            raise AssertionError(error_msg)
        logger.info(f"✓ 文本包含断言通过: 找到了 '{text}'")

    @staticmethod
    def json_not_empty(response: Response, path: str, message: Optional[str] = None):
        """断言JSON字段不为空"""
        try:
            from glom import glom

            response_json = response.json()
            value = glom(response_json, path)
            if not value or (isinstance(value, (list, dict, str)) and len(value) == 0):
                error_msg = message or f"期望 {path} 不为空，但实际为空"
                logger.error(f"非空断言失败: {error_msg}")
                raise AssertionError(error_msg)
            logger.info(f"✓ 非空断言通过: {path} 不为空")
        except json.JSONDecodeError:
            error_msg = message or "响应不是有效的JSON格式"
            logger.error(f"非空断言失败: {error_msg}")
            raise AssertionError(error_msg)
        except Exception as e:
            error_msg = message or f"JSON路径 {path} 非空断言失败: {str(e)}"
            logger.error(f"非空断言失败: {error_msg}")
            raise AssertionError(error_msg)

    @staticmethod
    def json_array_length(
        response: Response,
        path: str,
        expected_length: int,
        message: Optional[str] = None,
    ):
        """断言JSON数组长度"""
        try:
            from glom import glom

            response_json = response.json()
            array = glom(response_json, path)
            if not isinstance(array, list):
                error_msg = message or f"路径 {path} 不是数组类型"
                logger.error(f"数组长度断言失败: {error_msg}")
                raise AssertionError(error_msg)

            actual_length = len(array)
            if actual_length != expected_length:
                error_msg = (
                    message
                    or f"期望数组长度 {expected_length}，实际获得 {actual_length}"
                )
                logger.error(f"数组长度断言失败: {error_msg}")
                raise AssertionError(error_msg)
            logger.info(f"✓ 数组长度断言通过: {path} 长度为 {actual_length}")
        except json.JSONDecodeError:
            error_msg = message or "响应不是有效的JSON格式"
            logger.error(f"数组长度断言失败: {error_msg}")
            raise AssertionError(error_msg)
        except Exception as e:
            error_msg = message or f"JSON数组长度断言失败: {str(e)}"
            logger.error(f"数组长度断言失败: {error_msg}")
            raise AssertionError(error_msg)


# 便捷的全局断言实例
assert_api = APIAssert()
