"""MiniMax API 适配器

封装 MiniMax API 调用，用于任务分解等场景。
"""
import json
import os
from typing import AsyncIterator, Optional

import httpx


class MiniMaxAdapter:
    """MiniMax API 适配器"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.minimax.chat",
        model: str = "MiniMax-M2",
    ):
        self._api_key = api_key or os.getenv("MINIMAX_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._model = model

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def complete(self, prompt: str, **kwargs) -> str:
        """调用补全接口（非流式）"""
        if not self.is_configured:
            raise ValueError("MiniMax API key not configured")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.7),
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._base_url}/v1/text/chatcompletion_v2",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def complete_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """流式调用补全接口"""
        if not self.is_configured:
            raise ValueError("MiniMax API key not configured")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.7),
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/v1/text/chatcompletion_v2",
                headers=headers,
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        if line.strip() == "data: [DONE]":
                            break
                        try:
                            chunk = json.loads(line[6:])
                            delta = chunk.get("choices", [{}])[0].get("delta", "")
                            if delta:
                                yield delta
                        except json.JSONDecodeError:
                            continue
