import os

import shutil
import uuid

import allure
import pytest

from core.enums import App, Env, ProjectPath
from core.initializer import Initializer
from core.logger import api_logger as logger

import subprocess


def pytest_load_initial_conftests(early_config, parser, args):
    """在 xdist 处理命令行参数之前动态设置分布式执行模式"""
    pass


def pytest_configure(config):
    config.addinivalue_line("markers", "p0: p0 用例")
    config.addinivalue_line("markers", "p1: p1 用例")
    config.addinivalue_line("markers", "p2: p2 用例")
    config.addinivalue_line("markers", "case_id(android_id, ios_id): 平台特定的用例ID")

    # 根据 --app 参数自动设置测试目录
    app_option = config.getoption("--app", default=None)
    if app_option:
        app_test_dir = f"tests/{app_option}"
        if os.path.exists(app_test_dir):
            # 若命令行没有指定具体的测试路径，则使用 app 对应的测试目录
            if not any(arg.startswith("tests/") for arg in config.args):
                config.args = [app_test_dir] + config.args
                logger.info(f"测试目录: {app_test_dir}")
        else:
            logger.warning(f"指定的应用测试目录不存在: {app_test_dir}")


def pytest_addoption(parser):
    parser.addoption("--env", action="store", default=Env.TEST.value, help="测试环境")
    # parser.addoption("--env", action="store", default=Env.PROD.value, help="测试环境")
    parser.addoption(
        "--app", action="store", default=App.HTTPBIN.value, help="测试应用"
    )


@pytest.fixture(scope="session", autouse=True)
def init_framework_for_worker(request):
    """为每个 pytest-xdist worker 进程初始化框架实例"""
    env_value = request.config.getoption("--env")
    app_value = request.config.getoption("--app")

    env = Env(env_value)
    app = App(app_value)

    # 初始化框架实例
    ctx = Initializer(
        env=env,
        app=app,
    )

    yield ctx

    ctx.cleanup()


def pytest_unconfigure(config):
    """在测试结束后生成报告"""

    worker_id = getattr(config, "workerinput", {}).get("workerid", "master")
    if worker_id != "master":  # 只在主进程中生成报告和合并日志
        return

    # 合并worker进程的日志文件
    try:
        from utils.utils import merge_worker_logs

        merge_worker_logs()
    except Exception as e:
        logger.error(f"合并worker日志失败: {e}")

    # 生成 allure 报告
    allure_result_dir = ProjectPath.ALLURE_RESULT_PATH.value
    allure_report_dir = ProjectPath.ALLURE_REPORT_PATH.value

    history_dir_source = os.path.join(allure_report_dir, "history")
    history_dir_target = os.path.join(allure_result_dir, "history")

    # 确保目录存在
    if not os.path.exists(allure_result_dir):
        os.makedirs(allure_result_dir)
    if not os.path.exists(allure_report_dir):
        os.makedirs(allure_report_dir)

    if os.path.exists(history_dir_source):
        if os.path.exists(history_dir_target):
            shutil.rmtree(history_dir_target)
            shutil.copytree(history_dir_source, history_dir_target)

    # 生成 allure 报告
    cmd = f'allure generate "{allure_result_dir}" -o "{allure_report_dir}" --clean'
    subprocess.run(cmd, shell=True, check=True)


@pytest.fixture(autouse=True)
def bind_case_info(request):
    """绑定用例ID和用例名称"""

    case_name = request.node.name
    # 生成8位的短ID
    case_id = f"case_{uuid.uuid4().hex[:8]}"
    logger.set_case_info(case_name, case_id)

    # 在 Tags 中显示用例ID
    allure.dynamic.tag(f"用例ID: {case_id}")

    yield

    logger.clear_case_info()


def pytest_runtest_teardown(item, nextitem):
    """在每个测试用例执行完成后添加日志附件"""
    case_id = logger._case_id.get()
    if case_id and case_id != "N/A":
        try:
            from utils.utils import extract_case_logs_by_blocks

            case_logs = extract_case_logs_by_blocks(case_id)
            if case_logs:
                allure.attach(
                    case_logs,
                    name="测试执行日志",
                    attachment_type=allure.attachment_type.TEXT,
                )
        except Exception as e:
            logger.warning(f"收集用例日志失败: {e}")
