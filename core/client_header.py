import random

from core.enums import PlatformType
from core.config import ConfigLoader


class ClientHeader:
    """
    客户端类，用于构造请求头
    """

    # header 属性映射，定义了支持的请求头属性与其对应的 header 名称、类型、处理函数等
    header_map = {
        "plat": {
            "header": "plat",
            "type": PlatformType,
            "procedure": lambda x: x.value,
        },
        "channel": {"header": "channel"},
        "devid": {"header": "devid"},
        "ver": {"header": "ver"},
        "q36": {"header": "q36"},
        "authorization": {"header": "Authorization"},
        "content-type": {"header": "Content-Type"},
        "cookies": {"header": "Cookies"},
        "user-agent": {"header": "User-Agent"},
        "accept": {"header": "Accept"},
        "host": {"header": "Host"},
        "accept-encoding": {"header": "Accept-Encoding"},
        "content-length": {"header": "Content-Length"},
        "api-ver": {"header": "api-ver"},
        "payload": {"header": "payload"},
    }

    def __init__(self, **kwargs):
        """
        初始化请求头属性
        :param kwargs: 请求头属性的键值对
        """
        for header in kwargs:
            # 获取属性对应的映射信息
            h = self.header_map.get(header)
            if h is None:
                # 如果传入了不支持的请求头，抛出异常
                raise ValueError(f"不支持的请求头: {header}")

            # 获取期望的属性类型，默认为str
            expected_type = h.get("type", str)
            # 获取实际传入的属性类型
            get_actual_type = type(kwargs[header])

            if expected_type != get_actual_type:
                # 如果类型不匹配，抛出异常
                raise ValueError(
                    f"{header} 的数据类型错误，期望 {expected_type}，实际 {get_actual_type}"
                )

            # 将属性设置到实例上
            setattr(self, header, kwargs[header])

    def __str__(self):
        """
        返回请求头属性的字符串表示
        :return: 请求头属性的字符串表示
        """
        attr = {}
        for name in self.header_map:
            if hasattr(self, name):
                # 将实例上存在的属性添加到attr字典中
                attr[name] = getattr(self, name)
        return str(attr)

    def headers(self):
        """
        生成请求头字典
        :return: 请求头字典
        """
        headers = {}

        for key in self.header_map:
            # 获取属性对应的映射信息
            k = self.header_map.get(key)

            if hasattr(self, key):
                # 如果实例上存在该属性
                val = getattr(self, key)
                if k.get("procedure") is not None and val is not None:
                    # 如果有自定义处理函数，则调用处理函数对属性值进行转换
                    val = k["procedure"](val)
                # 将转换后的属性值设置到请求头字典中
                headers[k["header"]] = val  # type: ignore

        return headers


class HttpbinClientHeader(ClientHeader):
    def __init__(self, **kwargs):
        kwargs.setdefault("plat", PlatformType.ANDROID)
        super(HttpbinClientHeader, self).__init__(**kwargs)
