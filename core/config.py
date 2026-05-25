import tomllib

from pathlib import Path
from typing import Any, Dict
from glom import glom, PathAccessError

from core.enums import Env, ProjectPath


class ConfigLoader:
    _instance = None

    def __new__(cls, env: Env):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance

    def __init__(self, env: Env):
        if hasattr(self, "initialized"):
            return
        self.initialized = True

        self.env = env.value
        self.root_path = Path(ProjectPath.ROOTPATH.value)
        self._config = self._load_config()

    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if cls._instance is None:
            raise Exception("未初始化, 请先初始化框架")
        return cls._instance

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_file = self.root_path / "config" / f"{self.env}.toml"

        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_file}")

        try:
            with open(config_file, "rb") as f:
                return tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"配置文件格式错误: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        try:
            return glom(self._config, key)
        except PathAccessError:
            if default is not None:
                return default
            raise KeyError(f"配置项不存在: {key}")

    def get_env(self) -> str:
        """获取当前环境"""
        return self.env
