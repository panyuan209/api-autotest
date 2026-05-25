# AGENTS.md - API Autotest Framework

## Build/Lint/Test Commands

### Environment Setup
```bash
uv sync  # Python 3.13+ required
```

### Running Tests
```bash
pytest                                    # All tests (default: httpbin, test env)
python run_test.py                        # Wrapper script
python run_test.py --app httpbin          # Specific app
python run_test.py --env dev --app httpbin # With env selection
python run_test.py --mark p0              # By marker (p0/p1/p2)
```

### Running Single Tests
```bash
pytest tests/httpbin/test_http_method.py                                          # File
pytest tests/httpbin/test_http_method.py::TestHttpMethod                          # Class
pytest tests/httpbin/test_http_method.py::TestHttpMethod::test_get                # Method
pytest -k "test_get"                                                              # By name
```

### Default Pytest Options (`pyproject.toml`)
`-vs --alluredir=./output/allure-results -n 3 --dist=loadscope --capture=no --timeout=300 --tb=short`

### Allure Reports
```bash
allure serve ./output/allure-results
```

## Architecture

Four-layer separation:
- **tests/** — Pytest cases organized by app (e.g., httpbin)
- **business/** — Flow-based logic: `apis/` (API wrappers), `flow/` (business flows), `data/` (test data)
- **core/** — Framework core: `api.py`, `flow.py`, `config.py`, `logger.py`, `auth_manager.py`, `exceptions.py`
- **utils/** — Shared utilities: decorators, auth strategies

## Code Style

### Imports Order
```python
# 1. Standard library
import os, json, time
from typing import Optional, Dict, Any

# 2. Third-party
import pytest, allure
from pydantic import BaseModel

# 3. Core framework
from core.api import Api, ClientSession
from core.flow import Flow

# 4. Business modules
from business.httpbin.apis.api import HttpbinApi

# 5. Utilities
from utils.decorator import json
```

### Type Hints
Always annotate function signatures:
```python
def setup(self, client_session: Optional[ClientSession] = None, **kwargs) -> None:
def get_params(self, key: str, default: Any = None) -> Any:
```

### Naming Conventions
- **Classes**: PascalCase — `HttpbinApi`, `GetFlow`, `TestHttpMethod`
- **Functions/Methods**: snake_case — `get_params`, `do_request`
- **Constants**: UPPER_SNAKE_CASE — `HOST_KEY`, `APP_NAME`
- **Test files**: `test_*.py` | **Test classes**: `Test*` prefix | **Flow classes**: `*Flow` suffix

### Test Structure
```python
import allure, pytest
from business.httpbin.flow.get_flow import GetFlow
from tests.httpbin.httpbin_test import HttpbinTest

class TestFeature(HttpbinTest):
    @pytest.mark.p0
    @allure.feature("Feature Name")
    @allure.title("Test case title")
    def test_something(self):
        with allure.step("Step description"):
            result = GetFlow(params={"key": "value"}).run()
            assert result.extract("json.key") == "value"
```

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

### Flow Pattern
```python
from core.flow import Flow

class ExampleFlow(Flow):
    @classmethod
    def desc(cls): return "Flow description"
    @classmethod
    def name(cls): return "Flow Name"
    @classmethod
    def schema(cls):
        return cls.create_schema({"param": {"type": str, "description": "desc", "required": True}})

    def setup(self, client_session=None, **kwargs):
        self.api = YourApi(client_session)

    def _run(self):
        return self.api.some_method(json={"data": self.get_params("param")})
```

### Decorators
- `@json` — Parse response as JSON, wraps in `JsonResult`; use `.extract("jmespath")` for data extraction

### Error Handling
```python
from core.exceptions import ApiRequestError, FlowExecutionError, ValidationError

raise ApiRequestError("msg", status_code=400, response_body="...")
raise FlowExecutionError("Flow execution failed")
raise ValidationError("Parameter validation failed")
```

### Logging
```python
from core.logger import api_logger as logger

logger.info("Message")
logger.labeled("Label", value, icon="📊")
logger.json_log(data, "Description")
logger.timing("Operation", duration)
```

### Configuration
```python
from core.config import ConfigLoader
config = ConfigLoader.get_instance()
value = config.get("host.your_host")
```

## Important Notes
- Package manager: `uv` (not pip)
- Tests run in parallel by default (3 workers via pytest-xdist)
- Allure generates test reports automatically in `output/allure-results`
- Sensitive data in logs is auto-masked
- Auth is handled automatically based on `APP_NAME` via `auth_manager.py`
- Environment configs in `config/{test,dev,prod}.toml`
