# API 自动化测试框架

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![Pytest](https://img.shields.io/badge/Pytest-8.3.5-green.svg)](https://pytest.org/)
[![Allure](https://img.shields.io/badge/Allure-2.14.3-orange.svg)](http://allure.qatools.ru/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)

一个基于 Python 的接口自动化测试框架，采用四层分离架构设计，集成 Flow 模式的业务流程编排、智能认证管理、多环境配置、并发测试执行、可视化测试报告生成和前端测试数据构造管理页面。

## ✨ 核心特性

### 🏗️ 分层架构设计

- **测试层 (Tests)** - 基于 Pytest 的测试用例组织
- **业务层 (Business)** - Flow 模式的业务流程封装
- **接口层 (APIs)** - 统一的 API 调用封装
- **核心层 (Core)** - 框架底层能力支撑

### 🚀 高级功能特性

- **Flow 编排引擎** - 基于抽象基类的业务流程标准化
- **智能认证管理** - 多应用认证策略自动管理
- **多环境配置** - TOML 配置文件支持 test/dev/prod 环境切换
- **高性能并发** - 基于 pytest-xdist 的多进程并发执行
- **实时性能监控** - API 响应时间和性能指标统计
- **可视化报告** - 集成 Allure 详细测试报告
- **Web 管控台** - FastAPI 驱动的 Flow 执行管理界面

## 📁 项目架构

```
api_test/
├── 🧪 tests/                 # 测试用例层(按不同应用划分)
│   └── httpbin/              #   HttpBin(示例应用)
├── 🏢 business/              # 业务流程层
│   └── httpbin/              #   Httpbin 示例业务流程
│       ├── apis/             #     接口定义
│       └── flow/             #     Flow 流程
├── ⚙️ core/                  # 核心功能层
│   ├── api.py                #   API 调用引擎
│   ├── flow.py               #   Flow 基础框架
│   ├── auth_manager.py       #   认证管理器
│   ├── client_header.py      #   请求头构造器
│   ├── config.py             #   配置加载器
│   ├── logger.py             #   结构化日志
│   └── initializer.py        #   框架初始化器
├── 🛠️ utils/                 # 工具支撑层
│   ├── decorator.py          #   装饰器工具
│   ├── httpbin_auth_strategy.py  # 认证策略示例
│   └── utils.py              #   通用工具函数
├── 🌐 web_app/               # Web 管控台
│   ├── main.py               #   FastAPI 应用入口
│   ├── services/             #   业务服务
│   └── static/               #   前端界面
├── ⚙️ config/                # 环境配置
│   ├── test.toml             #   测试环境配置
│   ├── dev.toml              #   开发环境配置
│   └── prod.toml             #   生产环境配置
├── 📊 output/                # 输出文件
│   ├── allure-results/       #   Allure 结果数据
│   ├── report/               #   测试报告
│   └── logs/                 #   执行日志
├── conftest.py               # Pytest 全局配置
├── run_test.py               # 测试执行入口
└── pyproject.toml            # 项目依赖配置
```

## 🚀 快速开始

### 环境准备

```bash
# 确保已安装 Python 3.13+ 和 uv
python --version  # >= 3.13
uv --version

# 安装依赖
uv sync
```

### 运行方式

#### 1️⃣ 命令行执行

```bash
# 基础用法（默认运行 httpbin 示例测试）
python run_test.py

# 指定环境和应用
python run_test.py --env dev --app httpbin

# 指定测试标记
python run_test.py --mark p0

# 直接运行 pytest
pytest tests/httpbin/ -v
```

#### 2️⃣ Web 管控台

```bash
# 开发模式启动
cd web_app && uvicorn main:app --reload --port 8880

# 访问管控台
open http://127.0.0.1:8880
```

### 查看测试报告

```bash
# 生成并查看 Allure 报告
allure serve ./output/allure-results
```

## 📖 开发指南

### 🔧 框架核心概念

#### Flow 模式

框架采用 Flow 模式封装业务逻辑，每个 Flow 代表一个完整的业务流程（最小为一个接口）：

```python
# business/your_app/flow/example.py
from core.flow import Flow

class ExampleFlow(Flow):
    def desc(self):
        return "示例业务流程"

    def setup(self, client_session):
        self.api = YourAppApi(client_session)

    def _run(self):
        # 实现具体业务逻辑
        username = self.get_param("username")
        return self.api.login(json={"username": username})
```

#### 智能认证管理

框架内置多应用认证策略，自动管理 Token 和签名：

```python
# core/auth_manager.py 自动处理认证
class YourAppApi(Api):
    HOST_KEY = "host.your_app_host"
    APP_NAME = App.YOUR_APP  # 指定应用名称即可自动认证
```

#### 配置管理

支持多环境配置，自动加载对应环境配置文件：

```toml
# config/test.toml
[host]
your_app_host = "http://test.your-app.com"

[auth]
[auth.your_app]
username = "test_user"
password = "test_password"
```

### 🛠️ 开发流程

#### 1. 创建 API 封装

```python
# business/your_app/apis/api.py
from core.api import Api
from core.enums import App

class YourAppApi(Api):
    HOST_KEY = "host.your_app_host"
    APP_NAME = App.YOUR_APP

    def login(self, **kwargs):
        return self.post("/api/login", **kwargs)

    def get_user_info(self, **kwargs):
        return self.get("/api/user/info", **kwargs)
```

#### 2. 实现基础 Flow

```python
# business/your_app/flow/base.py
from core.flow import Flow
from business.your_app.apis.api import YourAppApi

class YourAppFlow(Flow):
    def setup(self, client_session):
        self.client_session = client_session
        self.api = YourAppApi(self.client_session)
```

#### 3. 编写业务 Flow

```python
# business/your_app/flow/login.py
from business.your_app.flow.base import YourAppFlow

class LoginFlow(YourAppFlow):
    def desc(self):
        return "用户登录流程"

    def _run(self):
        username = self.get_param("username")
        password = self.get_param("password")

        response = self.api.login(
            json={"username": username, "password": password}
        )

        return response.json()
```

#### 4. 生成测试数据

```python
# business/your_app/data/generate_user.py
def generate_user(user_type="normal"):
    """生成测试用户数据"""
    users = {
        "normal": {"username": "test_user", "password": "test_pwd"},
        "vip": {"username": "vip_user", "password": "vip_pwd"}
    }
    return users.get(user_type, users["normal"])
```

#### 5. 编写测试用例

```python
# tests/your_app/test_login.py
import allure
import pytest
from business.your_app.flow.login import LoginFlow
from business.your_app.data.generate_user import generate_user

@allure.feature("登录功能测试")
class TestLogin:

    @pytest.mark.p0
    @allure.title("正常用户登录测试")
    def test_normal_user_login(self):
        user = generate_user("normal")

        result = LoginFlow(params=user).run()

        assert result["code"] == 200
        assert "token" in result["data"]
```

## 🔧 高级功能

### 📊 性能监控

框架内置 API 性能监控，自动统计响应时间：

```python
# 获取性能统计数据
api = YourAppApi(client_session)
summary = api.get_performance_summary()
print(f"平均响应时间: {summary['avg_response_time']}ms")
```

### 🧪 并发测试执行

```bash
# pytest-xdist 自动并发
pytest -n auto  # 自动检测CPU核心数

# 指定进程数
pytest -n 3

# 按模块分发（推荐）
pytest -n auto --dist=loadscope
```

### 🏷️ 测试分级标记

```python
@pytest.mark.p0  # P0级别 - 核心功能
@pytest.mark.p1  # P1级别 - 重要功能
@pytest.mark.p2  # P2级别 - 一般功能

# 执行指定级别测试
pytest -m p0
pytest -m "p0 or p1"
```

### 🔄 重试机制

```bash
# 失败重试配置（在 pyproject.toml 中）
--reruns 2 --reruns-delay 3  # 失败重试2次，间隔3秒
```

### 📝 结构化日志

框架提供丰富的结构化日志记录：

```python
from core.logger import api_logger as logger

# 标签化日志
logger.labeled("业务流程", "用户登录成功", uid=12345)

# JSON 格式日志
logger.json_log({"request": data, "response": result})

# 性能日志
logger.performance("API调用", duration=1.23, endpoint="/api/login")
```

## 🌐 Web 管控台

框架提供基于 FastAPI 的 Web 管控台，支持：

- **Flow 可视化执行** - 在线选择和执行业务流程
- **动态参数配置** - 可视化参数输入界面
- **实时执行监控** - 执行状态和结果实时显示
- **多环境切换** - 支持在线环境切换

```bash
# 开发模式启动
cd web_app && uvicorn main:app --reload --port 8880

# 访问地址: http://127.0.0.1:8880
```

## 📚 最佳实践

### 🎯 测试用例设计原则

1. **单一职责** - 每个测试用例只验证一个功能点
2. **独立性** - 测试用例间不相互依赖
3. **可重复** - 多次执行结果一致
4. **有意义的命名** - 测试名称清晰表达测试意图

### 🔧 Flow 设计规范

1. **职责明确** - 每个 Flow 封装一个完整业务流程
2. **参数标准化** - 使用 `get_param()` 获取参数
3. **异常处理** - 合理处理和传递异常信息
4. **性能考量** - 避免不必要的重复调用

### 📊 数据管理策略

1. **环境隔离** - 不同环境使用不同测试数据
2. **数据生成** - 使用数据工厂模式生成测试数据
3. **敏感数据** - 配置文件中的敏感信息加密存储

## 🤝 贡献指南

### 提交流程

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件
