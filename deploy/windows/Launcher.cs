using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Windows.Forms;

class ArcReelLauncher : Form {
    Process backend;
    StreamWriter log;
    Label status = new Label();
    Button open = new Button();
    System.Windows.Forms.Timer poll = new System.Windows.Forms.Timer();
    string home;
    DateTime started;
    bool closing;
    bool backendStarted;

    [STAThread]
    static void Main() {
        bool first;
        using (var mutex = new Mutex(true, @"Local\ArcReelDesktop", out first)) {
            if (!first) {
                MessageBox.Show("ArcReel 已在运行，请打开已有的启动器窗口。", "ArcReel");
                return;
            }
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new ArcReelLauncher());
        }
    }

    public ArcReelLauncher() {
        Text = "ArcReel Desktop"; Width = 540; Height = 265;
        FormBorderStyle = FormBorderStyle.FixedDialog; MaximizeBox = false;
        StartPosition = FormStartPosition.CenterScreen;
        home = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ArcReel");
        Directory.CreateDirectory(home);
        status.SetBounds(22, 20, 480, 55); status.Text = "正在启动本地工作台…";
        open.SetBounds(22, 87, 150, 36); open.Text = "打开工作台"; open.Enabled = false;
        open.Click += (s,e) => Process.Start("http://127.0.0.1:1241");
        var credentials = new Button(); credentials.SetBounds(185, 87, 145, 36);
        credentials.Text = "查看登录信息";
        credentials.Click += (s,e) => {
            string file = Path.Combine(home, "desktop.env");
            if (File.Exists(file)) Process.Start("notepad.exe", "\"" + file + "\"");
        };
        var data = new Button(); data.SetBounds(345, 87, 145, 36); data.Text = "打开数据文件夹";
        data.Click += (s,e) => Process.Start("explorer.exe", "\"" + home + "\"");
        var hint = new Label(); hint.SetBounds(22, 145, 475, 60);
        hint.Text = "关闭此窗口将停止本地服务。\n首次登录后，在设置中配置模型供应商及 API Key。";
        Controls.AddRange(new Control[] {status, open, credentials, data, hint});
        Shown += (s,e) => StartBackend();
        FormClosing += StopBackend;
    }

    void StartBackend() {
        try {
            var listener = new TcpListener(IPAddress.Loopback, 1241);
            listener.Start(); listener.Stop();
            string root = AppDomain.CurrentDomain.BaseDirectory;
            log = new StreamWriter(Path.Combine(home, "desktop-launcher.log"), true);
            log.AutoFlush = true;
            backend = new Process();
            backend.StartInfo = new ProcessStartInfo(Path.Combine(root, "python", "python.exe"),
                "-u \"" + Path.Combine(root, "app", "desktop_entry.py") + "\" --data-home \"" + home + "\"");
            backend.StartInfo.UseShellExecute = false;
            backend.StartInfo.CreateNoWindow = true;
            backend.StartInfo.WorkingDirectory = root;
            backend.StartInfo.RedirectStandardInput = true;
            backend.StartInfo.RedirectStandardOutput = true;
            backend.StartInfo.RedirectStandardError = true;
            backend.StartInfo.EnvironmentVariables.Remove("PYTHONHOME");
            backend.StartInfo.EnvironmentVariables.Remove("PYTHONPATH");
            backend.StartInfo.EnvironmentVariables["PYTHONUTF8"] = "1";
            backend.OutputDataReceived += WriteLog;
            backend.ErrorDataReceived += WriteLog;
            backend.Start(); backendStarted = true;
            backend.BeginOutputReadLine(); backend.BeginErrorReadLine();
            started = DateTime.UtcNow;
            poll.Interval = 1000; poll.Tick += CheckReady; poll.Start();
        } catch (Exception ex) {
            status.Text = "启动失败：" + ex.Message + "\n请检查端口 1241 或数据文件夹中的日志。";
        }
    }

    void WriteLog(object sender, DataReceivedEventArgs e) {
        if (e.Data != null && log != null) lock (log) log.WriteLine(e.Data);
    }

    void CheckReady(object sender, EventArgs e) {
        if (backend.HasExited || (DateTime.UtcNow - started).TotalSeconds > 180) {
            poll.Stop(); status.Text = "启动失败或超时，请查看数据文件夹中的 desktop-launcher.log。"; return;
        }
        try {
            var request = WebRequest.Create("http://127.0.0.1:1241/health");
            request.Proxy = null; request.Timeout = 500;
            using (var response = request.GetResponse()) {
                poll.Stop(); open.Enabled = true;
                status.Text = "本地工作台已启动。登录信息保存在数据文件夹。";
                Process.Start("http://127.0.0.1:1241");
            }
        } catch (WebException) { }
    }

    void StopBackend(object sender, FormClosingEventArgs e) {
        if (closing) return;
        if (backendStarted && !backend.HasExited) {
            if (MessageBox.Show("关闭将停止服务。请先确认当前生成任务已结束。", "ArcReel",
                MessageBoxButtons.OKCancel) != DialogResult.OK) { e.Cancel = true; return; }
            closing = true; poll.Stop();
            backend.StandardInput.WriteLine("stop"); backend.StandardInput.Flush();
            if (!backend.WaitForExit(20000)) {
                var kill = Process.Start(new ProcessStartInfo("taskkill.exe", "/PID " + backend.Id + " /T /F") {
                    UseShellExecute = false, CreateNoWindow = true
                });
                kill.WaitForExit(); backend.WaitForExit();
            }
        }
        if (log != null) log.Dispose();
    }
}
