const { app, BrowserWindow, Menu, dialog, shell } = require('electron');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const net = require('node:net');

const argument = (name) => {
  const index = process.argv.indexOf(name);
  return index < 0 ? undefined : process.argv[index + 1];
};
const smokeReport = argument('--desktop-smoke-report');
const home = smokeReport ? argument('--desktop-smoke-home') : path.join(process.env.LOCALAPPDATA, 'ArcReel');
if (!home || !path.isAbsolute(home)) throw new Error('An absolute desktop data directory is required');
fs.mkdirSync(home, { recursive: true });
app.setPath('userData', path.join(home, 'desktop-profile'));
app.setName('ArcReel');
app.commandLine.appendSwitch('lang', 'zh-CN');
const root = path.dirname(process.execPath);
let window;
let backend;
let log;
let stopping = false;
let stopped = false;
let base;
let exitCode = 0;
let decidingQuit = false;

function logError(error) {
  log?.write(`${new Date().toISOString()} ${error.stack || error}\n`);
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', reject);
    server.listen(smokeReport ? 0 : 1241, '127.0.0.1', () => {
      const port = server.address().port;
      server.close((error) => error ? reject(error) : resolve(port));
    });
  });
}

async function waitForBackend() {
  const deadline = Date.now() + 180000;
  while (Date.now() < deadline && !stopping) {
    if (backend.exitCode !== null) throw new Error('本地服务启动失败，请查看启动日志。');
    try {
      const response = await fetch(`${base}/health`, { signal: AbortSignal.timeout(800) });
      if (response.ok) return;
    } catch { /* The service is still starting. */ }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error('本地服务启动超时，请查看启动日志。');
}

async function stopBackend() {
  if (!backend || backend.exitCode !== null) return;
  await new Promise((resolve) => {
    const timeout = setTimeout(() => {
      const killer = spawn('taskkill.exe', ['/PID', String(backend.pid), '/T', '/F'], { windowsHide: true });
      killer.once('error', (error) => { logError(error); resolve(); });
      killer.once('exit', resolve);
    }, 20000);
    backend.once('exit', () => { clearTimeout(timeout); resolve(); });
    if (backend.stdin.writable) backend.stdin.end('stop\n');
  });
}

function buildMenu() {
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    { label: '工作台', submenu: [
      { label: '查看登录信息', click: async () => {
        const filename = path.join(home, 'desktop.env');
        const detail = fs.existsSync(filename) ? fs.readFileSync(filename, 'utf8') : '服务正在启动，请稍后重试。';
        await dialog.showMessageBox(window, { type: 'info', title: '登录信息', message: '本机工作台账号', detail, buttons: ['关闭'] });
      } },
      { label: '打开数据文件夹', click: () => shell.openPath(home) },
      { label: '查看启动日志', click: () => shell.openPath(path.join(home, 'desktop-launcher.log')) },
      { type: 'separator' },
      { label: '退出', accelerator: 'Alt+F4', click: () => app.quit() },
    ] },
    { label: '编辑', submenu: [
      { label: '撤销', role: 'undo' }, { label: '重做', role: 'redo' }, { type: 'separator' },
      { label: '剪切', role: 'cut' }, { label: '复制', role: 'copy' },
      { label: '粘贴', role: 'paste' }, { label: '全选', role: 'selectAll' },
    ] },
    { label: '视图', submenu: [
      { label: '重新加载', role: 'reload' }, { label: '放大', role: 'zoomIn' },
      { label: '缩小', role: 'zoomOut' }, { label: '实际大小', role: 'resetZoom' },
      { label: '全屏', role: 'togglefullscreen' },
    ] },
  ]));
}

function permitNavigation(url) {
  return url.startsWith(`${base}/`) || url.startsWith(`blob:${base}/`);
}

async function start() {
  log = fs.createWriteStream(path.join(home, 'desktop-launcher.log'), { flags: 'a' });
  base = `http://127.0.0.1:${await freePort()}`;
  window = new BrowserWindow({
    title: 'ArcReel 创作工作台', width: 1360, height: 900, minWidth: 960, minHeight: 640,
    backgroundColor: '#111827', show: !smokeReport,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false, contextIsolation: true, sandbox: true, backgroundThrottling: false,
    },
  });
  window.webContents.session.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
  window.webContents.setWindowOpenHandler(({ url }) => {
    if (permitNavigation(url)) return { action: 'allow', overrideBrowserWindowOptions: { webPreferences: { nodeIntegration: false, contextIsolation: true, sandbox: true } } };
    if (/^https?:/.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });
  window.webContents.on('will-navigate', (event, url) => {
    if (!permitNavigation(url)) {
      event.preventDefault();
      if (/^https?:/.test(url)) shell.openExternal(url);
    }
  });
  window.webContents.on('page-title-updated', (event) => { event.preventDefault(); });
  window.on('close', (event) => { if (!stopped) { event.preventDefault(); app.quit(); } });
  buildMenu();
  await window.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent('<html lang="zh-CN"><body style="background:#111827;color:#eee;font:20px Microsoft YaHei;padding:60px"><h1>ArcReel 创作工作台</h1><p>正在启动，请稍候…</p></body></html>'));
  const env = { ...process.env, PYTHONUTF8: '1', PYTHONNOUSERSITE: '1' };
  for (const key of ['PYTHONHOME', 'PYTHONPATH', 'ELECTRON_RUN_AS_NODE']) delete env[key];
  backend = spawn(path.join(root, 'python', 'python.exe'), [
    '-u', path.join(root, 'app', 'desktop_entry.py'), '--data-home', home, '--port', new URL(base).port,
  ], { cwd: root, env, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
  backend.stdout.pipe(log, { end: false });
  backend.stderr.pipe(log, { end: false });
  backend.stdin.on('error', logError);
  backend.on('error', fail);
  backend.on('exit', (code) => {
    if (!stopping) fail(new Error(`本地服务已停止（${code}），请查看启动日志。`));
  });
  await waitForBackend();
  if (stopping) return;
  await window.loadURL(base);
  if (smokeReport) {
    await require('./smoke.cjs').verify({ window, base, home, root, report: smokeReport });
    app.quit();
  }
}

function fail(error) {
  exitCode = 1;
  logError(error);
  if (smokeReport) {
    fs.writeFileSync(smokeReport, JSON.stringify({ passed: false, error: String(error) }));
    app.quit();
  } else {
    dialog.showErrorBox('ArcReel 启动失败', `${error.message}\n日志：${path.join(home, 'desktop-launcher.log')}`);
    app.quit();
  }
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', () => { if (window) { if (window.isMinimized()) window.restore(); window.show(); window.focus(); } });
  app.whenReady().then(start).catch(fail);
  app.on('window-all-closed', () => app.quit());
  app.on('before-quit', async (event) => {
    if (stopped) return;
    event.preventDefault();
    if (stopping || decidingQuit) return;
    if (!smokeReport && backend && backend.exitCode === null) {
      decidingQuit = true;
      const answer = await dialog.showMessageBox(window, {
        type: 'question', title: '退出 ArcReel', message: '退出将停止本地服务，请确认当前生成任务已结束。',
        buttons: ['退出', '继续使用'], defaultId: 1, cancelId: 1,
      });
      decidingQuit = false;
      if (answer.response !== 0) return;
    }
    stopping = true;
    await stopBackend();
    if (log) await new Promise((resolve) => log.end(resolve));
    stopped = true;
    app.exit(exitCode);
  });
}
