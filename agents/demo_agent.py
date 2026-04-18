"""
Demo Agent — LLM Gateway Track 2
=================================
This agent demonstrates proper usage of the LLM Gateway.

Key principles:
  - NO API keys in code
  - Uses environment variables only
  - Provider-agnostic: switching provider = change config.yaml only
  - Compatible with OpenTelemetry tracing
"""

import os
import sys
import uuid
import logging
from dotenv import load_dotenv
from openai import OpenAI

# Load .env if present (local dev only)
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_gateway_client() -> OpenAI:
    """
    Returns an OpenAI-compatible client pointed at the LLM Gateway.
    All agents should use this factory instead of instantiating OpenAI directly.
    """
    base_url = os.getenv("LLM_BASE_URL", "http://localhost:4000")
    api_key = os.getenv("LLM_API_KEY", "virtual-master-key")

    if not base_url:
        raise EnvironmentError("LLM_BASE_URL is not set. Please configure your environment.")
    if not api_key:
        raise EnvironmentError("LLM_API_KEY is not set. Please configure your environment.")

    logger.info(f"Connecting to LLM Gateway at: {base_url}")
    return OpenAI(api_key=api_key, base_url=base_url)


def run_agent(prompt: str, model: str = None, session_id: str = None) -> dict:
    """
    Runs a single LLM call through the gateway.

    Args:
        prompt:     User message
        model:      Model name from config.yaml (default: LLM_MODEL env var)
        session_id: Optional trace/session identifier

    Returns:
        dict with keys: response, model, session_id, usage
    """
    client = get_gateway_client()
    model = model or os.getenv("LLM_MODEL", "gpt-4")
    session_id = session_id or str(uuid.uuid4())

    logger.info(f"[Session {session_id}] Calling model='{model}' | prompt='{prompt[:60]}...'")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant. Be concise and clear."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        extra_headers={
            "X-Session-ID": session_id,   # For tracing
        }
    )

    result = {
        "response": response.choices[0].message.content,
        "model": response.model,
        "session_id": session_id,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
    }

    logger.info(
        f"[Session {session_id}] Response received | "
        f"tokens_used={result['usage']['total_tokens']}"
    )
    return result


def run_multi_turn_agent(conversation: list[dict], model: str = None) -> dict:
    """
    Multi-turn agent: accepts a conversation history and appends response.

    Args:
        conversation: List of {"role": ..., "content": ...} dicts
        model:        Model name

    Returns:
        dict with updated conversation and assistant reply
    """
    client = get_gateway_client()
    model = model or os.getenv("LLM_MODEL", "gpt-4")

    response = client.chat.completions.create(
        model=model,
        messages=conversation
    )

    assistant_message = {
        "role": "assistant",
        "content": response.choices[0].message.content
    }
    conversation.append(assistant_message)

    return {
        "reply": assistant_message["content"],
        "conversation": conversation,
        "usage": {
            "total_tokens": response.usage.total_tokens
        }
    }


# ─── Quick smoke test when run directly ───────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  LLM Gateway Demo Agent")
    print("="*60)

    prompt = sys.argv[1] if len(sys.argv) > 1 else "What is 2 + 2? Explain briefly."

    try:
        result = run_agent(prompt)
        print(f"\n✅ Model    : {result['model']}")
        print(f"✅ Session  : {result['session_id']}")
        print(f"✅ Tokens   : {result['usage']['total_tokens']}")
        print(f"\n💬 Response :\n{result['response']}\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure the LLM Gateway is running: docker-compose up llm-gateway")
        sys.exit(1)
