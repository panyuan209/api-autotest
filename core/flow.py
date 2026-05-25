from abc import abstractmethod
from typing import Dict, Any, Type, Optional
import time
import traceback

from pydantic import BaseModel, ValidationError as PydanticValidationError

from core.config import ConfigLoader
from core.exceptions import FlowExecutionError, ValidationError
from core.logger import api_logger as logger, LogFormatter


class Flow:
    """
    所有 Flow 的基类
    """

    def __init__(self, params=None, **kwargs):
        """
        初始化 Flow 实例
        """
        self.execution_metrics = {}
        self.params = params if params is not None else {}
        self.config: None | ConfigLoader = ConfigLoader._instance

        self.setup(**kwargs)
        self._validate_schema()

    @abstractmethod
    def setup(self, **kwargs):
        """
        设置方法，用于初始化 Flow 的参数和其他必要的设置
        """
        pass

    def teardown(self):
        """
        清理方法，用于释放资源或进行必要的清理工作
        """
        pass

    @abstractmethod
    def _run(self):
        pass

    def run(self) -> Any:
        """执行Flow，包含异常处理和性能监控"""
        flow_name = self.name()
        start_time = time.time()

        try:
            logger.section(f"FLOW开始: {flow_name}")
            logger.labeled("描述", self.desc(), icon="📝")
            logger.json_log(self.params, "输入参数")

            # 执行Flow
            result = self._run()

            execution_time = time.time() - start_time

            # 记录执行指标
            self.execution_metrics = {
                "flow_name": flow_name,
                "execution_time": execution_time,
                "success": True,
                "error": None,
                "timestamp": time.time(),
            }

            logger.section(f"FLOW成功: {flow_name}")
            logger.timing("执行时间", execution_time)
            logger.labeled("执行结果", "success", icon="📤")

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            error_trace = traceback.format_exc()

            self.execution_metrics = {
                "flow_name": flow_name,
                "execution_time": execution_time,
                "success": False,
                "error": str(e),
                "timestamp": time.time(),
            }

            logger.section(f"FLOW失败: {flow_name}", "error")
            logger.timing("执行时间", execution_time, "error")
            logger.labeled("执行结果", "failed", icon="📥")
            logger.labeled("错误信息", str(e), "error", "💥")
            logger.error(f"📍 【错误堆栈】\n{error_trace}")

            raise FlowExecutionError(f"Flow {flow_name} execution failed: {str(e)}")

        finally:
            # 执行清理
            try:
                self.teardown()
            except Exception as e:
                logger.warning(f"⚠️ Flow清理过程中发生错误: {str(e)}")

    @classmethod
    @abstractmethod
    def desc(cls):
        """
        返回 Flow 的描述信息
        :return: 描述信息字符串
        """
        pass

    @classmethod
    @abstractmethod
    def name(cls):
        """
        返回 Flow 的名称
        :return: 名称字符串
        """
        pass

    @classmethod
    def web_visible(cls):
        """
        返回 Flow 是否在 Web 页面中可见
        默认为 False，子类可以重写此方法来标记为可见
        :return: 布尔值，True 表示在 Web 页面中可见
        """
        return False

    @classmethod
    @abstractmethod
    def schema(cls):
        """
        返回 Flow 的验证 Schema
        :return: Pydantic BaseModel 类或 None
        """
        pass

    def _validate_schema(self):
        """使用 Pydantic 进行参数验证"""
        try:
            schema_model = self.schema()
            if schema_model is not None:
                # 使用 Pydantic model 验证参数
                validated_data = schema_model(**self.params)
                # 更新 params 为验证后的数据
                self.params = validated_data.model_dump()
                logger.status("参数验证", "通过", "debug")
                logger.debug(f"📊 验证参数: {LogFormatter.format_json(self.params)}")
            else:
                logger.warning("⚠️ Schema 为空，跳过参数验证")
        except PydanticValidationError as e:
            error_msg = f"参数验证失败：{str(e)}"
            logger.status("参数验证", "失败", "error")
            logger.error(f"💥 {error_msg}")
            raise ValidationError(error_msg)
        except TypeError as e:
            error_msg = f"参数验证失败（类型错误）：{str(e)}"
            logger.status("参数验证", "失败", "error")
            logger.error(f"💥 {error_msg}")
            raise ValidationError(error_msg)

    @staticmethod
    def create_schema(params: Dict[str, Dict[str, Any]]) -> Type[BaseModel]:
        """
        创建 Pydantic Model 类

        :param params: 参数定义字典
        :return: Pydantic BaseModel 类

        使用方法：
        1. 为每个参数定义一个字典，包含 type, description, 和 required（可选）键。
        2. type 可以使用 Python 类型（str, int, bool, list, dict）。

        示例：
        {
            "username": {"type": str, "description": "用户名", "required": True},
            "age": {"type": int, "description": "年龄"},
            "is_active": {"type": bool, "description": "是否激活"},
            "tags": {"type": list, "description": "标签"},
            "profile": {"type": dict, "description": "用户资料"}
        }
        """
        from pydantic import Field
        from typing import Optional as TypingOptional

        # 构建字段定义
        fields = {}
        annotations = {}

        for param_name, param_info in params.items():
            param_type = param_info["type"]
            description = param_info["description"]
            is_required = param_info.get("required", False)

            if is_required:
                # 必填字段
                fields[param_name] = Field(description=description)
                annotations[param_name] = param_type
            else:
                # 可选字段
                fields[param_name] = Field(default=None, description=description)
                annotations[param_name] = TypingOptional[param_type]

        # 动态创建 Pydantic 模型类
        model_class = type(
            "DynamicSchema", (BaseModel,), {"__annotations__": annotations, **fields}
        )

        return model_class

    @classmethod
    def get_json_schema(cls) -> Optional[Dict[str, Any]]:
        """
        获取 JSON Schema
        :return: JSON Schema 字典或 None
        """
        schema_model = cls.schema()
        if schema_model is not None:
            return schema_model.model_json_schema()
        return None

    def get_execution_metrics(self) -> Dict[str, Any]:
        """获取执行指标"""
        return self.execution_metrics

    def get_params(self, key: str, default: Any = None) -> Any:
        """获取参数值"""
        params = self.params.get(key)

        return params if params is not None else default
