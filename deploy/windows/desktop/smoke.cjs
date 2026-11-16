const assert = require('node:assert/strict');
const fs = require('node:fs');
const { Menu, app } = require('electron');

async function eventually(window, script) {
  for (let attempt = 0; attempt < 120; attempt++) {
    const value = await window.webContents.executeJavaScript(script);
    if (value) return value;
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Desktop rendering timed out: ${script}`);
}

exports.verify = async ({ window, base, home, root, report }) => {
  const result = { passed: false, electron: process.versions.electron, base, home, root };
  const preferences = window.webContents.getLastWebPreferences();
  assert.equal(preferences.nodeIntegration, false);
  assert.equal(preferences.contextIsolation, true);
  assert.equal(preferences.sandbox, true);
  result.menu = Menu.getApplicationMenu().items.map((item) => item.label);
  assert.deepEqual(result.menu, ['工作台', '编辑', '视图']);
  result.login = await eventually(window, `document.body.innerText.includes('用户名') && document.body.innerText.includes('密码') && document.body.innerText.includes('登录') && document.body.innerText`);
  result.locale = await window.webContents.executeJavaScript("localStorage.getItem('i18nextLng')");
  assert.equal(result.locale, 'zh');
  assert.equal(await window.webContents.executeJavaScript('typeof window.require'), 'undefined');
  fs.writeFileSync(`${report}.login.png`, (await window.webContents.capturePage()).toPNG());
  const text = fs.readFileSync(`${home}/desktop.env`, 'utf8');
  const entries = Object.fromEntries(text.trim().split(/\r?\n/).map((line) => { const index = line.indexOf('='); return [line.slice(0, index), line.slice(index + 1)]; }));
  const response = await fetch(`${base}/api/v1/auth/token`, {
    method: 'POST', body: new URLSearchParams({ username: entries.AUTH_USERNAME, password: entries.AUTH_PASSWORD }),
  });
  assert.equal(response.status, 200);
  const { access_token: token } = await response.json();
  await window.webContents.executeJavaScript(`localStorage.setItem('arcreel_auth_token', ${JSON.stringify(token)})`);
  await window.loadURL(base);
  result.dashboard = await eventually(window, `document.body.innerText.includes('还没有项目') && !document.querySelector('input[type="password"]') && document.body.innerText`);
  await window.webContents.executeJavaScript('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))');
  fs.writeFileSync(`${report}.dashboard.png`, (await window.webContents.capturePage()).toPNG());
  assert.equal(new URL(window.webContents.getURL()).origin, base);
  result.windowTitle = window.getTitle();
  result.userData = app.getPath('userData');
  result.passed = true;
  fs.writeFileSync(report, JSON.stringify(result, null, 2));
};
