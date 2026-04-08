"""Agent 池 - 管理所有可用的 Agent 实例"""

from typing import Dict, List, Optional

from .agents.base import Agent


class AgentPool:
    """Agent 池

    管理不同角色的 Agent 实例，提供 Agent 发现和获取功能。
    使用注册表模式，便于扩展新的 Agent 类型。
    """

    def __init__(self):
        self._agents: Dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        """注册 Agent

        Args:
            agent: Agent 实例
        """
        self._agents[agent.role] = agent

    def get(self, role: str) -> Optional[Agent]:
        """根据角色获取 Agent

        Args:
            role: Agent 角色标识

        Returns:
            Agent 实例，若不存在返回 None
        """
        return self._agents.get(role)

    def get_by_description(self, description: str) -> Optional[Agent]:
        """根据描述匹配最合适的 Agent

        当前实现：简单子串匹配。
        TODO: 第二阶段使用 LLM 做语义匹配。

        Args:
            description: 任务描述

        Returns:
            最匹配的 Agent 实例
        """
        best_match = None
        best_score = 0

        for agent in self._agents.values():
            # 简单的关键词匹配评分
            score = self._calculate_match_score(agent, description)
            if score > best_score:
                best_score = score
                best_match = agent

        return best_match or self._agents.get("coder")  # 默认 fallback 到 coder

    def list_agents(self) -> List[str]:
        """列出所有已注册的 Agent 角色"""
        return list(self._agents.keys())

    def _calculate_match_score(self, agent: Agent, task_desc: str) -> int:
        """计算匹配分数（使用子串匹配）"""
        score = 0
        task_lower = task_desc.lower()

        # 关键角色词表（特定角色词权重更高）
        role_keywords = {
            "coder": ["代码", "实现", "开发", "写", "code", "implement", "编写"],
            "reviewer": ["审查", "review", "检查", "评审"],
            "tester": ["测试", "test", "验证"],
        }

        agent_role = agent.role
        if agent_role in role_keywords:
            for kw in role_keywords[agent_role]:
                if kw in task_lower:
                    # 特定角色词权重更高（审查/评审/测试等）
                    if agent_role == "reviewer" and kw in ["审查", "评审", "检查"]:
                        score += 25
                    elif agent_role == "tester" and kw in ["测试", "验证"]:
                        score += 25
                    else:
                        score += 10

        return score

    def _find_best_role(self, description: str) -> Optional[str]:
        """从描述中识别角色"""
        desc_lower = description.lower()
        if "coder" in desc_lower or "code" in desc_lower:
            return "coder"
        if "reviewer" in desc_lower or "review" in desc_lower:
            return "reviewer"
        if "tester" in desc_lower or "test" in desc_lower:
            return "tester"
        return None
