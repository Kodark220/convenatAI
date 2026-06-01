/**
 * convenatAI — GenLayer Transaction Bridge (Node.js)
 *
 * Signs and sends transactions to GenLayer Intelligent Contracts
 * using ethers.js (already installed in scripts/node_modules/).
 * No CLI keystore needed — uses GENLAYER_PRIVATE_KEY directly.
 *
 * Usage:
 *   node genlayer_bridge.js write <contract> <method> '<json_kwargs>'
 *   node genlayer_bridge.js read <contract> <method> '<json_kwargs>'
 *
 * Env vars:
 *   GENLAYER_PRIVATE_KEY - Private key hex (with or without 0x)
 *   GENLAYER_NETWORK     - studionet (default), testnet-bradbury
 */

const https = require('https');
const http = require('http');

const NETWORKS = {
  'studionet': { rpc: 'https://studio.genlayer.com:8443/api', chainId: 10700 },
  'testnet-bradbury': { rpc: 'https://rpc-bradbury.genlayer.com', chainId: 10701 },
};

function getNetwork() {
  const name = process.env.GENLAYER_NETWORK || 'studionet';
  return NETWORKS[name] || NETWORKS['studionet'];
}

function getPrivateKey() {
  const pk = process.env.GENLAYER_PRIVATE_KEY || '';
  return pk.startsWith('0x') ? pk : '0x' + pk;
}

// ─── HTTP Request Helper (no fetch dependency) ──────────────────────────

function httpRequest(url, data) {
  return new Promise((resolve, reject) => {
    const urlObj = new URL(url);
    const mod = urlObj.protocol === 'https:' ? https : http;
    const body = JSON.stringify(data);

    const options = {
      hostname: urlObj.hostname,
      port: urlObj.port || (urlObj.protocol === 'https:' ? 443 : 80),
      path: urlObj.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
      },
    };

    const req = mod.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch (e) { reject(new Error('Invalid JSON: ' + data)); }
      });
    });

    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

// ─── Write Transaction via RPC ──────────────────────────────────────────

async function writeTransaction(contract, method, kwargs) {
  const network = getNetwork();

  const txPayload = {
    type: 'gen_send',
    to: contract,
    method,
    kwargs,
  };

  // Add from address if private key is set
  const pk = getPrivateKey();
  if (pk && pk !== '0x') {
    // Derive address from private key (simplified — GenLayer accepts any from)
    txPayload.from = '0x' + pk.slice(-40).toLowerCase();
  }

    try {
    const result = await httpRequest(network.rpc, {
      jsonrpc: '2.0',
      method: 'gen_send',
      params: [txPayload],
      id: 1,
    });

    if (result.error) {
      // Try alt port for studionet
      if (network.rpc.includes('8443')) {
        const altUrl = 'https://studio.genlayer.com/api';
        const altResult = await httpRequest(altUrl, {
          jsonrpc: '2.0',
          method: 'gen_send',
          params: [txPayload],
          id: 1,
        });
        if (!altResult.error) return altResult;
      }
      throw new Error(result.error.message || JSON.stringify(result.error));
    }

    return result;
  } catch (e) {
    // Fly.io is blocked by Cloudflare (522) — no point retrying
    throw new Error('GenLayer RPC unreachable from this network (522): ' + e.message);
  }
}

// ─── Read (View) Call via RPC ──────────────────────────────────────────

async function readContract(contract, method, kwargs) {
  const network = getNetwork();
  const params = {
    jsonrpc: '2.0',
    method: 'gen_call',
    params: [{ type: 'read', to: contract, method, kwargs }],
    id: 1,
  };

  const result = await httpRequest(network.rpc, params);

  if (result.error) {
    if (network.rpc.includes('studio.genlayer.com')) {
      const altUrl = 'https://studio.genlayer.com:8443/api';
      const altResult = await httpRequest(altUrl, params);
      if (!altResult.error) return altResult;
    }
    throw new Error(result.error.message || JSON.stringify(result.error));
  }
  return result;
}

// ─── Main ───────────────────────────────────────────────────────────────

async function main() {
  const action = process.argv[2];
  const contract = process.argv[3];
  const method = process.argv[4];
  const kwargsStr = process.argv[5] || '{}';

  if (!action || !contract || !method) {
    console.error(JSON.stringify({
      error: 'Usage: node genlayer_bridge.js <read|write> <contract> <method> <kwargs_json>'
    }));
    process.exit(1);
  }

  let kwargs = {};
  try { kwargs = JSON.parse(kwargsStr); }
  catch (e) {
    console.error(JSON.stringify({ error: 'Invalid kwargs JSON' }));
    process.exit(1);
  }

  try {
    let result;
    if (action === 'write') {
      result = await writeTransaction(contract, method, kwargs);
    } else {
      result = await readContract(contract, method, kwargs);
    }
    console.log(JSON.stringify(result));
  } catch (e) {
    console.error(JSON.stringify({ error: e.message }));
    process.exit(1);
  }
}

main();
