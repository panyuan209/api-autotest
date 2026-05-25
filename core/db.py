import re
import threading
import pymysql

from contextlib import contextmanager
from typing import Dict, Any, List, Optional, Union
from core.config import ConfigLoader
from core.logger import api_logger as logger
from core.exceptions import DataFactoryError

# SQL 标识符验证正则：只允许字母、数字、下划线，且不能以数字开头
_SQL_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _validate_sql_identifier(name: str, label: str = "SQL标识符") -> str:
    """
    验证 SQL 标识符（表名、列名）是否安全

    Args:
        name: 待验证的标识符
        label: 标识符的描述（用于错误信息）

    Returns:
        验证通过的标识符

    Raises:
        DataFactoryError: 标识符包含非法字符
    """
    if not _SQL_IDENTIFIER_RE.match(name):
        raise DataFactoryError(
            f"{label}包含非法字符: '{name}'，只允许字母、数字和下划线，且不能以数字开头"
        )
    return name


class DatabaseConnection:
    """数据库连接管理类"""

    _connections: Dict[str, "DatabaseConnection"] = None  # type: ignore
    _lock: threading.Lock = None  # type: ignore

    def __init__(self, connection_name: str):
        self.connection_name = connection_name
        self.config = ConfigLoader.get_instance()
        self.db_config = self.config.get(f"database.{connection_name}")
        self.connection = None

    @classmethod
    def _ensure_registry(cls):
        """延迟初始化类级别的连接池注册表"""
        if cls._connections is None:
            cls._connections = {}
        if cls._lock is None:
            cls._lock = threading.Lock()

    @classmethod
    def get_connection(cls, connection_name: str):
        """获取数据库连接（单例模式）"""
        cls._ensure_registry()
        with cls._lock:
            if connection_name not in cls._connections:
                cls._connections[connection_name] = cls(connection_name)
            return cls._connections[connection_name]

    def connect(self):
        """建立数据库连接"""
        if self.connection is None:
            try:
                self.connection = pymysql.connect(
                    host=self.db_config["host"],
                    port=self.db_config.get("port", 3306),
                    user=self.db_config["user"],
                    password=self.db_config["password"],
                    database=self.db_config["database"],
                    charset=self.db_config.get("charset", "utf8mb4"),
                    autocommit=True,
                )
                logger.debug(f"🔗 MySQL数据库连接建立成功: {self.connection_name}")
            except Exception as e:
                raise DataFactoryError(f"MySQL数据库连接失败: {str(e)}")

    @contextmanager
    def get_cursor(self):
        """获取数据库游标上下文管理器"""
        if self.connection is None:
            self.connect()

        cursor = self.connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    def execute_query(
        self, query: str, params: Optional[Union[tuple, list]] = None
    ) -> List[Dict[str, Any]]:
        """执行查询"""
        try:
            with self.get_cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                columns = (
                    [desc[0] for desc in cursor.description]
                    if cursor.description
                    else []
                )
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]

                return results
        except Exception as e:
            logger.error(f"查询执行失败: {query} - {str(e)}")
            raise DataFactoryError(f"查询执行失败: {str(e)}")

    def execute_non_query(
        self, query: str, params: Optional[Union[tuple, list]] = None
    ) -> int:
        """执行非查询语句（INSERT, UPDATE, DELETE）"""
        try:
            with self.get_cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                return cursor.rowcount
        except Exception as e:
            logger.error(f"非查询语句执行失败: {query} - {str(e)}")
            raise DataFactoryError(f"非查询语句执行失败: {str(e)}")

    def execute_batch(self, query: str, params_list: List[Union[tuple, list]]) -> int:
        """批量执行语句"""
        try:
            with self.get_cursor() as cursor:
                cursor.executemany(query, params_list)

                return cursor.rowcount
        except Exception as e:
            logger.error(f"批量执行失败: {query} - {str(e)}")
            raise DataFactoryError(f"批量执行失败: {str(e)}")

    def close(self):
        """关闭连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.debug(f"🔒 MySQL数据库连接已关闭: {self.connection_name}")


class DatabaseOperations:
    """数据库操作类，提供CRUD操作的高级接口"""

    def __init__(self, connection: DatabaseConnection):
        self.connection = connection

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """插入单条记录"""
        _validate_sql_identifier(table, "表名")
        columns = [_validate_sql_identifier(col, "列名") for col in data.keys()]
        placeholders = ", ".join(["%s"] * len(columns))
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        return self.connection.execute_non_query(query, list(data.values()))

    def insert_batch(self, table: str, data_list: List[Dict[str, Any]]) -> int:
        """批量插入记录"""
        if not data_list:
            return 0
        _validate_sql_identifier(table, "表名")
        columns = [_validate_sql_identifier(col, "列名") for col in data_list[0].keys()]
        placeholders = ", ".join(["%s"] * len(columns))
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        params_list = [list(data.values()) for data in data_list]
        return self.connection.execute_batch(query, params_list)

    def update(
        self,
        table: str,
        data: Dict[str, Any],
        where_clause: str,
        where_params: Optional[Union[tuple, list]] = None,
    ) -> int:
        """更新记录"""
        _validate_sql_identifier(table, "表名")
        validated_cols = [_validate_sql_identifier(col, "列名") for col in data.keys()]
        set_clause = ", ".join([f"{col} = %s" for col in validated_cols])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        params = list(data.values())
        if where_params:
            params.extend(
                where_params
                if isinstance(where_params, (list, tuple))
                else [where_params]
            )
        return self.connection.execute_non_query(query, params)

    def delete(
        self,
        table: str,
        where_clause: str,
        where_params: Optional[Union[tuple, list]] = None,
    ) -> int:
        """删除记录"""
        _validate_sql_identifier(table, "表名")
        query = f"DELETE FROM {table} WHERE {where_clause}"
        return self.connection.execute_non_query(query, where_params)

    def select(
        self,
        table: str,
        columns: str = "*",
        where_clause: str = "",
        where_params: Optional[Union[tuple, list]] = None,
        order_by: str = "",
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """查询记录"""
        _validate_sql_identifier(table, "表名")
        # 验证列名（支持 * 和逗号分隔的列名列表）
        if columns != "*":
            for col in columns.split(","):
                col = col.strip()
                if col and col != "*":
                    _validate_sql_identifier(col, "列名")
        # 验证 order_by 中的列名
        if order_by:
            for part in order_by.split(","):
                col = part.strip().split()[0]  # 去掉 ASC/DESC
                if col:
                    _validate_sql_identifier(col, "排序列名")
        query = f"SELECT {columns} FROM {table}"
        params = []
        if where_clause:
            query += f" WHERE {where_clause}"
            if where_params:
                params = (
                    list(where_params)
                    if isinstance(where_params, (list, tuple))
                    else [where_params]
                )
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit:
            query += f" LIMIT {limit}"
        return self.connection.execute_query(query, params if params else None)


class DatabaseManager:
    """数据库管理器，统一管理数据库连接和操作"""

    def __init__(self, config: Optional[ConfigLoader] = None):
        self.config = config or ConfigLoader._instance
        self.connections = {}
        self.operations = {}

    def get_connection(self, connection_name: str) -> DatabaseConnection:
        """获取数据库连接"""
        if connection_name not in self.connections:
            self.connections[connection_name] = DatabaseConnection.get_connection(
                connection_name
            )

        return self.connections[connection_name]

    def get_operations(self, connection_name: str) -> DatabaseOperations:
        """获取数据库操作对象"""
        if connection_name not in self.operations:
            connection = self.get_connection(connection_name)
            self.operations[connection_name] = DatabaseOperations(connection)

        return self.operations[connection_name]

    def cleanup(self):
        """清理所有数据库连接"""
        for connection in self.connections.values():
            connection.close()
        self.connections.clear()
        self.operations.clear()
        logger.debug("🧹 数据库管理器资源清理完成")


# 全局数据库管理器实例
_db_manager_instance = None
_db_manager_lock = threading.Lock()


def get_db_manager() -> DatabaseManager:
    """获取全局数据库管理器实例"""
    global _db_manager_instance
    if _db_manager_instance is None:
        with _db_manager_lock:
            if _db_manager_instance is None:  # 双重检查
                _db_manager_instance = DatabaseManager()
    return _db_manager_instance
