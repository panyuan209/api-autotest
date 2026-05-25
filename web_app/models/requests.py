"""
请求数据模型
"""

from pydantic import BaseModel
from typing import Dict, Any, Optional


class FlowExecutionRequest(BaseModel):
    """Flow 执行请求模型"""

    params: Dict[str, Any] = {}
    environment: Optional[str] = "test"
    description: Optional[str] = None
