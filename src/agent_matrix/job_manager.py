"""后台任务管理器"""

from __future__ import annotations
import asyncio
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import traceback


class JobStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """任务数据类"""
    id: str
    name: str
    status: JobStatus
    created_at: str  # ISO 格式时间
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        return cls(
            id=data["id"],
            name=data["name"],
            status=JobStatus(data["status"]),
            created_at=data["created_at"],
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            result=data.get("result"),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )


class JobManager:
    """后台任务管理器"""

    def __init__(self, storage_dir: Optional[Path] = None):
        """初始化任务管理器

        Args:
            storage_dir: 任务存储目录，默认 ~/.agent-matrix/jobs/
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".agent-matrix" / "jobs"

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._jobs: Dict[str, Job] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}

        # 加载已有任务
        self._load_jobs()

    def _job_file(self, job_id: str) -> Path:
        """获取任务文件路径"""
        return self.storage_dir / f"{job_id}.json"

    def _load_jobs(self) -> None:
        """加载所有任务"""
        self._jobs.clear()
        for job_file in self.storage_dir.glob("*.json"):
            try:
                data = json.loads(job_file.read_text(encoding="utf-8"))
                job = Job.from_dict(data)
                self._jobs[job.id] = job
            except Exception:
                pass  # 跳过损坏的任务文件

    def _save_job(self, job: Job) -> None:
        """保存任务到磁盘"""
        job_file = self._job_file(job.id)
        job_file.write_text(json.dumps(job.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def submit_task(
        self,
        task_fn: Callable,
        *args,
        name: Optional[str] = None,
        **kwargs,
    ) -> str:
        """提交任务（同步接口，用于 CLI）

        Args:
            task_fn: 任务函数
            *args: 位置参数
            name: 任务名称
            **kwargs: 关键字参数

        Returns:
            job_id
        """
        job_id = str(uuid.uuid4())[:8]
        job_name = name or f"task_{job_id}"

        # 创建任务记录
        job = Job(
            id=job_id,
            name=job_name,
            status=JobStatus.PENDING,
            created_at=datetime.now().isoformat(),
            metadata={"args": str(args), "kwargs": str(kwargs)},
        )
        self._jobs[job_id] = job
        self._save_job(job)

        return job_id

    def submit_async_task(
        self,
        coro: asyncio.coroutines,
        name: Optional[str] = None,
    ) -> str:
        """提交异步任务

        Args:
            coro: 协程对象
            name: 任务名称

        Returns:
            job_id
        """
        job_id = str(uuid.uuid4())[:8]
        job_name = name or f"task_{job_id}"

        # 创建任务记录
        job = Job(
            id=job_id,
            name=job_name,
            status=JobStatus.PENDING,
            created_at=datetime.now().isoformat(),
        )
        self._jobs[job_id] = job
        self._save_job(job)

        # 创建并启动异步任务
        async def run_task():
            job = self._jobs[job_id]
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now().isoformat()
            self._save_job(job)

            try:
                result = await coro
                job.status = JobStatus.COMPLETED
                job.result = str(result)[:10000]  # 限制结果长度
                job.completed_at = datetime.now().isoformat()
            except Exception as e:
                job.status = JobStatus.FAILED
                job.error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                job.completed_at = datetime.now().isoformat()
            finally:
                self._save_job(job)
                self._running_tasks.pop(job_id, None)

        task = asyncio.create_task(run_task())
        self._running_tasks[job_id] = task

        # 更新状态为 RUNNING
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now().isoformat()
        self._save_job(job)

        return job_id

    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """获取任务状态

        Args:
            job_id: 任务 ID

        Returns:
            任务状态，如果不存在返回 None
        """
        job = self._jobs.get(job_id)
        return job.status if job else None

    def get_job(self, job_id: str) -> Optional[Job]:
        """获取任务详情

        Args:
            job_id: 任务 ID

        Returns:
            任务对象，如果不存在返回 None
        """
        # 重新加载以获取最新状态
        job_file = self._job_file(job_id)
        if job_file.exists():
            try:
                data = json.loads(job_file.read_text(encoding="utf-8"))
                job = Job.from_dict(data)
                self._jobs[job_id] = job
            except Exception:
                pass

        return self._jobs.get(job_id)

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 50,
    ) -> List[Job]:
        """列出任务

        Args:
            status: 按状态过滤
            limit: 返回数量限制

        Returns:
            任务列表
        """
        jobs = list(self._jobs.values())

        # 按创建时间倒序
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        # 按状态过滤
        if status:
            jobs = [j for j in jobs if j.status == status]

        return jobs[:limit]

    def cancel_job(self, job_id: str) -> bool:
        """取消任务

        Args:
            job_id: 任务 ID

        Returns:
            是否成功取消
        """
        job = self._jobs.get(job_id)
        if not job:
            return False

        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            return False

        # 取消运行中的任务
        if job_id in self._running_tasks:
            self._running_tasks[job_id].cancel()
            self._running_tasks.pop(job_id, None)

        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.now().isoformat()
        self._save_job(job)

        return True

    def get_job_log(self, job_id: str) -> Optional[str]:
        """获取任务日志

        Args:
            job_id: 任务 ID

        Returns:
            日志内容
        """
        job = self.get_job(job_id)
        if not job:
            return None

        # 构建日志信息
        lines = [
            f"Job ID: {job.id}",
            f"Name: {job.name}",
            f"Status: {job.status.value}",
            f"Created: {job.created_at}",
        ]

        if job.started_at:
            lines.append(f"Started: {job.started_at}")

        if job.completed_at:
            lines.append(f"Completed: {job.completed_at}")

        if job.result:
            lines.append(f"\n--- Result ---")
            lines.append(job.result)

        if job.error:
            lines.append(f"\n--- Error ---")
            lines.append(job.error)

        return "\n".join(lines)

    def delete_job(self, job_id: str) -> bool:
        """删除任务

        Args:
            job_id: 任务 ID

        Returns:
            是否成功删除
        """
        if job_id not in self._jobs:
            return False

        # 取消运行中的任务
        if job_id in self._running_tasks:
            self._running_tasks[job_id].cancel()
            self._running_tasks.pop(job_id, None)

        # 删除文件
        job_file = self._job_file(job_id)
        if job_file.exists():
            job_file.unlink()

        # 删除内存中的记录
        self._jobs.pop(job_id, None)

        return True

    def cleanup_completed(self, older_than_days: int = 7) -> int:
        """清理已完成的任务

        Args:
            older_than_days: 清理多少天前的任务

        Returns:
            清理的任务数量
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=older_than_days)
        cleaned = 0

        for job in list(self._jobs.values()):
            if job.status not in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                continue

            if job.completed_at:
                completed_time = datetime.fromisoformat(job.completed_at)
                if completed_time < cutoff:
                    self.delete_job(job.id)
                    cleaned += 1

        return cleaned


# 全局任务管理器实例
_global_manager: Optional[JobManager] = None


def get_job_manager() -> JobManager:
    """获取全局任务管理器实例"""
    global _global_manager
    if _global_manager is None:
        _global_manager = JobManager()
    return _global_manager
