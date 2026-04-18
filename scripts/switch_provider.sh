#!/usr/bin/env bash
# =============================================================
# switch_provider.sh — Switch LLM provider without code changes
# =============================================================
# Usage:
#   ./scripts/switch_provider.sh openai
#   ./scripts/switch_provider.sh anthropic
# =============================================================

PROVIDER=${1:-"openai"}

echo ""
echo "  🔄 Switching LLM Provider → $PROVIDER"
echo "  ======================================="
echo ""

CONFIG_FILE="config.yaml"

case "$PROVIDER" in
    openai)
        echo "Setting default model to: openai/gpt-4"
        sed -i 's|model: anthropic/.*|model: openai/gpt-4|g' "$CONFIG_FILE"
        echo "✅ config.yaml updated."
        ;;
    anthropic)
        echo "Setting default model to: anthropic/claude-3-sonnet-20240229"
        sed -i 's|model: openai/.*|model: anthropic/claude-3-sonnet-20240229|g' "$CONFIG_FILE"
        echo "✅ config.yaml updated."
        ;;
    *)
        echo "Unknown provider: $PROVIDER"
        echo "Usage: $0 [openai|anthropic]"
        exit 1
        ;;
esac

echo ""
echo "Restarting gateway to apply changes..."
docker-compose -f docker-compose.local.yml restart llm-gateway
echo "✅ Gateway restarted. No code changes needed!"
echo ""
echo "Test it:"
echo "  python agents/demo_agent.py 'Which provider are you?'"
echo ""
