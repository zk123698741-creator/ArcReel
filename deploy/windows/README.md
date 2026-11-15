# Windows 独立安装包

目标：Windows 10/11 x64。安装程序包含 Python、后端依赖、构建好的前端、
Claude Agent SDK 自带 CLI、FFmpeg 和 Git for Windows/Bash。使用默认浏览器显示工作台。
运行端无需安装 Python、Node.js、Docker 或 Git；AI 生成仍需联网及配置模型供应商。

## GitHub 构建

1. 在自己的 Fork 中启用 Actions。
2. 打开 **Actions → Windows installer → Run workflow**，选择含构建文件的分支。
3. 成功运行后，下载 **ArcReel-windows-x64** artifact。
4. 解压 artifact，运行 `ArcReel-0.36.0-windows-x64-Setup.exe`；文件名版本跟随源码。

工作流先构建前端，再组装可迁移的 Python 运行时，执行两次真实启动测试，
最后用 Inno Setup 生成 EXE 和 `SHA256SUMS.txt`。没有配置代码签名。
每次构建要求新的输出目录，避免旧文件混入。

## 安装与使用

安装到当前用户目录，无需管理员权限。开始菜单启动 **ArcReel** 后，会打开本地工作台。
启动器的 **查看登录信息** 按钮打开首次生成的用户名和随机密码。
登录后进入设置配置 Agent、文本、图像、视频等服务。

- 程序：`%LOCALAPPDATA%\Programs\ArcReel`
- 数据：`%LOCALAPPDATA%\ArcReel\data`
- 登录配置：`%LOCALAPPDATA%\ArcReel\desktop.env`
- Claude 会话：`%LOCALAPPDATA%\ArcReel\claude`
- 启动日志：`%LOCALAPPDATA%\ArcReel\desktop-launcher.log`
- 监听：`127.0.0.1:1241`

关闭启动器窗口会停止后端；关闭前等待生成任务结束。端口 1241 被占用时启动器提示失败。
升级前退出启动器，备份整个 `%LOCALAPPDATA%\ArcReel`，再安装新版本。
卸载只移除安装目录，保留用户数据。恢复时，在停止服务后还原上述数据目录。

## 本地构建

构建机器需要 Windows x64、Git for Windows、Node.js 24、Corepack、uv 和 Inno Setup。

```powershell
cd frontend
corepack pnpm install --frozen-lockfile
corepack pnpm build
cd ..
uv run --no-project --python 3.13.14 python deploy/windows/build.py --output dist/windows --iscc 'C:\Program Files (x86)\Inno Setup 7\ISCC.exe'
```

`build.py` 沿用 `uv.lock`，把 workspace 子包安装成非 editable 包；
拷贝由 uv 管理的 Python 完整发行版和 Git 运行时，保留各自许可证。
应用的 `LICENSE`、`NOTICE` 和 `LICENSES/` 随包分发，应用源码也随安装目录分发。

## 验证范围

`smoke.py` 在清除系统 Python/Node/Git 路径后验证随包 FFmpeg、Claude CLI、Git Bash、
中文及空格数据路径、SQLite 迁移、前端 HTML、登录、令牌校验、凭据持久化和优雅停止。
不会调用付费模型服务。端到端生成、Windows Sandbox 全新系统安装、安装器交互和代码签名
需要各自单独验证，构建成功不代表这些步骤已执行。
