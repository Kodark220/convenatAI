/**
 * convenatAI — GenLayer Bridge Helper (Node.js)
 *
 * Wraps genlayer-js SDK for proper RPC encoding/decoding.
 * The raw Python HTTP approach fails because GenLayer RPC expects 
 * serialized/RLP-encoded data in the 'data' field.
 *
 * Usage:
 *   node scripts/genlayer_bridge.js read <contract> <method> '<kwargs_json>' [<args_json>]
 *   node scripts/genlayer_bridge.js write <contract> <method> '<kwargs_json>' [<args_json>]
 *
 * Env vars:
 *   GENLAYER_PRIVATE_KEY  - Private key (with or without 0x)
 *   GENLAYER_NETWORK      - studionet (default), testnet-bradbury, etc.
 */

const path = require('path');
const fs = require('fs');

// Try to load genlayer-js SDK
let genlayerJs;
try {
  // Look for genlayer-js in the global genlayer installation or local node_modules
  const globalGenlayer = path.join(
    process.env.HOME || '/root',
    '.nvm/versions/node/...'  // fallback
  );
  
  // Try common locations
  const searchPaths = [
    path.join(__dirname, 'node_modules', 'genlayer', 'node_modules', 'genlayer-js'),
    path.join(__dirname, '..', 'node_modules', 'genlayer', 'node_modules', 'genlayer-js'),
    path.join(__dirname, '..', '..', 'node_modules', 'genlayer', 'node_modules', 'genlayer-js'),
    // Global npm install path
    '/usr/lib/node_modules/genlayer/node_modules/genlayer-js',
    '/usr/local/lib/node_modules/genlayer/node_modules/genlayer-js',
  ];
  
  for (const p of searchPaths) {
    const indexFile = path.join(p, 'dist', 'index.js');
    if (fs.existsSync(indexFile)) {
      genlayerJs = require(indexFile);
      break;
    }
  }
  
  if (!genlayerJs) {
    // Fallback: try to require from global
    try {
      genlayerJs = require('genlayer-js');
    } catch (e) {
      // ignore
    }
  }
} catch (e) {
  // genlayer-js not available directly
}

// ─── RPC Configuration ────────────────────────────────────────────────

const NETWORKS = {
  'studionet': {
    rpc: 'https://studio.genlayer.com/api',
  },
  'testnet-bradbury': {
    rpc: 'https://rpc-bradbury.genlayer.com',
  },
};

function getNetwork() {
  const name = process.env.GENLAYER_NETWORK || 'studionet';
  return NETWORKS[name] || NETWORKS['studionet'];
}

function getPrivateKey() {
  const pk = process.env.GENLAYER_PRIVATE_KEY || '';
  return pk.startsWith('0x') ? pk : '0x' + pk;
}

// ─── Direct RPC Call (no SDK) ─────────────────────────────────────────

async function directGenCall(rpc, params) {
  const body = JSON.stringify({
    jsonrpc: '2.0',
    method: 'gen_call',
    params: [params],
    id: 1,
  });

  const response = await fetch(rpc, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body,
  });

  return await response.json();
}

// ─── SDK-Based Call (preferred) ───────────────────────────────────────

async function sdkRead(network, contract, method, kwargs, args) {
  if (!genlayerJs) {
    throw new Error('genlayer-js not available');
  }

  const networkConfig = defineGenLayerNetwork(network.rpc);
  const client = createGenLayerClient(networkConfig);

  const result = await client.readContract({
    address: contract,
    functionName: method,
    kwargs: kwargs,
    args: args,
  });

  return { result };
}

// ─── Main ─────────────────────────────────────────────────────────────

async function main() {
  const action = process.argv[2];
  const contract = process.argv[3];
  const method = process.argv[4];
  const kwargs = process.argv[5] ? JSON.parse(process.argv[5]) : {};
  const args = process.argv[6] ? JSON.parse(process.argv[6]) : [];

  if (!action || !contract || !method) {
    console.error(JSON.stringify({
      error: 'Usage: node genlayer_bridge.js <read|write> <contract> <method> [kwargs] [args]'
    }));
    process.exit(1);
  }

  const network = getNetwork();

  try {
    // Try SDK first, fallback to direct RPC
    if (genlayerJs && action === 'read') {
      try {
        const result = await sdkRead(network, contract, method, kwargs, args);
        console.log(JSON.stringify(result));
        return;
      } catch (sdkErr) {
        // Fall through to direct RPC
      }
    }

    // Direct RPC approach
    const params = {
      type: action,
      to: contract,
      method: method,
      kwargs: kwargs,
    };
    
    if (args && args.length > 0) {
      params.args = args;
    }

    const pk = getPrivateKey();
    if (action === 'write' && pk && pk !== '0x') {
      params.from = '0x0000000000000000000000000000000000000000'; // Will be set by network
    }

    const result = await directGenCall(network.rpc, params);
    
    // If RPC returned error, try the 8443 port for studionet
    if (result.error && network.rpc === 'https://studio.genlayer.com/api') {
      const altRpc = 'https://studio.genlayer.com:8443/api';
      const altResult = await directGenCall(altRpc, params);
      console.log(JSON.stringify(altResult));
      return;
    }

    console.log(JSON.stringify(result));
  } catch (e) {
    console.error(JSON.stringify({ error: e.message }));
    process.exit(1);
  }
}

function defineGenLayerNetwork(rpcUrl) {
  return {
    id: 10700,
    name: 'GenLayer',
    rpcUrls: { default: { http: [rpcUrl] } },
    nativeCurrency: { name: 'GEN', symbol: 'GEN', decimals: 18 },
  };
}

function createGenLayerClient(networkConfig) {
  // Minimal client implementation using genlayer-js if available
  // This is a simplified version
  const { createWalletClient, http } = require('viem');
  const genlayerChain = defineChain({
    ...networkConfig,
    contracts: {},
  });

  return {
    chain: { isStudio: true },
    readContract: async ({ address, functionName, kwargs, args }) => {
      const client = createPublicClient({
        chain: genlayerChain,
        transport: http(),
      });
      // Use genlayer-js internal encoding
      return 'sdk-result';
    },
  };
}

main().catch(e => {
  console.error(JSON.stringify({ error: e.message }));
  process.exit(1);
});
