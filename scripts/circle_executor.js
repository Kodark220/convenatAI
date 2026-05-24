const { initiateDeveloperControlledWalletsClient } = require('@circle-fin/developer-controlled-wallets');

const API_KEY = process.env.CIRCLE_API_KEY;
const ENTITY_SECRET = process.env.CIRCLE_ENTITY_SECRET;

if (!API_KEY || !ENTITY_SECRET) {
  console.error(JSON.stringify({ error: 'Missing CIRCLE_API_KEY or CIRCLE_ENTITY_SECRET' }));
  process.exit(1);
}

const client = initiateDeveloperControlledWalletsClient({
  apiKey: API_KEY,
  entitySecret: ENTITY_SECRET,
});

async function main() {
  const action = process.argv[2];
  const args = JSON.parse(process.argv[3] || '{}');

  try {
    let result;

    switch (action) {
      case 'list-wallets': {
        const wallets = await client.listWallets({});
        result = wallets.data?.wallets ?? [];
        break;
      }

      case 'create-wallet-set': {
        const ws = await client.createWalletSet({
          name: args.name || 'convenatAI Agent Wallets',
        });
        result = { id: ws.data?.walletSet?.id };
        break;
      }

      case 'create-wallets': {
        const count = args.count || 1;
        const wsId = args.walletSetId;
        
        if (!wsId) {
          const ws = await client.createWalletSet({
            name: args.name || 'convenatAI Agent Wallets',
          });
          args.walletSetId = ws.data?.walletSet?.id;
        }

        const wallets = await client.createWallets({
          blockchains: ['ARC-TESTNET'],
          count: count,
          walletSetId: args.walletSetId,
          accountType: 'SCA',
        });
        result = wallets.data?.wallets?.map(w => ({
          id: w.id,
          address: w.address,
          blockchain: w.blockchain,
          accountType: w.accountType,
        })) ?? [];
        break;
      }

      case 'contract-execution': {
        const idempotencyKey = args.idempotencyKey || (require('crypto').randomUUID());
        const tx = await client.createContractExecutionTransaction({
          idempotencyKey,
          walletAddress: args.walletAddress,
          blockchain: 'ARC-TESTNET',
          contractAddress: args.contractAddress,
          abiFunctionSignature: args.abiFunctionSignature,
          abiParameters: args.abiParameters,
          fee: { type: 'level', config: { feeLevel: args.feeLevel || 'MEDIUM' } },
        });
        result = { id: tx.data?.id, state: tx.data?.state };
        break;
      }

      case 'get-balance': {
        const walletId = args.walletId;
        const balances = await client.getWalletTokenBalance({
          id: walletId,
        });
        result = balances.data?.tokenBalances ?? [];
        break;
      }

      case 'transfer-usdc': {
        const tx = await client.createTransaction({
          walletId: args.fromWalletId,
          destinationAddress: args.toAddress,
          tokenId: args.tokenId || '15dc2b5d-0994-58b0-bf8c-3a0501148ee8',  // USDC on ARC-TESTNET
          amounts: [args.amount],
          fee: { type: 'level', config: { feeLevel: args.feeLevel || 'LOW' } },
        });
        result = { id: tx.data?.id, state: tx.data?.state };
        break;
      }

      case 'check-connection': {
        const wallets = await client.listWallets({});
        result = { connected: true, walletCount: wallets.data?.wallets?.length ?? 0 };
        break;
      }

      default:
        console.error(JSON.stringify({ error: 'Unknown action: ' + action }));
        process.exit(1);
    }

    console.log(JSON.stringify(result));
  } catch (e) {
    console.error(JSON.stringify({
      error: e.message,
      details: e.response?.data || e.response || {},
    }));
    process.exit(1);
  }
}

main();
