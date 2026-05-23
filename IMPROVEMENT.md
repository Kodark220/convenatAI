# convenatAI — Improvement Roadmap

## Vision
Autonomous agent economic coordination layer where AI agents discover, negotiate,
contract, stream payments, and settle jobs — powered by Arc Network + GenLayer.

## Architecture (Target)

```
┌─────────────────────────────────────────────────────┐
│                   convenatAI                         │
│                                                      │
│  ┌──────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │ Discovery │─▶│ Negotiation │─▶│   Contract &    │  │
│  │ (Registry)│  │ (P2P Loop)  │  │    Escrow       │  │
│  └──────────┘  └─────────────┘  └───────┬────────┘  │
│                                         │           │
│  ┌──────────────────┐  ┌──────────────┐ │           │
│  │  Payment Stream   │  │  SLA Monitor  │◀┘           │
│  │ (Arc Nanopay)     │  │ (GenLayer AI) │             │
│  └──────────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────┘
         │                      │
         ▼                      ▼
   Arc Network (L1)       GenLayer (IC)
   • ERC-8004 Identity    • AI Quality eval
   • ERC-8183 Jobs        • Kill-switch
   • USDC native gas      • Strict consensus
```

## Current State (May 2026)

### ✅ Working
- Core Python package with Agent, Wallet, MessageBus, NegotiationSession
- LegalContract with escrow, signatures, delivery tracking
- NanopaymentStream with mock USDC + real Circle Arc integration
- GenLayer ConvenatContract.py (SLA monitor)
- Balance checker script

### ❌ Broken / Needs Fixing
- **`circle-developer-controlled-wallets`** — pip install times out, hangs the whole build
- **pyproject.toml** — has `circle-developer-controlled-wallets` and `web3` as unconditional deps, but they fail to install in many environments
- **No local `circle` SDK mock** — `agent.py` tries to import circle SDK and fails if not installed, breaking all imports from `convenatai.agent`
- **Tests reference old APIs** — were fixed in this session but may regress
- **Top-level `run.py` vs `convenatai/run.py`** — duplicate CLI entry points, confusing

### 🚀 Next Steps (Priority Order)

#### 1. Fix Dependency Hell
- Make `circle-developer-controlled-wallets` an optional dependency
- Use try/except import pattern (already partially done with `HAS_CIRCLE`)
- Add a `pip install convenatai[circle]` extras pattern in pyproject.toml
- Pin working versions

#### 2. Align with Real Arc Contracts
- Replace custom `LegalContract`/`Escrow` with Arc's deployed **ERC-8183 AgenticCommerce** contract
  - Address: `0x0747EEf0706327138c69792bF28Cd525089e4583`
  - Methods: `createJob()`, `setBudget()`, `fund()`, `submit()`, `complete()`
- Replace custom agent identity with Arc's **ERC-8004** registries
  - IdentityRegistry: `0x8004A818BFB912233c491871b3d84c89A494BD9e`
  - ReputationRegistry: `0x8004B663056A597Dffe9eCcC1965A193B7388713`
  - ValidationRegistry: `0x8004Cb1BF31DAf7788923b405b754f57acEB4272`

#### 3. Wire Circle API Flow End-to-End
- Create a dev console account (https://console.circle.com)
- Get API key + Entity Secret
- Implement proper wallet provisioning flow
- Implement proper USDC transfer flow
- Add balance checking before job creation

#### 4. Connect GenLayer SLA Monitor
- Deploy ConvenatContract.py to GenLayer Studio
- Hook it into ERC-8183 `createJob(hook)` parameter
- Implement the kill-switch: when GenLayer detects SLA breach, emit event → Arc bridge → close payment channel

#### 5. LayerZero / Cross-Chain Bridge
- Build the bridge: Arc (BridgeSender.sol) → ZKsync (BridgeForwarder.sol) → GenLayer (ConvenatContract.py)
- Deploy Solidity contracts to Arc Testnet + ZKsync Sepolia
- Handle event listening and relay

#### 6. Tests & CI
- Unit tests for negotiation, contract lifecycle, payment streaming
- Mock Circle SDK for CI (no real API keys needed in PRs)
- Integration test with real Arc Testnet (optional, gated on env vars)

#### 7. Documentation & CLI
- Update README with actual supported workflows
- Polish `convenatai run` CLI command
- Add `--help` for all options

## Key API References

### Arc Docs
- Agentic Economy: https://docs.arc.io/build/agentic-economy
- ERC-8004 Agent Identity: https://docs.arc.io/arc/tutorials/register-your-first-ai-agent
- ERC-8183 Job Lifecycle: https://docs.arc.io/arc/tutorials/create-your-first-erc-8183-job
- App Kit: https://docs.arc.io/app-kit
- MCP Server: https://docs.arc.io/ai/mcp (for AI-assisted development)
- LLMs.txt index: https://docs.arc.io/llms.txt

### Arc Testnet
- Chain ID: 5042002
- RPC: https://testnet.rpc.arc.io
- Faucet: https://faucet.circle.com
- Explorer: https://testnet.arcscan.app
- USDC (gas token) address: `0x3600000000000000000000000000000000000000`

### Circle SDK (Python)
- `circle-developer-controlled-wallets` on PyPI
- Methods: createWalletSet, createWallet, createContractExecutionTransaction
- Needed for: wallet provisioning, contract calls, USDC transfers

### GenLayer
- GenLayer Studio: https://studio.genlayer.com
- Docs: https://docs.genlayer.com
- ConvenatContract.py already written — deploy and connect
