from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from faker import Faker

from core.config import ConfigLoader
from core.logger import api_logger as logger
from core.exceptions import DataFactoryError
from core.db import get_db_manager, DatabaseConnection


class BaseDataGenerator(ABC):
    """数据生成器基类"""

    def __init__(self, locale: str = "zh_CN"):
        self.faker = Faker(locale)

    @abstractmethod
    def generate(self, **kwargs) -> Any:
        """生成数据的抽象方法"""
        pass


class FakerDataGenerator(BaseDataGenerator):
    """基于Faker的数据生成器"""

    def __init__(self, locale: str = "zh_CN"):
        super().__init__(locale)

    def generate(self, data_type: str, **kwargs) -> Any:
        """
        生成指定类型的假数据

        Args:
            data_type: 数据类型 (name, email, phone, address等)
            **kwargs: 额外参数
        """
        try:
            if hasattr(self.faker, data_type):
                faker_method = getattr(self.faker, data_type)
                return faker_method()
            else:
                raise DataFactoryError(f"Faker不支持的数据类型: {data_type}")
        except Exception as e:
            raise DataFactoryError(f"Faker数据生成失败: {str(e)}")

    def generate_batch(self, data_type: str, count: int, **kwargs) -> List[Any]:
        """批量生成数据"""
        return [self.generate(data_type, **kwargs) for _ in range(count)]


class DatabaseDataGenerator(BaseDataGenerator):
    """基于数据库的数据生成器"""

    def __init__(self, connection: DatabaseConnection, locale: str = "zh_CN"):
        super().__init__(locale)
        self.connection = connection

    def generate(
        self, query: str, params: Optional[tuple] = None, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        从数据库生成数据

        Args:
            query: SQL查询语句
            params: 查询参数
        """
        try:
            return self.connection.execute_query(query, params)
        except Exception as e:
            raise DataFactoryError(f"数据库数据生成失败: {str(e)}")


class DataFactory:
    """数据工厂主类"""

    def __init__(self):
        self.config = ConfigLoader.get_instance()
        self.faker_generator = FakerDataGenerator()
        self.db_generators = {}
        self.db_manager = get_db_manager()

    def get_faker_generator(self, locale: str = "zh_CN") -> FakerDataGenerator:
        """获取Faker生成器"""
        if locale != "zh_CN":
            return FakerDataGenerator(locale)
        return self.faker_generator

    def get_database_generator(self, connection_name: str) -> DatabaseDataGenerator:
        """获取数据库生成器"""
        if connection_name not in self.db_generators:
            connection = self.db_manager.get_connection(connection_name)
            self.db_generators[connection_name] = DatabaseDataGenerator(connection)

        return self.db_generators[connection_name]

    def cleanup(self):
        """清理资源"""
        self.db_manager.cleanup()
        self.db_generators.clear()
        logger.debug("🧹 数据工厂资源清理完成")


# 全局数据工厂实例
_data_factory_instance = None


def get_data_factory() -> DataFactory:
    """获取全局数据工厂实例"""
    global _data_factory_instance
    if _data_factory_instance is None:
        _data_factory_instance = DataFactory()
    return _data_factory_instance
