/** Accept standard preview flags while keeping the Next.js app in its workspace. */
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const args = process.argv.slice(2);
const option = (name, fallback) => {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : fallback;
};
const host = option('--host', option('--hostname', '127.0.0.1'));
const port = option('--port', process.env.PORT ?? '3000');
const root = fileURLToPath(new URL('../', import.meta.url));
const mode = args.includes('--production') ? 'start' : 'dev';
const child = spawn(process.execPath, [root + 'node_modules/next/dist/bin/next',
  mode, root + 'apps/web', ...(mode === 'dev' ? ['--webpack'] : []),
  '--hostname', host, '--port', port], { stdio: 'inherit' });
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
child.on('exit', code => process.exit(code ?? 0));
child.on('error', error => { console.error(error.message); process.exit(1); });
