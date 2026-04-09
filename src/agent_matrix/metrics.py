"""Token 统计 - 统一计量 LLM 调用消耗"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TokenStats:
    """Token 消耗统计"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost: float = 0.0

    def merge(self, other: "TokenStats") -> None:
        """合并另一个统计"""
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.total_cost += other.total_cost

    def to_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
            "total_cost": self.total_cost,
        }


class TokenTracker:
    """Token 追踪器

    从 LLM 响应中解析 usage 字段，统一不同 provider 的格式。
    支持的 provider：MiniMax、OpenAI、Claude、OpenRouter 等。
    """

    # 各 provider 的 usage 字段映射
    USAGE_FIELD_MAP = {
        "minimax": "usage",
        "openai": "usage",
        "openrouter": "usage",
        "claude": "usage",
        "deepseek": "usage",
        "siliconflow": "usage",
    }

    # Token 单价（每 1M tokens 的价格，美元）
    # 可根据实际价格调整
    PRICE_PER_MILLION = {
        "minimax": 0.1,      # MiniMax-M2
        "openai": 0.15,      # GPT-4o-mini
        "openrouter": 0.2,   # 估算值
        "claude": 3.0,       # Claude Sonnet
        "deepseek": 0.14,    # DeepSeek Chat
        "siliconflow": 0.1,  # 估算值
    }

    @classmethod
    def parse_response(cls, provider: str, data: dict) -> TokenStats:
        """从 API 响应中解析 token 使用量

        Args:
            provider: 提供商名称
            data: API 响应数据

        Returns:
            TokenStats 实例
        """
        usage = None

        # 获取 usage 字段
        if provider == "claude":
            # Claude: {"usage": {"input_tokens": ..., "output_tokens": ...}}
            usage = data.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
        else:
            # OpenAI 兼容格式: {"usage": {"prompt_tokens": ..., "completion_tokens": ..., "total_tokens": ...}}
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0))
            output_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0))

        # 计算费用
        price = cls.PRICE_PER_MILLION.get(provider, 0.1)
        total_tokens = input_tokens + output_tokens
        total_cost = (total_tokens / 1_000_000) * price

        return TokenStats(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_cost=round(total_cost, 6),
        )

    @classmethod
    def parse_stream_chunk(cls, provider: str, chunk: dict) -> Optional[TokenStats]:
        """从流式响应块中解析 token（如果可用）

        大多数 provider 的流式响应不包含 usage，这里返回 None。
        仅部分 provider 支持流式 token 统计。

        Args:
            provider: 提供商名称
            chunk: 单个流式数据块

        Returns:
            TokenStats 或 None
        """
        # 目前主流 provider 的流式响应都不包含 usage
        return None
