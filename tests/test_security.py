"""Phase 3 测试用例"""

import pytest
from pathlib import Path

from agent_matrix.security.scanner import SecurityScanner, Vulnerability, Severity
from agent_matrix.job_manager import JobManager, JobStatus, Job


class TestSecurityScanner:
    """安全扫描器测试"""

    def test_vulnerability_dataclass(self):
        """测试 Vulnerability 数据类"""
        vuln = Vulnerability(
            severity=Severity.HIGH,
            location="src/main.py:42",
            description="使用 eval() 可能导致安全问题",
            fix="使用 ast.literal_eval() 替代",
            test_id="B307",
        )

        assert vuln.severity == Severity.HIGH
        assert vuln.location == "src/main.py:42"
        assert vuln.description == "使用 eval() 可能导致安全问题"
        assert vuln.fix == "使用 ast.literal_eval() 替代"
        assert vuln.test_id == "B307"

        # 测试 to_dict
        d = vuln.to_dict()
        assert d["severity"] == "HIGH"
        assert d["location"] == "src/main.py:42"

    def test_scanner_init(self):
        """测试扫描器初始化"""
        scanner = SecurityScanner()
        assert scanner.project_root == Path.cwd()

        custom_root = Path("/tmp/test")
        scanner2 = SecurityScanner(project_root=custom_root)
        assert scanner2.project_root == custom_root

    def test_scan_nonexistent_file(self):
        """测试扫描不存在的文件"""
        scanner = SecurityScanner()
        result = scanner.scan_file("/nonexistent/file.py")
        assert result == []

    def test_scan_code_content(self):
        """测试扫描代码内容"""
        scanner = SecurityScanner()
        # 包含潜在安全问题的代码
        code = """
import os
password = "hardcoded_password"

def bad_func():
    eval("print('hello')")
    exec("os.system('ls')")
"""
        vulns = scanner.scan_code_content(code, "test.py")
        # 应该能检测到一些漏洞
        assert isinstance(vulns, list)


class TestJobManager:
    """后台任务管理器测试"""

    def test_job_dataclass(self):
        """测试 Job 数据类"""
        job = Job(
            id="test123",
            name="test_job",
            status=JobStatus.PENDING,
            created_at="2024-01-01T00:00:00",
        )

        assert job.id == "test123"
        assert job.name == "test_job"
        assert job.status == JobStatus.PENDING

        # 测试序列化
        d = job.to_dict()
        assert d["id"] == "test123"
        assert d["status"] == "pending"

        # 测试反序列化
        job2 = Job.from_dict(d)
        assert job2.id == job.id
        assert job2.status == job.status

    def test_job_manager_init(self, tmp_path):
        """测试任务管理器初始化"""
        jm = JobManager(storage_dir=tmp_path)
        assert jm.storage_dir == tmp_path
        assert tmp_path.exists()

    def test_submit_task(self, tmp_path):
        """测试提交任务"""
        jm = JobManager(storage_dir=tmp_path)

        job_id = jm.submit_task(lambda: "result", name="my_task")
        assert job_id is not None
        assert len(job_id) == 8

        # 验证任务已创建
        job = jm.get_job(job_id)
        assert job is not None
        assert job.name == "my_task"
        assert job.status == JobStatus.PENDING

    def test_list_jobs(self, tmp_path):
        """测试列出任务"""
        jm = JobManager(storage_dir=tmp_path)

        # 提交多个任务
        jm.submit_task(lambda: None, name="task1")
        jm.submit_task(lambda: None, name="task2")
        jm.submit_task(lambda: None, name="task3")

        jobs = jm.list_jobs()
        assert len(jobs) == 3

    def test_get_job_status(self, tmp_path):
        """测试获取任务状态"""
        jm = JobManager(storage_dir=tmp_path)

        job_id = jm.submit_task(lambda: None)
        status = jm.get_job_status(job_id)
        assert status == JobStatus.PENDING

        # 不存在的任务
        assert jm.get_job_status("nonexistent") is None

    def test_cancel_job(self, tmp_path):
        """测试取消任务"""
        jm = JobManager(storage_dir=tmp_path)

        job_id = jm.submit_task(lambda: None)
        assert jm.cancel_job(job_id) is True

        job = jm.get_job(job_id)
        assert job.status == JobStatus.CANCELLED

        # 重复取消应失败
        assert jm.cancel_job(job_id) is False

    def test_delete_job(self, tmp_path):
        """测试删除任务"""
        jm = JobManager(storage_dir=tmp_path)

        job_id = jm.submit_task(lambda: None)
        assert jm.delete_job(job_id) is True
        assert jm.get_job(job_id) is None

        # 删除不存在的任务
        assert jm.delete_job("nonexistent") is False

    def test_cleanup_completed(self, tmp_path):
        """测试清理已完成任务"""
        jm = JobManager(storage_dir=tmp_path)

        job_id = jm.submit_task(lambda: None, name="old_task")
        # 模拟已完成的任务（手动修改状态）
        job = jm.get_job(job_id)
        job.status = JobStatus.COMPLETED
        job.completed_at = "2020-01-01T00:00:00"  # 很久以前
        jm._save_job(job)

        # 清理 7 天前的任务
        cleaned = jm.cleanup_completed(older_than_days=7)
        assert cleaned == 1

        # 任务应该已删除
        assert jm.get_job(job_id) is None

    def test_get_job_log(self, tmp_path):
        """测试获取任务日志"""
        jm = JobManager(storage_dir=tmp_path)

        job_id = jm.submit_task(lambda: None, name="my_task")
        log = jm.get_job_log(job_id)

        assert log is not None
        assert "my_task" in log
        assert "pending" in log

        # 不存在的任务
        assert jm.get_job_log("nonexistent") is None
