import pytest
import click


@click.command()
@click.option("-m", "--mark", help="运行指定标签的测试用例", default=None)
@click.option(
    "-e",
    "--env",
    type=click.Choice(["test", "dev", "prod"]),
    default="test",
    help="指定测试运行环境",
)
@click.option(
    "--app",
    type=click.Choice(["httpbin"]),
    default="httpbin",
    help="指定测试应用",
)
def run(mark, env, app):
    """测试用例执行脚本"""
    # 设置 pytest 运行参数
    pytest_args = []
    # 设置 pytest 运行环境
    if env:
        pytest_args.extend(["--env", env])
    if app:
        pytest_args.extend(["--app", app])
    if mark:
        pytest_args.extend(["-m", mark])

    # 运行测试
    exit_code = pytest.main(pytest_args)

    # 退出并返回pytest的退出码
    exit(exit_code)


if __name__ == "__main__":
    run()
