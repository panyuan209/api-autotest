"""
测试触发服务

通过异步子进程调用 run_test.py，
追踪每次触发的任务状态与日志输出。
"""

import asyncio
import os
import sys
import uuid
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from web_app.models.responses import TestJobStatus

# 保留最近 200 个任务，避免内存无限增长
_MAX_JOBS = 200

# 单个任务保留的最大日志行数
_MAX_LOG_LINES = 5000

# 项目根目录（web_app 的上一级）
_PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
_RUNNER_SCRIPT = _PROJECT_ROOT / "run_test.py"


class TestRunnerService:
    """异步测试触发服务（单例）"""

    def __init__(self):
        # 使用有序字典，方便按插入顺序获取最新任务
        self._jobs: OrderedDict[str, TestJobStatus] = OrderedDict()
        self._jobs_lock = asyncio.Lock()
        # 同一时刻只能有一个测试任务运行
        self._run_semaphore = asyncio.Semaphore(1)

    # ──────────────── 公开接口 ────────────────

    def running_job(self) -> Optional[TestJobStatus]:
        """返回当前正在运行的任务（若有）。"""
        for job in self._jobs.values():
            if job.status in ("pending", "running"):
                return job
        return None

    async def submit(
        self,
        env: str,
        app: str,
        mark: Optional[str] = None,
        send_notification: bool = True,
    ) -> str:
        """提交测试任务，立即返回 job_id。"""
        job_id = uuid.uuid4().hex
        job = TestJobStatus(
            job_id=job_id,
            status="pending",
            env=env,
            app=app,
            mark=mark,
            send_notification=send_notification,
            created_at=datetime.now(),
        )

        async with self._jobs_lock:
            self._jobs[job_id] = job
            self._evict_old_jobs()

        # 在后台运行，不阻塞当前请求
        asyncio.create_task(self._run_job(job_id))
        return job_id

    def get_job(self, job_id: str) -> Optional[TestJobStatus]:
        """按 job_id 查询任务详情。"""
        return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 50) -> List[TestJobStatus]:
        """返回最近 limit 个任务（最新在前）。"""
        jobs = list(self._jobs.values())
        return list(reversed(jobs))[:limit]

    # ──────────────── 内部实现 ────────────────

    async def _run_job(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if job is None:
            return

        # 等待上一个任务完成（避免资源竞争）
        async with self._run_semaphore:
            await self._execute_job(job)

    async def _execute_job(self, job: TestJobStatus) -> None:
        """实际执行测试脚本。"""
        # 构建命令行参数
        cmd = self._build_command(job)

        # 更新状态为运行中
        job.status = "running"
        job.started_at = datetime.now()

        log_lines: list[str] = []

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(_PROJECT_ROOT),
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )

            # 逐行读取输出
            assert proc.stdout is not None
            async for raw_line in proc.stdout:
                line = raw_line.decode("utf-8", errors="replace").rstrip()
                log_lines.append(line)
                # 超出上限时丢弃最早的行
                if len(log_lines) > _MAX_LOG_LINES:
                    log_lines = log_lines[-_MAX_LOG_LINES:]
                # 实时写回 job（直接赋值，Python GIL 保证原子性）
                job.output = "\n".join(log_lines)

            exit_code = await proc.wait()
            job.exit_code = exit_code
            job.status = "success" if exit_code == 0 else "failed"

        except Exception as exc:
            log_lines.append(f"[runner] 内部错误: {exc}")
            job.output = "\n".join(log_lines)
            job.status = "failed"
            job.exit_code = -1
        finally:
            job.finished_at = datetime.now()

    def _build_command(self, job: TestJobStatus) -> list[str]:
        cmd: list[str] = [
            sys.executable,
            str(_RUNNER_SCRIPT),
            "--env",
            job.env,
            "--app",
            job.app,
        ]
        if job.mark:
            cmd += ["--mark", job.mark]
        return cmd

    def _evict_old_jobs(self) -> None:
        """超出上限时删除最旧的任务。"""
        while len(self._jobs) > _MAX_JOBS:
            self._jobs.popitem(last=False)


# 全局单例
test_runner_service = TestRunnerService()
