import os
from enum import unique, Enum


@unique
class App(Enum):
    HTTPBIN = "httpbin"


@unique
class Env(Enum):
    TEST = "test"
    PROD = "prod"
    DEV = "dev"


@unique
class PlatformType(Enum):
    ANDROID = "ar"
    IOS = "ip"
    H5 = "h5"


@unique
class UserType(Enum):
    """用户类型枚举"""

    VIP = "vip"
    NORMAL = "normal"
    GUEST = "guest"
    FREE = "free"
    NO_AUTH = "no_auth"


@unique
class ProjectPath(Enum):
    ROOTPATH = "."
    LOG_PATH = os.path.join(ROOTPATH, "output", "logs")
    ALLURE_REPORT_PATH = os.path.join(ROOTPATH, "output", "report")
    ALLURE_RESULT_PATH = os.path.join(ROOTPATH, "output", "allure-results")
    CONFIG_PATH = os.path.join(ROOTPATH, "config")
    PERFORMANCE_TEMP_PATH = os.path.join(ROOTPATH, "data", "static")
