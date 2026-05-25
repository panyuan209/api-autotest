import jmespath
import functools

from core.assertions import assert_api
from core.logger import api_logger as logger


class JsonResult:
    """JSON 结果包装类，支持 jmespath 表达式提取"""

    def __init__(self, data):
        self.data = data

    def extract(self, expression):
        """使用 jmespath 表达式提取数据"""
        res = jmespath.search(expression, self.data)
        logger.info(f"🔍 提取结果: {res}")
        return res

    def __getattr__(self, name):
        """代理其他属性访问到原始数据"""
        return getattr(self.data, name)

    def __getitem__(self, key):
        """支持字典式访问"""
        return self.data[key]

    def __repr__(self):
        return f"JsonResult({self.data})"

    def dict(self):
        """提供 dict() 方法，用于支持 Pydantic 序列化"""
        return self.data

    def __iter__(self):
        """支持序列化时的迭代"""
        if isinstance(self.data, dict):
            return iter(self.data.items())
        return iter([])

    def keys(self):
        """支持字典接口"""
        if isinstance(self.data, dict):
            return self.data.keys()
        return []

    def values(self):
        """支持字典接口"""
        if isinstance(self.data, dict):
            return self.data.values()
        return []

    def items(self):
        """支持字典接口"""
        if isinstance(self.data, dict):
            return self.data.items()
        return []


def json(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        resp = func(*args, **kwargs)
        assert_api.status_code(resp, 200)
        if resp.text:
            json_res = JsonResult(resp.json())
            logger.json_log(json_res.data, "响应JSON")
            return json_res
        else:
            logger.warning("响应体为空，返回空 JsonResult")
            return JsonResult({})

    return wrapper
