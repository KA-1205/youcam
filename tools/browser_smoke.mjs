/** Run against an isolated local stack; no key or image bytes are logged. */
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const port = process.env.ANCHOR_BROWSER_PORT ?? '3017';
const origin = `http://127.0.0.1:${port}`;
const env = { ...process.env, CORS_ORIGINS: origin,
  NEXT_PUBLIC_TRANSPORT: 'live', NEXT_PUBLIC_API_BASE_URL: 'http://127.0.0.1:8017' };
const children = [];
function launch(command, args) { const child = spawn(command, args, { env, stdio: ['ignore', 'pipe', 'pipe'] });
  if (command === 'node') { child.stdout.on('data', chunk => process.stdout.write('WEB_BOOT ' + chunk.toString())); child.stderr.on('data', chunk => process.stdout.write('WEB_BOOT ' + chunk.toString())); }
  child.on('exit', code => { if (code) console.log('CHILD_EXIT', command, code); });
  children.push(child); return child; }
let browser;
let page;
const errors = [];
try {
  const migrated = launch('.venv/bin/python', ['-m', 'alembic', '-c', 'infra/migrations/alembic.ini', 'upgrade', 'head']);
  await new Promise((resolve, reject) => migrated.on('exit', code => code === 0 ? resolve() : reject(new Error('migration failed'))));
  launch('.venv/bin/uvicorn', ['apps.api.main:app', '--host', '127.0.0.1', '--port', '8017', '--no-access-log']);
  launch('.venv/bin/python', ['-m', 'apps.worker.main', '--loop']);
  launch('node', ['node_modules/next/dist/bin/next', 'start', 'apps/web', '--hostname', '127.0.0.1', '--port', port]);
  browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
    headless: true, args: ['--no-sandbox', '--no-zygote', '--single-process'] });
  page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  for (let attempt = 0; attempt < 80; attempt++) {
    try { const response = await page.goto(origin, { waitUntil: 'networkidle', timeout: 5000 });
      if (response?.ok()) break; }
    catch { await new Promise(resolve => setTimeout(resolve, 250)); }
  }
  console.log('API_HEALTH', (await page.request.get('http://127.0.0.1:8017/healthz')).status());
  const cors = await page.request.fetch('http://127.0.0.1:8017/api/sessions', { method: 'OPTIONS', headers: { Origin: origin, 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'content-type,idempotency-key' }});
  console.log('CORS_PROBE', cors.status(), await cors.text());
  console.log('HOME', await page.title());
  console.log('BUTTONS', await page.getByRole('button').allTextContents());
  if (!['live', 'commerce'].includes(process.env.ANCHOR_BROWSER_RUN)) {
    console.log('TEXT', (await page.locator('main').innerText()).slice(-2200));
  } else {
    await page.getByRole('button', { name: 'Generate looks' }).click();
    await page.waitForURL('**/studio', { timeout: 30000 });
    console.log('SESSION_CREATED');
    if (process.env.ANCHOR_BROWSER_RUN === 'commerce') {
      await page.getByRole('button', { name: 'Use this look', exact: true }).first().click();
      await page.goto(origin + '/checkout', { waitUntil: 'networkidle' });
      await page.getByRole('button', { name: 'Demo sign-in and keep this guest session' }).click();
      await page.getByRole('heading', { name: 'Totals', exact: true }).waitFor({ timeout: 30000 });
      console.log('CHECKOUT_READY');
      const checkboxes = page.getByRole('checkbox');
      for (const checkbox of await checkboxes.all()) await checkbox.check();
      await page.getByRole('button', { name: 'Confirm purchase', exact: true }).click();
      await page.waitForURL('**/orders/**', { timeout: 30000 });
      console.log('ORDER_CREATED');
      await page.goto(origin + '/wardrobe', { waitUntil: 'networkidle' });
      await page.getByRole('link', { name: 'View order', exact: true }).first().waitFor({ timeout: 30000 });
      console.log('ORDER_RESTORED_AFTER_FULL_RELOAD');
      await page.getByRole('button', { name: 'Add to wardrobe', exact: true }).click();
      await page.getByText(/owned 1 \(manual 1\)/).first().waitFor({ timeout: 30000 });
      console.log('MANUAL_WARDROBE_ENTRY_SAVED');
      console.log('CONSOLE_ERRORS', errors);
      if (errors.length) process.exitCode = 1;
      await browser.close(); browser = null;
      for (const child of children) child.kill('SIGTERM');
      process.exit(process.exitCode ?? 0);
    }
    await page.getByRole('link', { name: 'Preview', exact: true }).click();
    await page.getByRole('heading', { name: 'Preview on you' }).waitFor();
    const capture = page.getByRole('region', { name: 'Photo capture for HAIR_COLOR' });
    await capture.locator('input[type=checkbox]').nth(0).check();
    await capture.locator('input[type=checkbox]').nth(1).check();
    await capture.locator('input[type=file]').setInputFiles(process.env.ANCHOR_TEST_PHOTO);
    const upload = page.getByRole('region', { name: 'Upload and consent' });
    await upload.getByRole('checkbox').nth(0).check();
    await upload.getByRole('checkbox').nth(1).check();
    await upload.getByRole('button', { name: 'Upload photo', exact: true }).click();
    await page.getByRole('button', { name: 'Photo uploaded ✓' }).waitFor({ timeout: 60000 });
    console.log('PHOTO_UPLOADED');
    await page.getByRole('button', { name: 'Generate preview', exact: true }).click();
    await page.getByRole('img', { name: 'YouCam preview result', exact: true }).waitFor({ timeout: 600000 });
    const image = page.getByRole('img', { name: 'YouCam preview result', exact: true });
    await image.evaluate(img => img.decode());
    console.log('REAL_RESULT_DISPLAYED', await image.evaluate(img => ({ width: img.naturalWidth, height: img.naturalHeight })));
    await page.reload({ waitUntil: 'networkidle' });
    await page.getByRole('img', { name: 'YouCam preview result', exact: true }).waitFor({ timeout: 30000 });
    console.log('RELOAD_RESULT_RESTORED');
    await page.getByRole('button', { name: 'Delete my preview photos' }).click();
    await page.getByRole('img', { name: 'YouCam preview result', exact: true }).waitFor({ state: 'detached' });
    console.log('PRIVATE_PHOTOS_DELETED');
  }
  console.log('CONSOLE_ERRORS', errors);
  if (errors.length) process.exitCode = 1;
} catch (error) {
  console.log('BROWSER_FAILURE', error.message);
  console.log('CONSOLE_ERRORS', errors);
  if (page) console.log('FAILURE_UI', (await page.locator('main').innerText()).slice(-1600));
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  for (const child of children) child.kill('SIGTERM');
}
