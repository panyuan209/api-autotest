from core.config import ConfigLoader
from core.enums import App, Env
from core.logger import api_logger as logger
from utils.utils import get_worker_id


class Initializer:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        env: Env = Env.TEST,
        app: App = App.HTTPBIN,
    ):
        if hasattr(self, "initialized"):
            return
        self.initialized = True

        self.env = env
        self.app = app

        self.worker_id = get_worker_id()
        self.config = None
        self.sql = None

        self.initialize()

    def initialize(self):
        self.config = self._get_config()
        logger.set_config_log_level()

        return self

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            raise Exception("未初始化, 请先初始化框架")
        return cls._instance

    def _get_config(self):
        """获取配置信息"""
        config = ConfigLoader(self.env)
        logger.labeled(
            "框架初始化",
            f"Worker [{self.worker_id}] 加载 [{self.env}] 环境配置",
            icon="🏗️",
        )
        return config

    def _connect_sql(self):
        """连接数据库"""
        pass

    def cleanup(self):
        """清理资源"""
        logger.labeled(
            "框架清理", f"Worker [{self.worker_id}] 框架实例已清理", icon="🏗️"
        )

        # 清理配置实例
        if hasattr(self, "config") and self.config:
            # 重置配置单例，为下次测试准备
            ConfigLoader._instance = None

        # 清理其他资源
        if hasattr(self, "sql") and self.sql:
            # 如果有数据库连接，关闭它
            pass
