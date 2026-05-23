#!/usr/bin/env bash
# =============================================================================
# convenatAI — Go Live! Setup Script
# Run this after adding your CIRCLE_API_KEY and CIRCLE_ENTITY_SECRET to .env
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "  convenatAI — Go Live Setup"
echo "============================================================"

# 1. Verify .env has Circle keys
if ! grep -q "CIRCLE_API_KEY=" .env 2>/dev/null || \
   grep -q "CIRCLE_API_KEY=$" .env 2>/dev/null || \
   grep -q "CIRCLE_API_KEY=TEST_API_KEY" .env 2>/dev/null; then
  echo "❌ CIRCLE_API_KEY not set in .env"
  echo "   Get yours at: https://console.circle.com"
  exit 1
fi

if ! grep -q "CIRCLE_ENTITY_SECRET=" .env 2>/dev/null || \
   grep -q "CIRCLE_ENTITY_SECRET=$" .env 2>/dev/null || \
   grep -q "CIRCLE_ENTITY_SECRET=xxxxxxxx" .env 2>/dev/null; then
  echo "❌ CIRCLE_ENTITY_SECRET not set in .env"
  echo "   Register at: https://developers.circle.com/wallets/dev-controlled/register-entity-secret"
  exit 1
fi

echo "✅ Circle API keys found in .env"

# 2. Activate/create venv
if [ ! -d .venv ]; then
  python3 -m venv .venv
  echo "✅ Created virtual environment"
fi
source .venv/bin/activate

# 3. Install dependencies (including Circle SDK)
echo "Installing dependencies..."
pip install -e ".[circle]" 2>&1 | tail -5
echo "✅ Dependencies installed"

# 4. Test Circle connection
echo ""
echo "Testing Circle connection..."
python3 -c "
from convenatai.agent import HAS_CIRCLE
if HAS_CIRCLE:
    print('✅ Circle SDK loaded successfully')
else:
    print('❌ Circle SDK failed to load — check your API keys')
    exit(1)
"

# 5. Provision wallets
echo ""
echo "Provisioning Arc Testnet wallets..."
python3 -c "
from convenatai.arc_integration import ArcJobManager
mgr = ArcJobManager(use_live=True)
print(f'ArcJobManager live mode: {mgr.is_live}')
if mgr.is_live:
    print('✅ Ready to create ERC-8183 jobs on Arc Testnet!')
else:
    print('❌ Live mode not available')
"

# 6. Run the demo in live mode
echo ""
echo "============================================================"
echo "  ✅ Setup complete! Run the live demo with:"
echo ""
echo "  source .venv/bin/activate"
echo "  python3 run.py --price 5 --duration 3"
echo ""
echo "  (Use small amounts — each USDC = 1,000,000 units at 6 decimals)"
echo "============================================================"
