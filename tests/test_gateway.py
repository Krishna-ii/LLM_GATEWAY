"""
Integration Tests — LLM Gateway Track 2
=========================================
Run with: pytest tests/ -v

Tests verify:
1. No API keys in agent source code
2. Environment variables used correctly
3. Gateway reachability
4. Agent LLM calls work
5. Provider switching works
6. Multi-turn conversation works
7. Tracing headers are forwarded
"""

import os
import sys
import inspect
import pytest
import httpx

# Ensure agents package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import agents.demo_agent as demo_agent_module
from agents.demo_agent import run_agent, run_multi_turn_agent
from agents.gateway_client import GatewayClient

GATEWAY_URL = os.getenv("LLM_BASE_URL", "http://localhost:4000")
GATEWAY_KEY = os.getenv("LLM_API_KEY", "virtual-master-key")


# ─── Security Tests ────────────────────────────────────────────────────────────

class TestSecurity:

    def test_no_hardcoded_openai_key_in_demo_agent(self):
        """Agent source must not contain hardcoded OpenAI API keys."""
        source = inspect.getsource(demo_agent_module)
        assert "sk-" not in source, \
            "FAIL: Hardcoded API key found in demo_agent.py! Remove it immediately."

    def test_no_hardcoded_anthropic_key_in_demo_agent(self):
        """Agent source must not contain hardcoded Anthropic API keys."""
        source = inspect.getsource(demo_agent_module)
        assert "sk-ant-" not in source, \
            "FAIL: Hardcoded Anthropic API key found in demo_agent.py!"

    def test_agent_reads_base_url_from_env(self):
        """Agent must use env var for gateway URL, not hardcode openai.com."""
        source = inspect.getsource(demo_agent_module)
        assert "api.openai.com" not in source, \
            "FAIL: Direct OpenAI URL found. Use LLM_BASE_URL env var instead."
        assert "LLM_BASE_URL" in source, \
            "FAIL: Agent must read LLM_BASE_URL from environment."

    def test_agent_reads_api_key_from_env(self):
        """Agent must read LLM_API_KEY from environment."""
        source = inspect.getsource(demo_agent_module)
        assert "LLM_API_KEY" in source, \
            "FAIL: Agent must read LLM_API_KEY from environment."

    def test_env_example_has_no_real_keys(self):
        """The .env.example file must not contain real API keys."""
        env_example_path = os.path.join(os.path.dirname(__file__), "..", ".env.example")
        if os.path.exists(env_example_path):
            with open(env_example_path) as f:
                content = f.read()
            assert "sk-proj-" not in content, "Real OpenAI key found in .env.example!"
            assert "sk-ant-api03-" not in content, "Real Anthropic key found in .env.example!"


# ─── Gateway Connectivity Tests ────────────────────────────────────────────────

class TestGatewayConnectivity:

    @pytest.mark.skipif(
        "CI" not in os.environ and not os.getenv("OPENAI_API_KEY"),
        reason="Skipping live gateway test — no API key configured"
    )
    def test_gateway_health(self):
        """Gateway /health endpoint must return 200."""
        try:
            r = httpx.get(f"{GATEWAY_URL}/health", timeout=10)
            assert r.status_code == 200, f"Gateway health check failed: {r.status_code}"
        except httpx.ConnectError:
            pytest.skip("Gateway not running — start with: docker-compose up llm-gateway")

    def test_gateway_client_initialization(self):
        """GatewayClient must initialize without raising errors."""
        client = GatewayClient(
            base_url="http://localhost:4000",
            api_key="virtual-master-key",
            default_model="gpt-4"
        )
        assert client.base_url == "http://localhost:4000"
        assert client.default_model == "gpt-4"
        # Key must NOT be a real key
        assert not client.api_key.startswith("sk-proj-")

    def test_gateway_url_is_not_openai_direct(self):
        """LLM_BASE_URL must not point directly to OpenAI."""
        base_url = os.getenv("LLM_BASE_URL", "http://localhost:4000")
        assert "api.openai.com" not in base_url, \
            "LLM_BASE_URL is pointing directly to OpenAI! It must point to the gateway."


# ─── Live LLM Call Tests (require running gateway) ────────────────────────────

class TestLiveLLMCalls:
    """
    These tests require a running gateway + valid API keys.
    They are skipped automatically in environments without API keys.
    """

    @pytest.fixture(autouse=True)
    def skip_without_gateway(self):
        if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("No API keys configured — skipping live tests")
        try:
            httpx.get(f"{GATEWAY_URL}/health", timeout=5)
        except httpx.ConnectError:
            pytest.skip("Gateway not running")

    def test_basic_agent_call_returns_response(self):
        """Agent must return a non-empty response."""
        result = run_agent("What is 1 + 1? Answer with just the number.")
        assert result is not None
        assert isinstance(result, dict)
        assert "response" in result
        assert len(result["response"]) > 0

    def test_agent_response_contains_usage(self):
        """Response must include token usage info."""
        result = run_agent("Say 'hello'")
        assert "usage" in result
        assert result["usage"]["total_tokens"] > 0

    def test_multi_turn_conversation(self):
        """Multi-turn agent must maintain conversation context."""
        conversation = [
            {"role": "user", "content": "My name is Alice. Remember that."}
        ]
        result = run_multi_turn_agent(conversation)
        assert "reply" in result

        # Second turn — check context is maintained
        conversation = result["conversation"]
        conversation.append({"role": "user", "content": "What is my name?"})
        result2 = run_multi_turn_agent(conversation)
        assert "Alice" in result2["reply"], "Multi-turn context not maintained!"

    def test_provider_switch_openai_to_anthropic(self):
        """
        Calling with model='claude-3' must work without any code change.
        This proves provider switching via config.yaml works.
        """
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

        result = run_agent("Say 'hello from claude'", model="claude-3")
        assert result is not None
        assert len(result["response"]) > 0

    def test_session_id_in_response(self):
        """Response must contain the session_id for tracing."""
        result = run_agent("Hello")
        assert "session_id" in result
        assert len(result["session_id"]) > 0

    def test_gateway_client_chat(self):
        """GatewayClient.chat() must return a string response."""
        client = GatewayClient()
        reply = client.chat("What is the capital of France? One word only.")
        assert isinstance(reply, str)
        assert len(reply) > 0
        assert "Paris" in reply


# ─── Provider Switching Test ───────────────────────────────────────────────────

class TestProviderSwitching:

    def test_model_names_are_config_driven(self):
        """
        Model name 'gpt-4' vs 'claude-3' must be config-driven.
        Agent code must not hardcode the actual provider model string.
        """
        source = inspect.getsource(demo_agent_module)
        # These are provider-specific model strings that should be in config, not code
        assert "gpt-4-turbo-preview" not in source
        assert "claude-3-sonnet-20240229" not in source

    def test_default_model_from_env(self):
        """Model selection must read from LLM_MODEL env var."""
        source = inspect.getsource(demo_agent_module)
        assert "LLM_MODEL" in source, \
            "Agent must support LLM_MODEL env var for model selection."


# ─── Run summary ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
