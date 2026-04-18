# LLM Gateway — Track 2 Implementation

> **Hackathon Track 2:** Centralized LLM Gateway so agents never store API keys directly.

---

## 🏗️ Architecture

```
Agent Code
   │
   │  uses env vars only (LLM_BASE_URL, LLM_API_KEY, LLM_MODEL)
   ▼
LLM Gateway (LiteLLM Proxy)   ← single endpoint for all LLM calls
   │         running at :4000
   ├──→  OpenAI  (gpt-4, gpt-3.5-turbo)
   └──→  Anthropic (claude-3, claude-3-haiku)
```

**Before (broken):**
```
Agent → api.openai.com (hardcoded key)
```

**After (your implementation):**
```
Agent → http://llm-gateway:4000 → OpenAI / Anthropic
```

---

## 🚀 Quick Start

### 1. Setup

```bash
# Clone / unzip project
cd llm-gateway

# Install Python deps
pip install -r requirements.txt

# Create .env from template
make setup
# Then edit .env and fill in your API keys
```

### 2. Start Gateway

```bash
make start
# Gateway runs at http://localhost:4000

make health   # verify it's up
```

### 3. Run Demo Agent

```bash
python agents/demo_agent.py "What is the capital of France?"
```

You should see output like:
```
✅ Model    : gpt-4
✅ Session  : 3f2e1a...
✅ Tokens   : 42
💬 Response : The capital of France is Paris.
```

---

## 📁 Project Structure

```
llm-gateway/
├── config.yaml               # LiteLLM gateway config (providers + models)
├── docker-compose.local.yml  # Docker services including gateway
├── Dockerfile.agent          # Container for demo agent
├── requirements.txt          # Python dependencies
├── Makefile                  # All commands (make help)
├── pytest.ini                # Test config
├── .env.example              # Template — copy to .env
├── .gitignore
│
├── agents/
│   ├── __init__.py
│   ├── demo_agent.py         # ✅ Main demo agent (no API keys)
│   └── gateway_client.py     # Reusable GatewayClient wrapper
│
├── tests/
│   ├── __init__.py
│   └── test_gateway.py       # Full integration + security tests
│
└── scripts/
    ├── start.sh              # Platform startup script
    └── switch_provider.sh    # Switch provider without code changes
```

---

## ⚙️ Configuration

### `config.yaml` — Add/Change Providers

```yaml
model_list:
  - model_name: gpt-4          # ← Name agents use
    litellm_params:
      model: openai/gpt-4      # ← Actual provider model
      api_key: os.environ/OPENAI_API_KEY

  - model_name: claude-3
    litellm_params:
      model: anthropic/claude-3-sonnet-20240229
      api_key: os.environ/ANTHROPIC_API_KEY
```

Keys are **never in config** — they come from environment variables.

---

## 🔁 Provider Switching (Zero Code Change)

```bash
# Switch to Anthropic
./scripts/switch_provider.sh anthropic

# Switch back to OpenAI
./scripts/switch_provider.sh openai
```

Or manually:
1. Edit `config.yaml` — change the `model:` line
2. `make restart`
3. Agent works unchanged ✅

---

## 🧪 Testing

```bash
# All tests
make test

# Security/unit tests only (no gateway needed)
make test-unit

# With live gateway
make start
make test
```

### Test Categories

| Class | What it tests | Needs gateway? |
|---|---|---|
| `TestSecurity` | No hardcoded keys in code | ❌ |
| `TestGatewayConnectivity` | Client init, URL validation | ❌ |
| `TestLiveLLMCalls` | Real LLM calls via gateway | ✅ |
| `TestProviderSwitching` | Config-driven model selection | ❌ |

---

## 🔍 Observability (Phoenix Tracing)

The gateway forwards OpenTelemetry headers automatically.

To enable Phoenix tracing, add to `config.yaml`:

```yaml
litellm_settings:
  success_callback: ["arize_phoenix"]
  failure_callback: ["arize_phoenix"]
```

And set in `.env`:
```env
ARIZE_SPACE_KEY=your-space-key
ARIZE_API_KEY=your-api-key
```

Each agent call includes a `X-Session-ID` header for trace correlation.

---

## 🔒 Security Rules

| Rule | Status |
|---|---|
| No API keys in agent code | ✅ Enforced by tests |
| Keys in environment only | ✅ Via `.env` + docker env |
| `.env` in `.gitignore` | ✅ Never committed |
| Virtual key for agents | ✅ `virtual-master-key` |

---

## 🔧 Environment Variables

| Variable | Description | Default |
|---|---|---|
| `LLM_BASE_URL` | Gateway URL | `http://localhost:4000` |
| `LLM_API_KEY` | Virtual key for agents | `virtual-master-key` |
| `LLM_MODEL` | Default model name | `gpt-4` |
| `OPENAI_API_KEY` | Real key (host only) | — |
| `ANTHROPIC_API_KEY` | Real key (host only) | — |

**Only `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` are real API keys.
They never enter agent code — only the gateway container sees them.**

---

## 📝 Using in Your Own Agents

```python
# Option 1: Direct usage
from agents.demo_agent import run_agent

result = run_agent("Your prompt here")
print(result["response"])

# Option 2: GatewayClient wrapper
from agents.gateway_client import GatewayClient

client = GatewayClient()
reply = client.chat("Your prompt here")
print(reply)
```

No API key needed. Just set the env vars and point to the gateway.

---

## ❓ Common Issues

**Gateway won't start:**
```bash
docker-compose logs llm-gateway   # check for key errors
```

**Agent can't connect:**
```bash
make health    # verify gateway is up
# Inside Docker: use http://llm-gateway:4000
# On host: use http://localhost:4000
```

**Model not found:**
- Check that `model_name` in `config.yaml` matches what the agent passes
- Restart gateway after config changes: `make restart`
