"""
Flow 服务 - 负责扫描、加载和执行 Flow
"""

import os
import importlib
import inspect
import traceback
from typing import List, Dict, Any


from core.flow import Flow
from core.initializer import Initializer
from core.enums import Env, App, ProjectPath
from core.logger import api_logger as logger
from web_app.models.responses import FlowInfo, FlowExecutionResult


class FlowService:
    """Flow 服务类"""

    def __init__(self):
        self._flow_cache = {}  # 缓存已扫描的 Flow 类
        self._initialized_apps = {}  # 缓存已初始化的应用环境

    def get_available_apps(self) -> List[str]:
        """获取所有可用的应用"""
        business_path = os.path.join(ProjectPath.ROOTPATH.value, "business")
        if not os.path.exists(business_path):
            return []

        apps = []
        for item in os.listdir(business_path):
            item_path = os.path.join(business_path, item)
            if os.path.isdir(item_path) and not item.startswith("_"):
                flow_path = os.path.join(item_path, "flow")
                if os.path.exists(flow_path):
                    apps.append(item)

        return apps

    def get_flows_by_app(self, app_name: str) -> List[FlowInfo]:
        """获取指定应用的所有 Flow"""
        if app_name in self._flow_cache:
            return self._flow_cache[app_name]

        flows = []
        flow_path = os.path.join(
            ProjectPath.ROOTPATH.value, "business", app_name, "flow"
        )

        if not os.path.exists(flow_path):
            raise ValueError(f"应用 {app_name} 不存在")

        # 扫描 flow 目录中的所有 Python 文件
        for filename in os.listdir(flow_path):
            if (
                filename.endswith(".py")
                and filename != "__init__.py"
                and filename != "base.py"
            ):
                module_name = filename[:-3]  # 去掉 .py 后缀

                try:
                    # 动态导入模块
                    module_path = f"business.{app_name}.flow.{module_name}"
                    module = importlib.import_module(module_path)

                    # 查找模块中的 Flow 类
                    for name, obj in inspect.getmembers(module):
                        if (
                            inspect.isclass(obj)
                            and issubclass(obj, Flow)
                            and obj != Flow
                        ):  # 排除 Flow 基类
                            # 检查是否是具体的 Flow 实现（不是应用基类）
                            module_obj = inspect.getmodule(obj)
                            if module_obj and module_obj.__name__ == module_path:
                                # 检查 Flow 是否标记为 Web 可见
                                if not obj.web_visible():
                                    logger.debug(
                                        f"跳过不可见的 Flow: {name} -> {obj.name()}"
                                    )
                                    continue

                                # 获取 Flow 信息
                                try:
                                    flow_info = FlowInfo(
                                        name=obj.name(),
                                        description=obj.desc(),
                                        class_name=f"{module_path}.{name}",
                                    )
                                    flows.append(flow_info)
                                    logger.info(
                                        f"找到可见的 Flow: {name} -> {obj.name()}"
                                    )
                                except Exception as e:
                                    logger.warning(
                                        f"获取 Flow {name} 信息时出错: {str(e)}"
                                    )
                                    continue
                            else:
                                logger.debug(
                                    f"跳过导入的 Flow: {name} (来源: {module_obj.__name__ if module_obj else 'Unknown'})"
                                )

                except Exception as e:
                    logger.warning(f"扫描 Flow 文件 {filename} 时出错: {str(e)}")
                    continue  # 缓存结果
        self._flow_cache[app_name] = flows
        return flows

    def get_flow_schema(self, app_name: str, flow_name: str) -> Dict[str, Any]:
        """获取指定 Flow 的 schema"""
        flow_class = self._get_flow_class(app_name, flow_name)
        if not flow_class:
            raise ValueError(f"Flow {flow_name} 在应用 {app_name} 中不存在")

        schema = flow_class.get_json_schema()
        if schema is None:
            schema = {"type": "object", "properties": {}}

        # 添加 Flow 的描述信息
        schema["description"] = flow_class.desc()

        return schema

    def execute_flow(
        self,
        app_name: str,
        flow_name: str,
        params: Dict[str, Any],
        environment: str | None = "test",
    ) -> FlowExecutionResult:
        """执行指定的 Flow"""
        try:
            # 获取 Flow 类
            flow_class = self._get_flow_class(app_name, flow_name)
            if not flow_class:
                raise ValueError(f"Flow {flow_name} 在应用 {app_name} 中不存在")

            # 初始化应用环境
            ctx = self._get_or_create_app_context(app_name, environment)

            # 创建 Flow 实例并执行
            flow_instance = flow_class(params=params, client_session=ctx.client_session)

            # 执行 Flow
            result = flow_instance.run()
            metrics = flow_instance.get_execution_metrics()

            return FlowExecutionResult(
                flow_name=flow_name,
                execution_time=metrics.get("execution_time", 0),
                success=True,
                result=result,
                metrics=metrics,
            )

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"执行 Flow {flow_name} 失败: {str(e)}")
            logger.error(f"错误堆栈: {error_trace}")

            return FlowExecutionResult(
                flow_name=flow_name,
                execution_time=0,
                success=False,
                error=str(e),
                result=None,
            )

    def _get_flow_class(self, app_name: str, flow_name: str):
        """获取 Flow 类"""
        flows = self.get_flows_by_app(app_name)

        for flow_info in flows:
            if flow_info.name == flow_name:
                # 从类名字符串导入类
                module_path, class_name = flow_info.class_name.rsplit(".", 1)
                module = importlib.import_module(module_path)
                return getattr(module, class_name)

        return None

    def _get_or_create_app_context(self, app_name: str, environment: str = "test"):
        """获取或创建应用上下文"""
        # 使用应用名和环境作为缓存键
        cache_key = f"{app_name}_{environment}"

        if cache_key in self._initialized_apps:
            return self._initialized_apps[cache_key]

        # 创建新的应用上下文
        try:
            app_enum = App(app_name.upper())
        except ValueError:
            app_enum = App.HTTPBIN

        # 根据环境参数选择环境
        env_enum = Env.PROD if environment.lower() == "prod" else Env.TEST

        # 检查是否需要环境切换
        if Initializer._instance:
            # 如果当前环境与请求的环境不同，需要清理并重置
            current_env = getattr(Initializer._instance, "env", None)
            if current_env != env_enum:
                # 先清理现有实例的资源
                Initializer._instance.cleanup()
                Initializer._instance = None
                # 清空所有应用缓存，因为它们都基于旧的环境配置
                self._initialized_apps.clear()

        ctx = Initializer(
            env=env_enum,
            app=app_enum,
        )

        # 为不同的应用创建对应的 ClientSession
        from core.api import ClientSession

        if app_name.lower() == "httpbin":
            from core.client_header import HttpbinClientHeader

            client_session = ClientSession(client=HttpbinClientHeader())
        else:
            # 默认使用 HttpbinClientHeader
            from core.client_header import HttpbinClientHeader

            client_session = ClientSession(client=HttpbinClientHeader())

        # 将 client_session 作为上下文的属性
        setattr(ctx, "client_session", client_session)

        self._initialized_apps[cache_key] = ctx
        return ctx

    def cleanup(self):
        """清理资源"""
        for ctx in self._initialized_apps.values():
            try:
                ctx.cleanup()
            except Exception as e:
                logger.warning(f"清理应用上下文时出错: {str(e)}")

        self._initialized_apps.clear()
        self._flow_cache.clear()
