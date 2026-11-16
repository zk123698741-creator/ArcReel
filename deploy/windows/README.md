# Windows 独立中文桌面版

Windows 10/11 x64。安装包内置 Electron/Chromium、Python、后端依赖、React 工作台、
Claude CLI、FFmpeg 和 Git/Bash。启动 ArcReel.exe 直接显示独立窗口，首次默认中文。
运行端无需另装浏览器、WebView2、Python、Node.js、Docker 或 Git。AI 生成需要配置模型服务。

## GitHub 构建

Actions → Windows installer → Run workflow。成功后下载 ArcReel-windows-x64 artifact，
解压并运行 ArcReel-0.36.0-windows-x64-Setup.exe。版本跟随源码，未配置代码签名。

流程构建原前端，按 uv.lock 安装后端，按 package-lock.json 安装 Electron 45.3.2，
将 Chromium 完整运行时随包分发。分别执行后端和真实桌面渲染测试，再编译中文 Inno Setup 安装器。
桌面语言初始化只修改独立 profile，后续设置中的语言选择会保留。

## 使用与升级

启动后直接进入桌面窗口。菜单「工作台 → 查看登录信息」显示首次生成的账号密码；
菜单也可打开数据目录和启动日志。登录后在设置中配置供应商。
退出时确认当前生成任务已结束；程序停止本地服务。

- 安装：默认 %LOCALAPPDATA%\Programs\ArcReel；已有安装沿用原路径。
- 数据：%LOCALAPPDATA%\ArcReel\data
- 登录：%LOCALAPPDATA%\ArcReel\desktop.env
- Claude：%LOCALAPPDATA%\ArcReel\claude
- 桌面 profile：%LOCALAPPDATA%\ArcReel\desktop-profile
- 日志：%LOCALAPPDATA%\ArcReel\desktop-launcher.log
- 本机接口：127.0.0.1:1241，保留认证。

升级前退出旧版并备份 %LOCALAPPDATA%\ArcReel，再安装新版。
卸载保留用户数据。外部供应商文档链接在用户点击后使用系统浏览器，工作台本身在桌面窗口内运行。

## 本地构建

构建环境：Windows x64、Git for Windows、Node.js 24、Corepack、uv、Inno Setup。

```powershell
cd frontend
corepack pnpm install --frozen-lockfile
corepack pnpm build
cd ..
uv run --no-project --python 3.13.14 python deploy/windows/build.py --output dist/windows --iscc 'C:\Program Files (x86)\Inno Setup 7\ISCC.exe'
```

输出目录必须全新。应用 LICENSE、NOTICE、LICENSES、源码及 Electron/Chromium 和运行时许可证随包分发。
安装器中文资源来自 Inno Setup 官方仓库 jrsoftware/issrc，提交
1f29baac6c6dfd35e04c237af2ea51c482ee782a，Files/Languages/ChineseSimplified.isl，
SHA256 e0b0b350e2245f3c5e65586dfe43d574f6e7f06f2261149aba284954b3fc9a8d。

## 验证范围

smoke.py：清除系统运行时路径，验证随包工具、中文空格数据路径、SQLite、HTTP、认证、重启和停止。
desktop_smoke.py：以隔离数据目录实际运行 ArcReel.exe，验证中文登录页、认证后项目页、中文菜单、
渲染进程隔离和服务退出；生成 JSON 和页面截图。此测试不读取正式项目，也不调用付费模型。
安装器交互、全新 Windows 系统安装、付费模型创作全流程需单独验证。
