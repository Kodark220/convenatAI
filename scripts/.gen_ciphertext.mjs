// Circle entity secret ciphertext generator
// Called by circle_client.py when REST public key endpoint fails
import { initiateDeveloperControlledWalletsClient } from '@circle-fin/developer-controlled-wallets';

const client = initiateDeveloperControlledWalletsClient({
  apiKey: process.env.CIRCLE_API_KEY,
  entitySecret: process.env.CIRCLE_ENTITY_SECRET,
});

client.generateEntitySecretCiphertext().then(c => {
  console.log(JSON.stringify({ ciphertext: c }));
}).catch(e => {
  console.error(JSON.stringify({ error: e.message }));
  process.exit(1);
});
