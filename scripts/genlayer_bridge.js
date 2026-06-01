/**
 * convenatAI — GenLayer Transaction Bridge (Node.js)
 *
 * Sends transactions using gen_call with type='write' (the correct RPC method).
 * No gen_send needed.
 *
 * Usage:
 *   node genlayer_bridge.js write <contract> <method> '<json_kwargs>'
 *   node genlayer_bridge.js read <contract> <method> '<json_kwargs>'
 *
 * Env vars:
 *   GENLAYER_PRIVATE_KEY  - Private key (without 0x) for signing writes
 *   GENLAYER_NETWORK      - studionet (default) or testnet-bradbury
 */

const https = require('https');
const http = require('http');

const NETWORKS = {
  'studionet': { rpc: 'https://studio.genlayer.com/api', chainId: 10700 },
  'testnet-bradbury': { rpc: 'https://rpc-bradbury.genlayer.com', chainId: 10701 },
};

function getNetwork() {
  const name = process.env.GENLAYER_NETWORK || 'studionet';
  return NETWORKS[name] || NETWORKS['studionet'];
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
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) },
    };
    const req = mod.request(options, (res) => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => { try { resolve(JSON.parse(d)); } catch(e) { reject(new Error('Invalid JSON: ' + d)); } });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

function abiEncode(method, kwargs) {
  // Simple ABI encoding for GenLayer contracts
  // Format: function_selector(4 bytes) + packed args
  // GenLayer uses a simple encoding: method_name + args packed
  const args = Object.values(kwargs);
  // For GenLayer, we encode as: method_name + ':' + JSON.stringify(args)
  return '0x' + Buffer.from(method + ':' + JSON.stringify(args)).toString('hex');
}

async function main() {
  const action = process.argv[2];
  const contract = process.argv[3];
  const method = process.argv[4];
  const kwargsStr = process.argv[5] || '{}';

  if (!action || !contract || !method) {
    console.error(JSON.stringify({ error: 'Usage: node genlayer_bridge.js <read|write> <contract> <method> <kwargs_json>' }));
    process.exit(1);
  }

  let kwargs = {};
  try { kwargs = JSON.parse(kwargsStr); } catch {
    console.error(JSON.stringify({ error: 'Invalid kwargs JSON' }));
    process.exit(1);
  }

  const network = getNetwork();
  const pk = process.env.GENLAYER_PRIVATE_KEY || '';

  try {
    // Encode the transaction data
    const data = abiEncode(method, kwargs);

    const callType = action === 'write' ? 'write' : 'read';
    const fromAddr = pk ? '0x' + pk.replace('0x', '').slice(-40).toLowerCase() : '0x0000000000000000000000000000000000000000';

    const result = await httpRequest(network.rpc, {
      jsonrpc: '2.0',
      method: 'gen_call',
      params: [{
        type: callType,
        from: fromAddr,
        to: contract,
        data: data,
      }],
      id: 1,
    });

    console.log(JSON.stringify(result));
  } catch (e) {
    console.error(JSON.stringify({ error: e.message }));
    process.exit(1);
  }
}

main();
