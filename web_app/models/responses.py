"""
响应数据模型
"""

from pydantic import BaseModel, field_serializer
from typing import List, Dict, Any, Optional
from datetime import datetime


class TestJobStatus(BaseModel):
    """测试任务状态"""

    job_id: str
    status: str = "pending"
    env: str = "test"
    app: str = "httpbin"
    mark: Optional[str] = None
    skip_git: bool = False
    send_notification: bool = True
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    output: str = ""
    exit_code: int = -1

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class FlowInfo(BaseModel):
    """Flow 基本信息"""

    name: str
    description: str
    class_name: str


class FlowListResponse(BaseModel):
    """Flow 列表响应"""

    success: bool
    data: List[FlowInfo]


class FlowSchemaResponse(BaseModel):
    """Flow Schema 响应"""

    success: bool
    data: Dict[str, Any]


class FlowExecutionResult(BaseModel):
    """Flow 执行结果"""

    flow_name: str
    execution_time: float
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None

    @field_serializer("result")
    def serialize_result(self, value):
        """自定义序列化 result 字段"""
        if value is None:
            return None

        # 如果是 JsonResult 类型，返回其内部数据
        if hasattr(value, "data") and hasattr(value, "extract"):
            return value.data

        # 如果有 dict() 方法，调用它
        if hasattr(value, "dict") and callable(getattr(value, "dict")):
            try:
                return value.dict()
            except Exception:
                pass

        # 如果有 __dict__ 属性，返回它
        if hasattr(value, "__dict__"):
            try:
                return value.__dict__
            except Exception:
                pass

        # 否则返回原值
        return value


class FlowExecutionResponse(BaseModel):
    """Flow 执行响应"""

    success: bool
    data: FlowExecutionResult
