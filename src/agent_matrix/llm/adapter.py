"""通用 LLM 适配器

支持多种模型提供商，自动适配不同的 API 格式。
"""
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, AsyncIterator, Tuple

import httpx

from ..metrics import TokenStats, TokenTracker


# 各提供商的默认配置
PROVIDER_DEFAULTS: Dict[str, Dict[str, str]] = {
    "minimax": {
        "base_url": "https://api.minimaxi.com/v1",
        "model": "MiniMax-M2",
        "env_key": "MINIMAX_API_KEY",
        "endpoint": "/chat/completions",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
        "endpoint": "/chat/completions",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "anthropic/claude-3-haiku",
        "env_key": "OPENROUTER_API_KEY",
        "endpoint": "/chat/completions",
    },
    "claude": {
        "base_url": "https://api.anthropic.com/v1",
        "model": "claude-sonnet-4-20250514",
        "env_key": "ANTHROPIC_API_KEY",
        "endpoint": "/messages",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
        "endpoint": "/chat/completions",
    },
    "siliconflow": {
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "env_key": "SILICONFLOW_API_KEY",
        "endpoint": "/chat/completions",
    },
}


def create_adapter(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> "LLMAdapter":
    """工厂函数：创建 LLM 适配器

    Args:
        provider: 提供商名称 (minimax/openai/openrouter/claude/deepseek/siliconflow)
        api_key: API 密钥（默认从环境变量读取）
        base_url: 自定义 API 地址（覆盖默认）
        model: 模型名称（覆盖默认）
    """
    if provider is None:
        provider = "minimax"

    # 解析 provider，可能是 "provider/model" 格式
    actual_provider = provider
    if "/" in provider:
        parts = provider.split("/", 1)
        actual_provider = parts[0]
        if model is None:
            model = provider  # 用完整的 provider/model 作为模型名

    if actual_provider not in PROVIDER_DEFAULTS:
        raise ValueError(f"不支持的 provider: {provider}，可选: {list(PROVIDER_DEFAULTS.keys())}")

    config = PROVIDER_DEFAULTS[actual_provider]

    # 确定 api_key
    actual_key = api_key or os.getenv(config["env_key"], "")

    # 确定 base_url
    actual_url = base_url or config["base_url"]

    # 确定 model
    actual_model = model or config["model"]

    return LLMAdapter(
        provider=actual_provider,
        api_key=actual_key,
        base_url=actual_url,
        model=actual_model,
        endpoint=config["endpoint"],
    )


@dataclass
class UsageInfo:
    """LLM 使用量信息"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost: float = 0.0

    def to_token_stats(self) -> TokenStats:
        return TokenStats(
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            total_cost=self.total_cost,
        )


class LLMAdapter:
    """通用 LLM 适配器

    支持多种提供商，统一 OpenAI 格式输出。
    """

    def __init__(
        self,
        provider: str,
        api_key: str,
        base_url: str,
        model: str,
        endpoint: str = "/chat/completions",
    ):
        self._provider = provider
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._endpoint = endpoint
        self._last_usage: Optional[UsageInfo] = None

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model(self) -> str:
        return self._model

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def get_usage(self) -> Optional[UsageInfo]:
        """获取最近一次调用的 usage 信息"""
        return self._last_usage

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {"Content-Type": "application/json"}

        if self._provider == "claude":
            headers["x-api-key"] = self._api_key
            headers["anthropic-version"] = "2023-06-01"
            headers["anthropic-dangerous-direct-browser-access"] = "true"
        else:
            headers["Authorization"] = f"Bearer {self._api_key}"

        return headers

    def _build_payload(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """构建请求体"""
        temperature = kwargs.get("temperature", 0.7)

        if self._provider == "claude":
            # Claude API 格式
            last_msg = messages[-1] if messages else {"role": "user", "content": ""}
            return {
                "model": self._model,
                "messages": messages[:-1] if len(messages) > 1 else [],
                "max_tokens": kwargs.get("max_tokens", 4096),
                "temperature": temperature,
                "system": messages[0]["content"] if messages and messages[0]["role"] == "system" else None,
                "stream": kwargs.get("stream", False),
            }
        else:
            # OpenAI 兼容格式
            return {
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
                "stream": kwargs.get("stream", False),
            }

    def _parse_response(self, data: dict) -> Tuple[str, UsageInfo]:
        """解析 API 响应，提取文本和 usage

        Returns:
            (response_text, usage_info)
        """
        if self._provider == "claude":
            text = data["content"][0]["text"]
            usage_data = data.get("usage", {})
            self._last_usage = UsageInfo(
                input_tokens=usage_data.get("input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0),
            )
        else:
            text = data["choices"][0]["message"]["content"]
            usage_data = data.get("usage", {})
            self._last_usage = UsageInfo(
                input_tokens=usage_data.get("prompt_tokens", usage_data.get("input_tokens", 0)),
                output_tokens=usage_data.get("completion_tokens", usage_data.get("output_tokens", 0)),
            )

        # 计算费用
        price = TokenTracker.PRICE_PER_MILLION.get(self._provider, 0.1)
        total_tokens = self._last_usage.input_tokens + self._last_usage.output_tokens
        self._last_usage.total_cost = round((total_tokens / 1_000_000) * price, 6)

        return text, self._last_usage

    async def complete(
        self,
        prompt: str = "",
        messages: Optional[List[Dict[str, Any]]] = None,
        image_urls: Optional[List[str]] = None,
        **kwargs
    ) -> Tuple[str, UsageInfo]:
        """调用补全接口（非流式）

        Args:
            prompt: 简单提示词（与 messages 二选一）
            messages: 消息列表（支持多模态格式）
            image_urls: 图片URL列表（会自动转换为多模态消息格式）
            **kwargs: 其他参数如 system_prompt, temperature 等

        Returns:
            (response_text, usage_info)
        """
        if not self.is_configured:
            raise ValueError(f"LLM API key not configured for {self._provider}")

        # 构建消息
        if messages is None:
            messages = [{"role": "user", "content": prompt}]
        elif image_urls:
            # 将 image_urls 合并到最后一条用户消息
            last_msg = messages[-1] if messages else {"role": "user", "content": ""}
            if isinstance(last_msg["content"], str):
                last_msg["content"] = [{"type": "text", "text": last_msg["content"]}]
            for url in image_urls:
                last_msg["content"].append({"type": "image_url", "image_url": {"url": url}})

        if kwargs.get("system_prompt"):
            messages.insert(0, {"role": "system", "content": kwargs["system_prompt"]})

        headers = self._build_headers()
        payload = self._build_payload(messages, **kwargs)

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self._base_url}{self._endpoint}",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        return self._parse_response(data)

    async def complete_stream(
        self,
        prompt: str = "",
        messages: Optional[List[Dict[str, Any]]] = None,
        image_urls: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式调用补全接口

        Yields:
            逐个 token 输出
        """
        if not self.is_configured:
            raise ValueError(f"LLM API key not configured for {self._provider}")

        # 构建消息
        if messages is None:
            messages = [{"role": "user", "content": prompt}]
        elif image_urls:
            last_msg = messages[-1] if messages else {"role": "user", "content": ""}
            if isinstance(last_msg["content"], str):
                last_msg["content"] = [{"type": "text", "text": last_msg["content"]}]
            for url in image_urls:
                last_msg["content"].append({"type": "image_url", "image_url": {"url": url}})

        if kwargs.get("system_prompt"):
            messages.insert(0, {"role": "system", "content": kwargs["system_prompt"]})

        headers = self._build_headers()
        payload = self._build_payload(messages, stream=True, **kwargs)

        full_response = []
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}{self._endpoint}",
                headers=headers,
                json=payload,
            ) as resp:
                resp.raise_for_status()

                if self._provider == "claude":
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            if line.strip() == "data: [DONE]":
                                break
                            try:
                                chunk = json.loads(line[6:])
                                if chunk.get("type") == "content_block_delta":
                                    delta = chunk.get("delta", {}).get("text", "")
                                    if delta:
                                        full_response.append(delta)
                                        yield delta
                            except json.JSONDecodeError:
                                continue
                else:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            if line.strip() == "data: [DONE]":
                                break
                            try:
                                chunk = json.loads(line[6:])
                                delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if delta:
                                    full_response.append(delta)
                                    yield delta
                            except json.JSONDecodeError:
                                continue

        # 流式响应结束后，尝试从最终请求获取 usage（如果 API 支持）
        # 注意：大多数流式 API 不返回 usage，这里做降级处理
        if self._last_usage is None:
            self._last_usage = UsageInfo()
