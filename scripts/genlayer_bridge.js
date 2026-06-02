/**
 * convenatAI — GenLayer Transaction Bridge (Fixed)
 *
 * Correctly encodes GenLayer RPC transactions using gen_call with proper
 * method/args format (NOT hex data encoding — that only works for EVM-compatible chains).
 *
 * GenLayer's gen_call RPC accepts:
 *   READ:  type='read',  to, method, args (object of keyword args)
 *   WRITE: type='write', from, to, method, args (object of keyword args)
 *
 * Usage:
 *   node genlayer_bridge.js read <contract> <method> '<json_args>'
 *   node genlayer_bridge.js write <contract> <method> '<json_args>'
 *
 * Env:
 *   GENLAYER_PRIVATE_KEY  - Private key (with or without 0x prefix)
 *   GENLAYER_NETWORK      - testnet-bradbury (default), studionet, or studionet-8443
 */

const https = require('https');
const http = require('http');

const NETWORKS = {
  'studionet':       { rpc: 'https://studio.genlayer.com/api',          chainId: 10700 },
  'studionet-8443':  { rpc: 'https://studio.genlayer.com:8443/api',     chainId: 10700 },
  'testnet-bradbury':{ rpc: 'https://rpc-bradbury.genlayer.com',        chainId: 10701 },
};

function getNetwork() {
  const name = (process.env.GENLAYER_NETWORK || 'testnet-bradbury').toLowerCase();
  return NETWORKS[name] || NETWORKS['testnet-bradbury'];
}

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
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => {
        try { resolve(JSON.parse(d)); }
        catch(e) { reject(new Error('Invalid JSON from RPC: ' + d.substring(0, 200))); }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

async function main() {
  const action = process.argv[2];    // 'read' or 'write'
  const contract = process.argv[3];
  const method = process.argv[4];
  const argsStr = process.argv[5] || '{}';

  if (!action || !contract || !method) {
    console.error(JSON.stringify({
      error: 'Usage: node genlayer_bridge.js <read|write> <contract> <method> <args_json>'
    }));
    process.exit(1);
  }

  let args = {};
  try { args = JSON.parse(argsStr); }
  catch {
    console.error(JSON.stringify({ error: 'Invalid args JSON' }));
    process.exit(1);
  }

  const network = getNetwork();
  const pk = (process.env.GENLAYER_PRIVATE_KEY || '').replace('0x', '');
  const fromAddr = pk ? '0x' + pk.slice(-40).toLowerCase() : '0x0000000000000000000000000000000000000000';

  try {
    // Build gen_call params
    const callType = action === 'write' ? 'write' : 'read';
    const params = {
      type: callType,
      to: contract,
      method: method,
      args: args,
    };

    // Only add 'from' for writes (required for tx signing)
    if (action === 'write') {
      params.from = fromAddr;
    }

    const result = await httpRequest(network.rpc, {
      jsonrpc: '2.0',
      method: 'gen_call',
      params: [params],
      id: 1,
    });

    console.log(JSON.stringify(result));
  } catch (e) {
    console.error(JSON.stringify({ error: e.message }));
    process.exit(1);
  }
}

main();
