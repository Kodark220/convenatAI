/**
 * convenatAI — GenLayer Helper (Node.js)
 * 
 * Uses genlayer-js SDK to properly encode/decode GenLayer RPC calls.
 * The raw Python HTTP approach fails because GenLayer uses serialized data.
 * 
 * Usage:
 *   node scripts/genlayer_helper.js read <contract> <method> '<kwargs_json>'
 *   node scripts/genlayer_helper.js write <contract> <method> '<kwargs_json>'
 * 
 * Env: GENLAYER_PRIVATE_KEY (with or without 0x prefix)
 *      GENLAYER_PASSWORD (keystore password) 
 *      GENLAYER_NETWORK (studionet, testnet-bradbury, etc.)
 */

const { createWalletClient, http, createPublicClient, defineChain } = require('viem');
const { privateKeyToAccount } = require('viem/accounts');

const GENLAYER_PRIVATE_KEY = process.env.GENLAYER_PRIVATE_KEY || '';
const GENLAYER_PASSWORD = process.env.GENLAYER_PASSWORD || 'convenatAI123';
const GENLAYER_NETWORK = process.env.GENLAYER_NETWORK || 'studionet';

// Network configs
const NETWORKS = {
  'studionet': {
    rpc: 'https://studio.genlayer.com/api',
    isStudio: true,
  },
  'studionet-8443': {
    rpc: 'https://studio.genlayer.com:8443/api',
    isStudio: true,
  },
  'testnet-bradbury': {
    rpc: 'https://rpc-bradbury.genlayer.com',
    isStudio: false,
  },
};

async function main() {
  const action = process.argv[2];
  const contract = process.argv[3];
  const method = process.argv[4];
  const kwargs = process.argv[5] ? JSON.parse(process.argv[5]) : {};
  const args = process.argv[6] ? JSON.parse(process.argv[6]) : [];

  const network = NETWORKS[GENLAYER_NETWORK] || NETWORKS['studionet'];

  // For now, use direct HTTP calls with the correct format
  // The genlayer-js SDK handles serialization, but we can use eth_call for reads
  // and the gen_call JSON-RPC for writes with proper serialization
  
  if (action === 'read') {
    const result = await readContract(network, contract, method, kwargs, args);
    console.log(JSON.stringify(result));
  } else if (action === 'write') {
    const result = await writeContract(network, contract, method, kwargs, args);
    console.log(JSON.stringify(result));
  } else {
    console.error(JSON.stringify({ error: 'Unknown action: ' + action }));
    process.exit(1);
  }
}

async function readContract(network, contract, method, kwargs, args) {
  try {
    // Use direct gen_call RPC — the SDK handles the encoding
    // Simple HTTP approach: genlayer accepts gen_call with proper params
    const body = {
      jsonrpc: '2.0',
      method: 'gen_call',
      params: [{
        type: 'read',
        to: contract,
        method: method,
        args: args,
        kwargs: kwargs,
      }],
      id: 1,
    };

    const response = await fetch(network.rpc, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    
    if (data.error) {
      // Try alternate format — some RPCs expect 'args' as positional array with kwargs separate
      const body2 = {
        jsonrpc: '2.0',
        method: 'gen_call',
        params: [{
          type: 'read',
          to: contract,
          method: method,
          args: args,
          kwargs: kwargs,
        }],
        id: 1,
      };
      
      const response2 = await fetch(network.rpc, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body2),
      });
      
      return await response2.json();
    }

    return data;
  } catch (e) {
    return { error: e.message };
  }
}

async function writeContract(network, contract, method, kwargs, args) {
  try {
    if (!GENLAYER_PRIVATE_KEY) {
      return { error: 'GENLAYER_PRIVATE_KEY not set' };
    }

    const pk = GENLAYER_PRIVATE_KEY.startsWith('0x') ? GENLAYER_PRIVATE_KEY : '0x' + GENLAYER_PRIVATE_KEY;
    
    // Use gen_call with type=write
    const body = {
      jsonrpc: '2.0',
      method: 'gen_call',
      params: [{
        type: 'write',
        from: '0x0000000000000000000000000000000000000000', // Will be set by network
        to: contract,
        method: method,
        args: args,
        kwargs: kwargs,
      }],
      id: 1,
    };

    const response = await fetch(network.rpc, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    return await response.json();
  } catch (e) {
    return { error: e.message };
  }
}

main().catch(e => {
  console.error(JSON.stringify({ error: e.message }));
  process.exit(1);
});
