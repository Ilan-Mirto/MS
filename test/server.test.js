const { test } = require('node:test');
const assert = require('node:assert/strict');
const { createAppServer } = require('../server');

test('serves the page and accepts a Socket.IO connection', async (t) => {
  const { httpServer, io } = createAppServer();
  await new Promise((resolve) => httpServer.listen(0, resolve));
  t.after(() => new Promise((resolve) => io.close(resolve)));

  const address = httpServer.address();
  const baseUrl = `http://localhost:${address.port}`;
  const page = await fetch(baseUrl);
  assert.equal(page.status, 200);
  assert.match(await page.text(), /Socket\.IO/);

  const clientScript = await fetch(`${baseUrl}/socket.io/socket.io.js`);
  assert.equal(clientScript.status, 200);

  const pollingUrl = new URL('/socket.io/', baseUrl);
  pollingUrl.search = new URLSearchParams({ EIO: '4', transport: 'polling' });
  const handshake = await fetch(pollingUrl);
  assert.equal(handshake.status, 200);
  const handshakeData = await handshake.text();
  const engineSid = JSON.parse(handshakeData.slice(1)).sid;

  pollingUrl.searchParams.set('sid', engineSid);
  const connect = await fetch(pollingUrl, { method: 'POST', body: '40' });
  assert.equal(connect.status, 200);
  const connected = await fetch(pollingUrl);
  assert.match(await connected.text(), /^40\{"sid":/);

  await fetch(pollingUrl, { method: 'POST', body: '41' });
});
