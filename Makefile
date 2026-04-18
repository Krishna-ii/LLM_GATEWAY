# ================================================================
# Makefile — LLM Gateway Track 2
# ================================================================

.PHONY: help setup start stop restart logs test test-unit health clean switch-provider

# Default: show help
help:
	@echo ""
	@echo "  LLM Gateway — Available Commands"
	@echo "  ================================="
	@echo ""
	@echo "  make setup            Copy .env.example → .env (edit keys after)"
	@echo "  make start            Start LLM Gateway"
	@echo "  make start-nasiko     Start full platform (gateway + agents)"
	@echo "  make stop             Stop all services"
	@echo "  make restart          Restart gateway only"
	@echo "  make logs             Tail gateway logs"
	@echo "  make health           Check gateway health"
	@echo "  make test             Run all tests"
	@echo "  make test-unit        Run security/unit tests only (no gateway needed)"
	@echo "  make demo             Run demo agent"
	@echo "  make switch-provider  Show provider switching instructions"
	@echo "  make clean            Remove containers and volumes"
	@echo ""

# ─── Setup ────────────────────────────────────────────────────

setup:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env from .env.example"; \
		echo "⚠️  Edit .env and fill in your API keys before starting."; \
	else \
		echo "ℹ️  .env already exists, skipping."; \
	fi
	pip install -r requirements.txt

# ─── Start / Stop ─────────────────────────────────────────────

start:
	docker-compose -f docker-compose.local.yml up -d llm-gateway
	@echo "✅ LLM Gateway started at http://localhost:4000"
	@echo "   Run 'make health' to verify."

start-nasiko:
	docker-compose -f docker-compose.local.yml up -d
	@echo "✅ Full platform started."

stop:
	docker-compose -f docker-compose.local.yml down

restart:
	docker-compose -f docker-compose.local.yml restart llm-gateway
	@echo "✅ Gateway restarted."

# ─── Logs & Health ────────────────────────────────────────────

logs:
	docker-compose -f docker-compose.local.yml logs -f llm-gateway

health:
	@curl -s http://localhost:4000/health | python3 -m json.tool || \
		echo "❌ Gateway not reachable. Run: make start"

# ─── Tests ────────────────────────────────────────────────────

test:
	pytest tests/ -v --tb=short

test-unit:
	pytest tests/test_gateway.py::TestSecurity tests/test_gateway.py::TestGatewayConnectivity::test_gateway_client_initialization tests/test_gateway.py::TestGatewayConnectivity::test_gateway_url_is_not_openai_direct tests/test_gateway.py::TestProviderSwitching -v --tb=short

# ─── Demo ─────────────────────────────────────────────────────

demo:
	@echo "Running demo agent..."
	python agents/demo_agent.py "What is the capital of France?"

# ─── Provider Switching ───────────────────────────────────────

switch-provider:
	@echo ""
	@echo "  Provider Switching — Zero Code Change"
	@echo "  ======================================"
	@echo ""
	@echo "  1. Edit config.yaml"
	@echo "     Change:  model: openai/gpt-4"
	@echo "     To:      model: anthropic/claude-3-sonnet-20240229"
	@echo ""
	@echo "  2. Restart gateway:"
	@echo "     make restart"
	@echo ""
	@echo "  3. Run demo — no code change needed:"
	@echo "     make demo"
	@echo ""

# ─── Clean ────────────────────────────────────────────────────

clean:
	docker-compose -f docker-compose.local.yml down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleaned up."
