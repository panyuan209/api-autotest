"""
FastAPI 服务主入口
"""

import os
import uvicorn

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from web_app.services.flow_service import FlowService
from web_app.models.requests import FlowExecutionRequest
from web_app.models.responses import (
    FlowListResponse,
    FlowSchemaResponse,
    FlowExecutionResponse,
)

app = FastAPI(
    title="测试数据构造服务",
    description="个用于测试数据构造的 FastAPI 服务",
    version="1.0.0",
)

# 配置 CORS
environment = os.getenv("ENVIRONMENT", "dev")

if environment == "prod":
    # 生产环境 CORS 配置
    allowed_origins = [
        "*",
        # 添加其他允许的域名
    ]
else:
    # 开发环境允许所有来源
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# 初始化服务
flow_service = FlowService()

# 静态文件服务（用于前端页面）
app.mount("/static", StaticFiles(directory="web_app/static"), name="static")


@app.get("/")
async def index():
    """返回前端页面"""
    return FileResponse("web_app/static/index.html")


@app.get("/api/apps")
async def get_apps():
    """获取所有可用的应用列表"""
    try:
        apps = flow_service.get_available_apps()
        return {"success": True, "data": apps}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/flows/{app_name}", response_model=FlowListResponse)
async def get_flows(app_name: str):
    """获取指定应用的所有 Flow 列表"""
    try:
        flows = flow_service.get_flows_by_app(app_name)
        return FlowListResponse(success=True, data=flows)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/flows/{app_name}/{flow_name}/schema", response_model=FlowSchemaResponse)
async def get_flow_schema(app_name: str, flow_name: str):
    """获取指定 Flow 的参数 schema"""
    try:
        schema = flow_service.get_flow_schema(app_name, flow_name)
        return FlowSchemaResponse(success=True, data=schema)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post(
    "/api/flows/{app_name}/{flow_name}/execute", response_model=FlowExecutionResponse
)
async def execute_flow(app_name: str, flow_name: str, request: FlowExecutionRequest):
    """执行指定的 Flow"""
    try:
        result = flow_service.execute_flow(
            app_name, flow_name, request.params, environment=request.environment
        )
        return FlowExecutionResponse(success=True, data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8880,
        reload=True,
        reload_dirs=["web_app", "core", "business"],
    )
