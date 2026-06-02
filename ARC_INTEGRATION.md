# convenatAI — Arc ERC-8183 Integration Plan

This creates a new file that bridges your agent negotiation layer directly to Arc's deployed on-chain contracts.

## Contract Addresses (Arc Testnet)
- **AgenticCommerce (ERC-8183)**: `0xcc23aF94f43Ffcfe7348C5135B5d1Fb4e148E5f1`
- **USDC (ERC-20 interface)**: `0x3600000000000000000000000000000000000000`
- **IdentityRegistry (ERC-8004)**: `0x8004A818BFB912233c491871b3d84c89A494BD9e`
- **ReputationRegistry**: `0x8004B663056A597Dffe9eCcC1965A193B7388713`
- **ValidationRegistry**: `0x8004Cb1BF31DAf7788923b405b754f57acEB4272`

## Network
- **RPC**: `https://rpc.testnet.arc.network`
- **Chain ID**: 5042002
- **Explorer**: `https://testnet.arcscan.app`
- **Faucet**: `https://faucet.circle.com`
- **Native gas**: USDC (6 decimals for ERC-20 interface, 18 for native)

## ERC-8183 Contract Functions
| Function | Signature | Called By | State |
|----------|-----------|-----------|-------|
| `createJob(provider, evaluator, expiredAt, description, hook)` | returns `jobId` | Client | Open |
| `setBudget(jobId, amount, optParams)` | — | Provider | Open |
| `fund(jobId, optParams)` | — | Client | Funded |
| `submit(jobId, deliverable, optParams)` | — | Provider | Submitted |
| `complete(jobId, reason, optParams)` | — | Evaluator | Completed/Rejected |
| `getJob(jobId)` | returns job tuple | Anyone | — |

## Job Status Values
0=Open, 1=Funded, 2=Submitted, 3=Completed, 4=Rejected, 5=Expired

## Architecture After Integration

```
Agent Negotiation Layer (Python)
         │
         ▼   uses Circle Developer-Controlled Wallets API
Arc Network
  ├─ ERC-8183: createJob → setBudget → fund → submit → complete
  ├─ USDC: approve → transfer (escrow)
  └─ ERC-8004: register agent identity + reputation

GenLayer (optional, via hook parameter)
  └─ ConvenatContract.py evaluates deliverables, triggers kill-switch
```
