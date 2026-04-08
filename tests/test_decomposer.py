"""TaskDecomposer 测试"""

import pytest

from agent_matrix.decomposer import TaskDecomposer


class TestTaskDecomposer:
    """任务分解器测试"""

    def test_decompose_with_coding_task(self):
        """测试包含编码任务的任务分解"""
        decomposer = TaskDecomposer()
        tasks = decomposer._mock_decompose("实现一个用户登录功能")

        assert len(tasks) >= 2
        task_ids = [t.id for t in tasks]

        # 分析任务应该在最前面
        analysis_task = next(t for t in tasks if "analysis" in t.id)
        assert analysis_task.dependencies == []

        # 编码任务应该依赖分析任务
        coding_task = next((t for t in tasks if "coding" in t.id), None)
        if coding_task:
            assert analysis_task.id in coding_task.dependencies

    def test_decompose_with_test_keywords(self):
        """测试包含测试关键词的任务"""
        decomposer = TaskDecomposer()
        tasks = decomposer._mock_decompose("实现并测试用户注册功能")

        assert any("test" in t.id for t in tasks)

    def test_decompose_with_review_keywords(self):
        """测试包含审查关键词的任务"""
        decomposer = TaskDecomposer()
        tasks = decomposer._mock_decompose("开发并审查订单模块")

        assert any("review" in t.id for t in tasks)

    def test_decompose_returns_valid_tasks(self):
        """测试分解结果都是有效的 Task 对象"""
        decomposer = TaskDecomposer()
        tasks = decomposer._mock_decompose("实现简单功能")

        for task in tasks:
            assert task.id
            assert task.description
            assert isinstance(task.dependencies, list)
