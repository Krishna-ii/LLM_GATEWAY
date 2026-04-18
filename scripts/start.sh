#!/usr/bin/env bash
# =============================================================
# start.sh — Start the LLM Gateway platform
# =============================================================
set -e

echo ""
echo "  🚀 LLM Gateway — Starting Platform"
echo "  ===================================="
echo ""

# Check .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Copying from .env.example..."
    cp .env.example .env
    echo "✅ Created .env — please edit it with your API keys and re-run."
    exit 1
fi

# Load env
export $(grep -v '^#' .env | xargs)

# Validate required keys
if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ERROR: At least one of OPENAI_API_KEY or ANTHROPIC_API_KEY must be set in .env"
    exit 1
fi

echo "✅ Environment loaded"
echo "   Gateway URL : ${LLM_BASE_URL:-http://localhost:4000}"
echo "   Model       : ${LLM_MODEL:-gpt-4}"
echo ""

# Start gateway
echo "Starting LLM Gateway..."
docker-compose -f docker-compose.local.yml up -d llm-gateway

# Wait for health
echo "Waiting for gateway to be healthy..."
MAX_WAIT=30
WAITED=0
until curl -sf http://localhost:4000/health > /dev/null 2>&1; do
    if [ "$WAITED" -ge "$MAX_WAIT" ]; then
        echo "❌ Gateway did not start in ${MAX_WAIT}s. Check logs: docker-compose logs llm-gateway"
        exit 1
    fi
    sleep 2
    WAITED=$((WAITED + 2))
    echo "  Waiting... (${WAITED}s)"
done

echo ""
echo "✅ LLM Gateway is live at http://localhost:4000"
echo ""
echo "  Quick test:"
echo "    python agents/demo_agent.py 'Hello, world!'"
echo ""
echo "  Run tests:"
echo "    make test"
echo ""
