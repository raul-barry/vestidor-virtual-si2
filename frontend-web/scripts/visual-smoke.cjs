// Run after npm run build. Uses isolated fixtures; never contacts the backend.
const { createServer } = require('node:http');
const { readFileSync, existsSync, mkdirSync, writeFileSync, mkdtempSync } = require('node:fs');
const { join, extname, resolve } = require('node:path');
const { tmpdir } = require('node:os');
const { spawn } = require('node:child_process');
const WebSocket = require('ws');
const assert = require('node:assert/strict');

const root = resolve(__dirname, '../dist/vestidor-virtual-web/browser');
const artifacts = resolve(__dirname, '../artifacts/visual');
const chrome = process.env.CHROME_BIN || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const products = [1, 2, 3].map((id, i) => ({
  id_producto: id, nombre: ['Camisa Oxford', 'Pantalon de lino', 'Chaqueta urbana'][i],
  descripcion: 'Una prenda para cada ocasion.', precio_base: '250.00', estado: 'ACTIVO',
  categoria: { id_categoria: 1, nombre: 'Esenciales' }, variantes: []
}));

async function main() {
  assert(existsSync(join(root, 'index.html')), 'Run npm run build first');
  mkdirSync(artifacts, { recursive: true });
  const server = createServer((req, res) => {
    const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    let file = resolve(root, '.' + pathname);
    if (!file.startsWith(root + '/') && !file.startsWith(root + '\\')) file = join(root, 'index.html');
    if (!existsSync(file) || !extname(file)) file = join(root, 'index.html');
    res.setHeader('Content-Type', ({ '.js': 'text/javascript', '.css': 'text/css', '.html': 'text/html' })[extname(file)] || 'application/octet-stream');
    res.end(readFileSync(file));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const profile = mkdtempSync(join(tmpdir(), 'vestidor-visual-'));
  const browser = spawn(chrome, ['--headless=new', '--disable-gpu', '--disable-software-rasterizer', '--no-sandbox', '--no-first-run', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { windowsHide: true, stdio: ['ignore', 'ignore', 'pipe'] });
  let socket;
  try {
    const endpoint = await new Promise((resolve, reject) => {
      let output = '';
      const timeout = setTimeout(() => reject(new Error('Chrome startup timeout: ' + output)), 30000);
      browser.on('error', reject);
      browser.stderr.on('data', chunk => {
        output += chunk;
        const match = output.match(/DevTools listening on (ws:\/\/[^\s]+)/);
        if (match) { clearTimeout(timeout); resolve(match[1]); }
      });
    });
    const port = new URL(endpoint).port;
    const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
    socket = new WebSocket(targets.find(x => x.type === 'page').webSocketDebuggerUrl);
    await new Promise(resolve => socket.on('open', resolve));
    let id = 0;
    const pending = new Map();
    const errors = [];
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const key = ++id;
      const timeout = setTimeout(() => { pending.delete(key); reject(new Error('CDP timeout: ' + method)); }, 20000);
      pending.set(key, { resolve: value => { clearTimeout(timeout); resolve(value); }, reject });
      socket.send(JSON.stringify({ id: key, method, params }));
    });
    socket.on('message', data => {
      const msg = JSON.parse(data);
      if (msg.id) {
        const task = pending.get(msg.id); pending.delete(msg.id);
        if (msg.error) task?.reject(new Error(JSON.stringify(msg.error))); else task?.resolve(msg.result);
      }
      if (msg.method === 'Runtime.exceptionThrown') errors.push(msg.params.exceptionDetails.text);
      if (msg.method === 'Fetch.requestPaused') {
        const { requestId, request } = msg.params;
        const url = new URL(request.url);
        if (url.pathname.includes('/api/')) {
          const body = /\/products$/.test(url.pathname) ? products : [];
          void send('Fetch.fulfillRequest', { requestId, responseCode: 200, responseHeaders: [{ name: 'Content-Type', value: 'application/json' }, { name: 'Access-Control-Allow-Origin', value: '*' }, { name: 'Access-Control-Allow-Headers', value: '*' }], body: Buffer.from(JSON.stringify(body)).toString('base64') });
        } else if (url.origin !== origin) {
          void send('Fetch.failRequest', { requestId, errorReason: 'BlockedByClient' });
        } else void send('Fetch.continueRequest', { requestId });
      }
    });
    const evaluate = async expression => (await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })).result.value;
    await send('Page.enable'); await send('Runtime.enable');
    await send('Fetch.enable', { patterns: [{ urlPattern: '*' }] });
    const report = [];
    for (const [role, route] of [['', '/catalog'], ['CLIENTE', '/catalog'], ['ADMINISTRADOR', '/admin/products'], ['ENCARGADO_SUCURSAL', '/inventory'], ['CAJERO', '/pos']]) {
      const token = 'test.' + Buffer.from(JSON.stringify({ rol: role, exp: 4102444800 })).toString('base64url') + '.test';
      const { identifier } = await send('Page.addScriptToEvaluateOnNewDocument', { source: `localStorage.clear(); ${role ? `localStorage.setItem('vestidor_virtual_token', ${JSON.stringify(token)}); localStorage.setItem('vestidor_virtual_user', ${JSON.stringify(JSON.stringify({ rol: role }))});` : ''}` });
      await send('Page.navigate', { url: origin + route });
      for (let i = 0; i < 60; i++) {
        if (await evaluate('!!document.querySelector("app-navbar") && !!document.querySelector("h1")')) break;
        await delay(250);
      }
      assert(await evaluate('!!document.querySelector("h1")'), role + ' page did not render');
      assert.equal(await evaluate('location.pathname'), route, role + ' unexpected redirect');
      await delay(300);
      const staff = !!role && role !== 'CLIENTE';
      assert.equal(await evaluate('!!document.querySelector("app-admin-sidebar")'), staff);
      if (role === 'CAJERO') assert.deepEqual(await evaluate('Array.from(document.querySelectorAll("app-admin-sidebar a"), a => a.getAttribute("href"))'), ['/pos']);
      for (const width of [1440, 768, 390, 320]) {
        await send('Emulation.setDeviceMetricsOverride', { width, height: 1000, deviceScaleFactor: 1, mobile: false });
        await delay(100);
        if (staff && width < 760) {
          await evaluate('document.querySelector(".menu-toggle").click()');
          assert.equal(await evaluate('document.querySelector(".menu-toggle").getAttribute("aria-expanded")'), 'true');
        }
        const dimensions = await evaluate('({scroll:document.documentElement.scrollWidth, viewport:innerWidth})');
        assert(dimensions.scroll <= dimensions.viewport + 1, `${role || 'visitor'} ${width}px overflow: ${JSON.stringify(dimensions)}`);
        const screenshot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
        writeFileSync(join(artifacts, `${role || 'VISITOR'}-${width}.png`), Buffer.from(screenshot.data, 'base64'));
        report.push({ role: role || 'VISITOR', route, width, ...dimensions });
        if (staff && width < 760) await evaluate('document.querySelector(".menu-toggle").click()');
      }
      await send('Page.removeScriptToEvaluateOnNewDocument', { identifier });
    }
    assert.deepEqual(errors, [], 'Browser runtime exceptions');
    writeFileSync(join(artifacts, 'report.json'), JSON.stringify(report, null, 2));
    console.log(`PASS: ${report.length} role/viewport checks; screenshots in artifacts/visual. API responses are fixtures.`);
  } finally {
    socket?.close(); browser.kill(); server.close();
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
