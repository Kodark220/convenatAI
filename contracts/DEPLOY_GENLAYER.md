# GenLayer ConvenatContract Deployment Guide

## Prerequisites
1. GenLayer Studio account: https://studio.genlayer.com
2. Some test GEN tokens (use the 💧 faucet in Studio)
3. Your ConvenatContract.py is at `contracts/ConvenatContract.py`

## Option 1: Deploy via GenLayer Studio (Web UI) — Recommended

1. Open https://studio.genlayer.com
2. Sign in with your wallet
3. Click **"New Contract"** → **"Upload"**
4. Upload `contracts/ConvenatContract.py`
5. Click **"Deploy"**
6. Confirm the transaction
7. Copy the deployed contract address → paste into `.env` as:
   ```
   CONVENAT_CONTRACT_ADDRESS=0xYourDeployedAddress
   ```

## Option 2: Deploy via GenLayer CLI

### Install GenLayer CLI
```bash
pip install genlayer-py
# or
npm install -g @genlayer/cli
```

### Configure Network
```bash
genlayer network set bradbury
```

### Deploy
```bash
genlayer deploy \
  --contract contracts/ConvenatContract.py \
  --network bradbury
```

### Save the address
```bash
genlayer code contracts/ConvenatContract.py
# Look for the contract address in the output
```

## After Deployment

Once deployed, update your `.env`:
```env
CONVENAT_CONTRACT_ADDRESS=0x<your-deployed-address>
GENLAYER_RPC_URL=https://studio.genlayer.com:8443/api
```

## Using as ERC-8183 Hook

When creating ERC-8183 jobs on Arc, pass the ConvenatContract address
as the `hook` parameter in `createJob(provider, evaluator, expiredAt, description, hook)`.

The hook contract receives callbacks during the job lifecycle:
- On `submit()` — the hook can validate the deliverable
- On `complete()` — the hook can confirm quality assessment

## Testing the Contract

### 1. Register a test job
Call `register_job()` with:
- `stream_id`: "test-job-001"
- `buyer_id`: "TradingAgent"
- `seller_id`: "DataBrokerAgent"
- `description`: "Twitter sentiment data"
- `quality_criteria`: "Must return structured JSON with sentiment scores"
- `deliverable_uri`: "https://api.example.com/sentiment/live"

### 2. Monitor the stream
Call `monitor_stream("test-job-001", "https://api.example.com/sentiment/live")`
The GenLayer validators will:
1. Fetch the deliverable from the URI
2. Evaluate against the quality criteria using LLM
3. Emit `StreamVerified` or `StreamTerminated` event

### 3. Check job status
Call `get_job_status("test-job-001")` to read the current state.

## Bridge to Arc

The StreamTerminated event is designed to be picked up by a bridge relay
(e.g., LayerZero or a simple webhook listener) that calls the Arc
network to close the payment channel / reject the ERC-8183 job.

In the current prototype, this bridge is stubbed in `service.py`:
- A log message is emitted: "Notifying GenLayer SLA Monitor via LayerZero bridge..."
- The `arc_integration.py` has hooks ready for the bridge integration
