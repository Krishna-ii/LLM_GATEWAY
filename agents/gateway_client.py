"""
gateway_client.py — Reusable LLM Gateway client wrapper
=========================================================
Import this in any agent instead of using OpenAI directly.

Usage:
    from agents.gateway_client import GatewayClient

    client = GatewayClient()
    reply = client.chat("Tell me a joke")
"""

import os
import logging
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class GatewayClient:
    """
    Thin wrapper around the LLM Gateway.
    Handles client creation, model selection, and basic error handling.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "http://localhost:4000")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "virtual-master-key")
        self.default_model = default_model or os.getenv("LLM_MODEL", "gpt-4")

        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        logger.info(f"GatewayClient initialized → {self.base_url} | model={self.default_model}")

    def chat(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: str = "You are a helpful assistant.",
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """Simple single-turn chat. Returns the assistant's reply as a string."""
        response = self._client.chat.completions.create(
            model=model or self.default_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def chat_with_history(
        self,
        messages: list[dict],
        model: Optional[str] = None,
    ) -> tuple[str, list[dict]]:
        """
        Multi-turn chat.
        Returns (reply_text, updated_messages_list).
        """
        response = self._client.chat.completions.create(
            model=model or self.default_model,
            messages=messages,
        )
        reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})
        return reply, messages

    def health_check(self) -> bool:
        """Returns True if the gateway is reachable."""
        import httpx
        try:
            r = httpx.get(f"{self.base_url}/health", timeout=5)
            return r.status_code == 200
        except Exception as e:
            logger.warning(f"Gateway health check failed: {e}")
            return False

    def list_models(self) -> list[str]:
        """Returns list of model names available on the gateway."""
        import httpx
        try:
            r = httpx.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=5
            )
            data = r.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception as e:
            logger.warning(f"Could not fetch models: {e}")
            return []
