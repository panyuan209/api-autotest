# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

API 自动化测试框架 (api-autotest) — a Python-based API testing framework with four-layer separation (tests/business/core/utils), Flow-based business orchestration, smart auth management, multi-environment config, parallel test execution via pytest-xdist, and Allure reporting.

## Build/Lint/Test Commands

### Environment Setup
```bash
uv sync  # Python 3.13+ required
```

### Running Tests
```bash
pytest                                    # All tests (default env: test, app: httpbin)
python run_test.py                        # Wrapper script
python run_test.py --app httpbin          # Specific app
python run_test.py --env dev --app httpbin # With env selection
python run_test.py --mark p0              # By marker (p0/p1/p2)
```

### Running Single Tests
```bash
pytest tests/httpbin/test_http_method.py                          # File
pytest tests/httpbin/test_http_method.py::TestHttpMethod           # Class
pytest tests/httpbin/test_http_method.py::TestHttpMethod::test_get # Method
pytest -k "test_get"                                               # By keyword
```

### Default Pytest Options (`pyproject.toml`)
`-vs --alluredir=./output/allure-results -n 3 --dist=loadscope --capture=no --timeout=300 --tb=short`

### Allure Reports
```bash
allure serve ./output/allure-results
```

## Architecture

### Four-Layer Separation
1. **tests/** — Pytest cases organized by app (e.g., httpbin)
2. **business/** — Flow-based logic: `apis/` (API wrappers), `flow/` (business flows), `data/` (test data)
3. **core/** — Framework core: `api.py`, `flow.py`, `config.py`, `logger.py`, `auth_manager.py`, `client_header.py`, `exceptions.py`
4. **utils/** — Shared utilities: decorators, crypto tools, auth strategies

### Key Components
- **web_app/** — FastAPI-based management console for Flow execution
- **config/*.toml** — Environment configs (dev/test/prod)
- **core/enums.py** — App/Env/PlatformType/UserType enums; App values: `httpbin`

## Code Patterns

### API Class Pattern
```python
from core.api import Api
from core.enums import App
from utils.decorator import json

class YourApi(Api):
    HOST_KEY = "host.your_host"
    APP_NAME = App.YOUR_APP

    @json
    def endpoint(self, **kwargs):
        return self.post("/api/path", **kwargs)
```

### Flow Class Pattern
```python
from core.flow import Flow

class ExampleFlow(Flow):
    @classmethod
    def name(cls): return "ExampleFlow"
    @classmethod
    def desc(cls): return "Flow description"
    @classmethod
    def schema(cls):
        return cls.create_schema({"param": {"type": str, "description": "desc", "required": True}})

    def setup(self, client_session=None, **kwargs):
        self.api = YourApi(client_session)

    def _run(self):
        return self.api.some_method(json={"data": self.get_params("param")})
```

### Test Class Pattern
```python
import allure, pytest
from business.app.flow.get_flow import GetFlow
from tests.app.app_test import AppTest

class TestFeature(AppTest):
    @pytest.mark.p0
    @allure.feature("Feature Name")
    @allure.title("Test case title")
    def test_something(self):
        with allure.step("Step description"):
            result = GetFlow(params={"key": "value"}).run()
            assert result.extract("json.key") == "value"
```

### Test Base Classes
Each app has a base test class in `tests/<app>/` (e.g., `HttpbinTest`) that provides `setup_class` with ClientSession registration.

### Decorators
- `@json` — Parse response as JSON, wraps in `JsonResult`; use `.extract("jmespath")` for data extraction

### Logging
```python
from core.logger import api_logger as logger
logger.info("Message")
logger.labeled("Label", value, icon="📊")
logger.json_log(data, "Description")
logger.timing("Operation", duration)
```

## Configuration
```python
from core.config import ConfigLoader
config = ConfigLoader.get_instance()
value = config.get("host.your_host")
```

TOML files in `config/` use dot-path keys (e.g., `host.httpbin_host`).

## Naming Conventions
- **Classes**: PascalCase — `HttpbinApi`, `GetFlow`, `TestHttpMethod`
- **Test files**: `test_*.py`
- **Flow classes**: `*Flow` suffix
- **Functions/Methods**: snake_case
- **Constants**: UPPER_SNAKE_CASE

## Important Notes
- Package manager: `uv` (not pip)
- Default app is `httpbin` (set in conftest.py)
- Default env is `test`
- Tests run in parallel (3 workers via pytest-xdist with `--dist=loadscope`)
- Allure results saved to `./output/allure-results`
- Auth is handled automatically based on `APP_NAME` via `auth_manager.py`
- Sensitive data in logs is auto-masked
