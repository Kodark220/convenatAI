# convenatAI

Autonomous economic infrastructure for AI agents. A dual-chain agent economy
built on **Arc Network** (ERC-8183 job lifecycle) and **GenLayer** (AI-driven
SLA enforcement via intelligent contracts).

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Quick Start — Mock Mode](#quick-start--mock-mode)
- [Live Mode — Requirements](#live-mode--requirements)
- [Architecture Diagram](#architecture-diagram)
- [Module Reference](#module-reference)
- [Testing](#testing)
- [Contract Addresses](#contract-addresses)
- [Wallet Funding](#wallet-funding)

---

## Architecture Overview

convenatAI lets AI agents discover each other, negotiate terms, lock in
agreements, and stream payments — all without human mediation.

### Dual-Chain Stack

| Layer | Chain | Role |
|-------|-------|------|
| **Identity & Reputation** | Arc Testnet | ERC-8004 IdentityRegistry, ReputationRegistry, ValidationRegistry |
| **Job Lifecycle** | Arc Testnet | ERC-8183 AgenticCommerce — create/setBudget/fund/submit/complete jobs |
| **Payments** | Arc Testnet | USDC transfers via Circle Developer-Controlled Wallets |
| **SLA Enforcement** | GenLayer Studionet | AI quality monitoring + kill-switch on breached SLAs |

### Key Components

- **`Agent` / `Wallet`** — Autonomous agent with balance, on-chain identity, and
  negotiation capabilities. Works locally (mock) or with real Arc wallets.
- **`AgentRegistry` / `MessageBus`** — P2P discovery and async messaging.
- **`NegotiationSession`** — Proposal/counter-offer exchange until agreement or
  max rounds.
- **`LegalContract`** — Self-executing contract with escrow, signing,
  fulfillment tracking, and arbitration.
- **`NanopaymentStream`** — Continuous value streaming over a
  `PaymentChannel`.
- **`ArcJobManager`** — ERC-8183 job lifecycle (create, setBudget, fund,
  submit, complete, release). Local mock or live on Arc.
- **`ArcIdentityManager`** — ERC-8004 identity/reputation/validation
  registries. Local mock or live on Arc.
- **`NotifyGenLayer`** — GenLayer SLA monitoring calls (register_job,
  monitor_stream, get_job_status).
- **`ContractExecutionService`** — High-level orchestrator tying negotiation →
  contract → payment → SLA monitoring in a single flow.

---

## Quick Start — Mock Mode

No API keys needed. Everything runs in-memory.

```bash
# 1. Install (requires Python >=3.11)
pip install -e .

# 2. Run the demo
python run.py

# 3. Or use the installed CLI
convenatAI --price 1200 --duration 5
```

### Programmatic Usage

```python
import asyncio
from convenatai.agent import Agent, Wallet
from convenatai.network import AgentRegistry, MessageBus
from convenatai.negotiation import Proposal
from convenatai.service import ContractExecutionService

registry = AgentRegistry()
bus = MessageBus(registry)

payer = Agent("Buyer", role="trading", wallet=Wallet(1500))
seller = Agent("Seller", role="broker", wallet=Wallet(500))
bus.register_agent(payer)
bus.register_agent(seller)

proposal = Proposal(
    proposer=payer,
    responder=seller,
    description="AI signal access",
    price=1200,
    duration=4,
    deliverable="signal_stream",
)

service = ContractExecutionService()
outcome = asyncio.run(service.execute_trade(proposal))
print(outcome.contract.state)  # FULFILLED
```

---

## Live Mode — Requirements

For actual on-chain execution on Arc Testnet:

1. **Circle API credentials** — set in `.env`:
   ```
   CIRCLE_API_KEY=your_live_api_key
   CIRCLE_ENTITY_SECRET=your_entity_secret
   USDC_TOKEN_ID=15dc2b5d-0994-58b0-bf8c-3a0501148ee8
   ARC_RPC_URL=https://rpc.testnet.arc.network
   ```

2. **Funded wallets** — at least one wallet with testnet USDC (see
   [Wallet Funding](#wallet-funding)).

3. **Install extras**:
   ```bash
   pip install -e ".[circle,server]"
   ```

The system auto-detects Circle keys. When present, `ArcJobManager` and
`ArcIdentityManager` use live on-chain mode. When absent, they transparently
fall back to local mocks.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                      convenatAI                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐   ┌──────────────┐   ┌─────────────────────┐  │
│  │  Agent    │──▶│Negotiation   │──▶│LegalContract        │  │
│  │  Wallet   │   │Session       │   │Escrow  Signing      │  │
│  └──────────┘   └──────────────┘   └────────┬────────────┘  │
│                                              │               │
│  ┌──────────┐   ┌──────────────┐             ▼               │
│  │AgentReg  │   │ MessageBus   │   ┌─────────────────────┐  │
│  │istry     │   │ (async P2P)  │   │NanopaymentStream    │  │
│  └──────────┘   └──────────────┘   │PaymentChannel       │  │
│                                     │ArcNanopaymentGateway│  │
│                                     └────────┬────────────┘  │
│                                              │               │
│  ┌───────────────────────────────────────────┘               │
│  ▼                                                           │
│  ┌──────────────────────────────────────────────────────┐    │
│  │            Dual-Chain Settlement                      │    │
│  │                                                       │    │
│  │  ┌──────────────────┐      ┌──────────────────┐      │    │
│  │  │  Arc Testnet      │      │ GenLayer          │      │    │
│  │  │                   │      │ Studionet         │      │    │
│  │  │  ERC-8183 Job     │      │ SLA Monitor       │      │    │
│  │  │  ERC-8004 Identity│      │ Kill-Switch       │      │    │
│  │  │  Circle USDC Tx   │      │ AI Evaluation     │      │    │
│  │  └──────────────────┘      └──────────────────┘      │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘

Flow:
 Agent A proposes ──▶ Negotiation ──▶ Agreement ──▶ Contract
    │                                                     │
    └─▶ Payment Channel ──▶ NanopaymentStream ──▶ Done
                                    │
                                    └─▶ GenLayer SLA Monitor
                                        ├─ OK  ─▶ Complete
                                        └─ FAIL ─▶ Kill-Switch (close channel)
```

---

## Module Reference

### `convenatai.agent`

| Class | Description |
|-------|-------------|
| `Wallet(balance, address, wallet_id)` | Agent wallet with deposit, withdraw, reserve, transfer |
| `Agent(name, role, wallet, capabilities)` | Autonomous agent with propose/evaluate/sign, async messaging |

### `convenatai.network`

| Class | Description |
|-------|-------------|
| `AgentRegistry()` | Register/lookup agents by name, role, or all |
| `MessageBus(registry)` | Async message queues for P2P agent communication |
| `Message(sender, receiver, type, payload, session_id)` | Message dataclass |

### `convenatai.negotiation`

| Class | Description |
|-------|-------------|
| `Proposal(proposer, responder, description, price, duration, deliverable)` | Deal terms with auto-computed payment schedule |
| `ProposalResponse(accepted, declined, reason, counter)` | Response with optional counter-offer |
| `NegotiationSession(initial_proposal, max_rounds)` | Async proposal/counter-offer loop |

### `convenatai.contract`

| Class | Description |
|-------|-------------|
| `LegalContract(proposal)` | Self-executing contract: sign, activate, delivery, breach, cancel, settle |
| `Escrow(payer, amount)` | Locked funds released on fulfillment |
| `Arbitrator(name)` | GenLayer-like adjudication for disputed contracts |

### `convenatai.payment`

| Class | Description |
|-------|-------------|
| `PaymentChannel(payer, payee, capacity)` | Bidirectional channel with open/send/close |
| `NanopaymentStream(channel, amount, duration)` | Streams payments per delivery unit; supports kill-switch |
| `ArcNanopaymentGateway(token_symbol)` | Factory for opening/closing channels |

### `convenatai.arc_integration`

| Class | Description |
|-------|-------------|
| `ArcJobManager(use_live)` | ERC-8183 job lifecycle (create, setBudget, fund, submit, complete, release) |
| `ArcJobInfo` | In-memory job state (job_id, addresses, budget, status) |
| `JobStatus` | Enum: OPEN, FUNDED, SUBMITTED, COMPLETED, REJECTED, EXPIRED |

### `convenatai.arc_identity`

| Class | Description |
|-------|-------------|
| `ArcIdentityManager(use_live)` | ERC-8004 identity/reputation/validation registries |
| `IdentityInfo` / `ReputationInfo` / `ValidationInfo` | Registry data classes |

### `convenatai.genlayer_client`

| Static Method | Description |
|---------------|-------------|
| `NotifyGenLayer.register_job(stream_id, buyer_id, seller_id, ...)` | Register SLA monitor on GenLayer |
| `NotifyGenLayer.monitor_stream(stream_id, deliverable_uri)` | Trigger AI quality evaluation |
| `NotifyGenLayer.get_job_status(stream_id)` | Check job active/inactive |

### `convenatai.service`

| Class | Description |
|-------|-------------|
| `ContractExecutionService(gateway, arc, identity)` | High-level orchestrator: negotiate → contract → payment → SLA |
| `ContractExecutionOutcome(stream, channel, contract, status)` | Result with stream, channel, status |

---

## Testing

Tests are in `tests/` and use **pytest** (no external API calls, all mock/local).

```bash
# Install test dependency
pip install pytest

# Run all tests
pytest tests/ -v

# Run a specific module
pytest tests/test_agent.py -v
pytest tests/test_arc_integration.py -v
pytest tests/test_arc_identity.py -v
pytest tests/test_genlayer_client.py -v
pytest tests/test_negotiation.py -v
pytest tests/test_network.py -v
pytest tests/test_payment.py -v

# Run without the execution service test (which hits real GenLayer RPC)
pytest tests/ -v -k "not execution_service"
```

### Test Coverage

| Module | Tests | What's covered |
|--------|-------|----------------|
| `test_agent.py` | 15 | Wallet operations (deposit, withdraw, reserve, transfer), Agent creation, propose, fund |
| `test_network.py` | 8 | Registry CRUD, MessageBus send/receive/broadcast, error handling |
| `test_negotiation.py` | 12 | Proposal creation, with_updates, ProposalResponse, evaluate logic, full negotiation session |
| `test_payment.py` | 10 | Channel open/send/close, NanopaymentStream full cycle, kill-switch, schedule |
| `test_arc_integration.py` | 11 | ArcJobManager mock mode: create, setBudget, fund, submit, complete, release, full lifecycle |
| `test_arc_identity.py` | 12 | Mock identity/reputation/validation registry operations |
| `test_genlayer_client.py` | 7 | Address formatting, RPC error handling without live CLI |
| `test_negotiator_net.py` | 3 | Legacy integration: contract lifecycle, payment stream, execution service |
| **Total** | **80+** | |

All tests run in < 35s (excluding the GenLayer-dependent execution service test).

---

## Contract Addresses

### Arc Testnet

| Contract | Address | Description |
|----------|---------|-------------|
| **AgenticCommerce** (ERC-8183) | `0x0747EEf0706327138c69792bF28Cd525089e4583` | Job lifecycle (create, fund, submit, complete) |
| **IdentityRegistry** (ERC-8004) | `0x8004A818BFB912233c491871b3d84c89A494BD9e` | Agent identity registration |
| **ReputationRegistry** (ERC-8004) | `0x8004B663056A597Dffe9eCcC1965A193B7388713` | Agent reputation scores |
| **ValidationRegistry** (ERC-8004) | `0x8004Cb1BF31DAf7788923b405b754f57acEB4272` | Agent validation status |
| **USDC (ERC-20)** | `0x3600000000000000000000000000000000000000` | Testnet USDC token |

### GenLayer Studionet

| Contract | Address | Description |
|----------|---------|-------------|
| **ConvenatContract** | `0xc821A31Bfe1299131D4D07E78a0c7D388B1E9642` | SLA monitor (register_job, monitor_stream, get_job_status) |

---

## Wallet Funding

### Arc Testnet Faucet

To obtain testnet USDC for agent wallets:

1. Go to the [Arc Testnet Faucet](https://faucet.testnet.arc.network) (or the
   official Arc faucet).

2. Enter the agent's wallet address (found in Circle dashboard after creating
   a Developer-Controlled Wallet).

3. Request testnet USDC — typically **25 USDC** per request.

### Circle Developer Dashboard

1. Navigate to **Circle Developer-Controlled Wallets**.
2. Create a **Wallet Set** → create wallets on **ARC-TESTNET**.
3. Fund wallets via faucet.
4. Set `CIRCLE_API_KEY` and `CIRCLE_ENTITY_SECRET` in `.env`.

### Local Wallet (Mock Mode)

In mock mode, wallet balances are just Python floats — no funding needed.

```python
wallet = Wallet(balance=1000.0)  # Instant mock funding
wallet.deposit(500.0)            # Add more
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CIRCLE_API_KEY` | Live only | — | Circle API key for Developer-Controlled Wallets |
| `CIRCLE_ENTITY_SECRET` | Live only | — | Circle entity secret |
| `USDC_TOKEN_ID` | Live only | `15dc2b5d-0994-58b0-bf8c-3a0501148ee8` | USDC token ID on Arc Testnet |
| `ARC_RPC_URL` | No | `https://rpc.testnet.arc.network` | Arc Testnet RPC endpoint |
| `GENLAYER_RPC_URL` | No | `https://studio.genlayer.com/api` | GenLayer RPC endpoint |
| `CONVENAT_CONTRACT_ADDRESS` | No | `0xc821A31Bfe1299131D4D07E78a0c7D388B1E9642` | GenLayer ConvenatContract address |

---

## License

MIT
