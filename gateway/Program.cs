using System.Net;
using System.Text;
using System.Text.Json;
using System.Security.Cryptography;
using Microsoft.Win32;

namespace MariageGateway;

internal sealed class GatewayConfig
{
    public string NasPath { get; set; } = @"X:\Mariage_Alexandra_Lucas";
    public string AdminPassword { get; set; } = "";
    public string DjPassword { get; set; } = "";
    public int Port { get; set; } = 8787;
    public bool StartWithWindows { get; set; } = true;
}

internal static class ConfigStore
{
    private static readonly string Folder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "MariageGateway");
    private static readonly string FilePath = Path.Combine(Folder, "config.json");

    public static GatewayConfig Load()
    {
        Directory.CreateDirectory(Folder);
        if (!File.Exists(FilePath)) return new GatewayConfig();
        try
        {
            return JsonSerializer.Deserialize<GatewayConfig>(File.ReadAllText(FilePath), new JsonSerializerOptions { PropertyNameCaseInsensitive = true }) ?? new GatewayConfig();
        }
        catch { return new GatewayConfig(); }
    }

    public static void Save(GatewayConfig config)
    {
        Directory.CreateDirectory(Folder);
        File.WriteAllText(FilePath, JsonSerializer.Serialize(config, new JsonSerializerOptions { WriteIndented = true }));
    }
}

internal sealed class GatewayServer : IDisposable
{
    private readonly GatewayConfig _config;
    private readonly HttpListener _listener = new();
    private CancellationTokenSource? _cts;
    private readonly Dictionary<string, (string Table, string Role)> _users;

    public GatewayServer(GatewayConfig config)
    {
        _config = config;
        _listener.Prefixes.Add($"http://+:{config.Port}/");
        _users = BuildUsers();
    }

    private static Dictionary<string, (string, string)> BuildUsers()
    {
        var users = new Dictionary<string, (string,string)>(StringComparer.OrdinalIgnoreCase);
        void Add(string table, params string[] names)
        {
            foreach (var name in names)
                users[Normalize(name)] = (table, name is "Alexandra" or "Lucas" ? "superadmin" : "guest");
        }
        Add("Guadeloupe","Kevin","Marie-Jo","Marc","Sylvie","Louise","Joseph","Boris","Méline","Morgane");
        Add("Île Maurice","Sophie D","Michel D","Éliane","Gérard","Michel T","Sophie T","Nino","Nathalie");
        Add("Maldives","Alexandra","Lucas","Maxime B","Roman","Marine","Clémence","Alexandre","Khoil","Michel A");
        Add("Mexique","Quentin","Maxime P","Lucas B","Chloé","Loris","Nina","Maxime G","Florian","Sarah");
        users[Normalize("DJ")] = ("", "dj");
        return users;
    }

    private static string Normalize(string value)
    {
        var normalized = value.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder();
        foreach (var c in normalized)
            if (System.Globalization.CharUnicodeInfo.GetUnicodeCategory(c) != System.Globalization.UnicodeCategory.NonSpacingMark)
                sb.Append(char.ToLowerInvariant(c));
        return sb.ToString().Trim();
    }

    public Task StartAsync()
    {
        if (_listener.IsListening) return Task.CompletedTask;
        _cts = new CancellationTokenSource();
        _listener.Start();
        _ = Task.Run(() => LoopAsync(_cts.Token));
        return Task.CompletedTask;
    }

    public void Stop()
    {
        try { _cts?.Cancel(); } catch { }
        try { if (_listener.IsListening) _listener.Stop(); } catch { }
    }

    private async Task LoopAsync(CancellationToken token)
    {
        while (!token.IsCancellationRequested && _listener.IsListening)
        {
            try
            {
                var context = await _listener.GetContextAsync();
                _ = Task.Run(() => HandleAsync(context));
            }
            catch when (token.IsCancellationRequested) { }
            catch { await Task.Delay(250, token); }
        }
    }

    private async Task HandleAsync(HttpListenerContext ctx)
    {
        AddCors(ctx.Response);
        if (ctx.Request.HttpMethod == "OPTIONS")
        {
            ctx.Response.StatusCode = 204;
            ctx.Response.Close();
            return;
        }

        try
        {
            var path = ctx.Request.Url?.AbsolutePath ?? "/";
            if (path == "/api/health")
            {
                await JsonAsync(ctx, new { ok = true, nasConnected = TestNas(), serverTime = DateTimeOffset.Now });
            }
            else if (path == "/api/time")
            {
                var unlock = new DateTimeOffset(2026, 8, 29, 18, 0, 0, TimeSpan.FromHours(2));
                await JsonAsync(ctx, new { serverTime = DateTimeOffset.Now, tableUnlockAt = unlock, tableUnlocked = DateTimeOffset.Now >= unlock });
            }
            else if (path == "/api/login" && ctx.Request.HttpMethod == "POST")
            {
                using var reader = new StreamReader(ctx.Request.InputStream, ctx.Request.ContentEncoding);
                var body = await reader.ReadToEndAsync();
                var doc = JsonDocument.Parse(body);
                var name = doc.RootElement.TryGetProperty("name", out var n) ? n.GetString() ?? "" : "";
                var password = doc.RootElement.TryGetProperty("password", out var p) ? p.GetString() ?? "" : "";
                if (!_users.TryGetValue(Normalize(name), out var user))
                {
                    await JsonAsync(ctx, new { error = "Prénom non reconnu." }, 401);
                    return;
                }
                if (user.Role == "superadmin" && password != _config.AdminPassword)
                {
                    await JsonAsync(ctx, new { error = "Mot de passe administrateur incorrect." }, 401);
                    return;
                }
                if (user.Role == "dj" && password != _config.DjPassword)
                {
                    await JsonAsync(ctx, new { error = "Mot de passe DJ incorrect." }, 401);
                    return;
                }
                var token = Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
                await JsonAsync(ctx, new { token, user = new { name, table = user.Table, role = user.Role } });
            }
            else
            {
                await JsonAsync(ctx, new { error = "Route inconnue." }, 404);
            }
        }
        catch (Exception ex)
        {
            await JsonAsync(ctx, new { error = ex.Message }, 500);
        }
    }

    private bool TestNas()
    {
        try
        {
            EnsureTree();
            var test = Path.Combine(_config.NasPath, "Logs", ".test-ecriture");
            File.WriteAllText(test, DateTime.Now.ToString("O"));
            File.Delete(test);
            return true;
        }
        catch { return false; }
    }

    public void EnsureTree()
    {
        string[] folders = {
            "Configuration",
            Path.Combine("Photos","Privees"),
            Path.Combine("Photos","Stories"),
            Path.Combine("Jeu","Questions"),
            Path.Combine("Jeu","Reponses"),
            Path.Combine("Jeu","Scores"),
            Path.Combine("Jeu","Historique"),
            "Sauvegardes","Logs","Temp"
        };
        Directory.CreateDirectory(_config.NasPath);
        foreach (var folder in folders)
            Directory.CreateDirectory(Path.Combine(_config.NasPath, folder));
    }

    private static void AddCors(HttpListenerResponse response)
    {
        response.Headers["Access-Control-Allow-Origin"] = "*";
        response.Headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization";
        response.Headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS";
    }

    private static async Task JsonAsync(HttpListenerContext ctx, object payload, int status = 200)
    {
        var bytes = JsonSerializer.SerializeToUtf8Bytes(payload);
        ctx.Response.StatusCode = status;
        ctx.Response.ContentType = "application/json; charset=utf-8";
        ctx.Response.ContentLength64 = bytes.Length;
        await ctx.Response.OutputStream.WriteAsync(bytes);
        ctx.Response.Close();
    }

    public void Dispose() => Stop();
}

internal sealed class MainForm : Form
{
    private readonly GatewayConfig _config;
    private GatewayServer? _server;
    private readonly TextBox _nas = new();
    private readonly TextBox _admin = new();
    private readonly TextBox _dj = new();
    private readonly Label _nasStatus = new();
    private readonly Label _serverStatus = new();
    private readonly NotifyIcon _tray = new();

    public MainForm()
    {
        _config = ConfigStore.Load();
        Text = "Passerelle Mariage — Alexandra & Lucas";
        Width = 760;
        Height = 560;
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(248,244,240);
        Font = new Font("Segoe UI", 10);

        var title = new Label { Text = "Alexandra & Lucas", Font = new Font("Georgia", 28, FontStyle.Bold), AutoSize = true, Left = 36, Top = 28, ForeColor = Color.FromArgb(115,74,65) };
        var subtitle = new Label { Text = "Passerelle sécurisée du mariage", AutoSize = true, Left = 39, Top = 82, ForeColor = Color.FromArgb(120,105,100) };
        var card = new Panel { Left = 32, Top = 125, Width = 680, Height = 335, BackColor = Color.White, BorderStyle = BorderStyle.FixedSingle };

        AddLabel(card, "Dossier du NAS", 24, 24);
        _nas.SetBounds(24, 50, 500, 32);
        _nas.Text = _config.NasPath;
        card.Controls.Add(_nas);
        var browse = MakeButton("Parcourir", 540, 49, 110, 34);
        browse.Click += (_,_) => BrowseNas();
        card.Controls.Add(browse);

        AddLabel(card, "Mot de passe Alexandra / Lucas", 24, 98);
        _admin.SetBounds(24, 124, 300, 32);
        _admin.UseSystemPasswordChar = true;
        _admin.Text = _config.AdminPassword;
        card.Controls.Add(_admin);

        AddLabel(card, "Mot de passe DJ", 350, 98);
        _dj.SetBounds(350, 124, 300, 32);
        _dj.UseSystemPasswordChar = true;
        _dj.Text = _config.DjPassword;
        card.Controls.Add(_dj);

        var save = MakeButton("Enregistrer", 24, 180, 145, 40);
        save.Click += (_,_) => SaveConfig();
        card.Controls.Add(save);
        var test = MakeButton("Tester le NAS", 182, 180, 145, 40);
        test.Click += (_,_) => TestNas();
        card.Controls.Add(test);
        var openNas = MakeButton("Ouvrir le dossier", 340, 180, 145, 40);
        openNas.Click += (_,_) => OpenNas();
        card.Controls.Add(openNas);
        var openWeb = MakeButton("Ouvrir l’application", 498, 180, 152, 40);
        openWeb.Click += (_,_) => System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo("https://alpesex.github.io/Alexandra-Lucas-Mariage/") { UseShellExecute = true });
        card.Controls.Add(openWeb);

        _nasStatus.SetBounds(24, 248, 610, 28);
        _serverStatus.SetBounds(24, 280, 610, 28);
        card.Controls.Add(_nasStatus);
        card.Controls.Add(_serverStatus);

        var start = MakeButton("Démarrer la passerelle", 32, 478, 220, 42);
        start.Click += async (_,_) => await StartGateway();
        Controls.Add(start);
        var stop = MakeButton("Arrêter", 265, 478, 120, 42);
        stop.Click += (_,_) => StopGateway();
        Controls.Add(stop);
        Controls.Add(title);
        Controls.Add(subtitle);
        Controls.Add(card);

        _tray.Text = "Passerelle Mariage";
        _tray.Icon = SystemIcons.Application;
        _tray.Visible = true;
        _tray.DoubleClick += (_,_) => { Show(); WindowState = FormWindowState.Normal; };
        Resize += (_,_) => { if (WindowState == FormWindowState.Minimized) Hide(); };
        FormClosing += (_,e) => { if (e.CloseReason == CloseReason.UserClosing) { e.Cancel = true; Hide(); } };

        UpdateStatuses();
        if (_config.StartWithWindows) ConfigureStartup(true);
    }

    private static void AddLabel(Control parent, string text, int x, int y)
    {
        parent.Controls.Add(new Label { Text = text, AutoSize = true, Left = x, Top = y, ForeColor = Color.FromArgb(80,70,67) });
    }

    private static Button MakeButton(string text, int x, int y, int w, int h)
    {
        return new Button { Text = text, Left = x, Top = y, Width = w, Height = h, FlatStyle = FlatStyle.Flat, BackColor = Color.FromArgb(184,121,104), ForeColor = Color.White, Font = new Font("Segoe UI", 9, FontStyle.Bold), Cursor = Cursors.Hand };
    }

    private void BrowseNas()
    {
        using var dialog = new FolderBrowserDialog { Description = "Sélectionnez le dossier Mariage_Alexandra_Lucas sur le NAS", SelectedPath = _nas.Text };
        if (dialog.ShowDialog() == DialogResult.OK) _nas.Text = dialog.SelectedPath;
    }

    private void SaveConfig()
    {
        _config.NasPath = _nas.Text.Trim();
        _config.AdminPassword = _admin.Text;
        _config.DjPassword = _dj.Text;
        ConfigStore.Save(_config);
        ConfigureStartup(true);
        MessageBox.Show("Configuration enregistrée.", "Passerelle mariage", MessageBoxButtons.OK, MessageBoxIcon.Information);
    }

    private void ConfigureStartup(bool enable)
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run", true);
            if (enable) key?.SetValue("MariageGateway", $"\"{Application.ExecutablePath}\"");
            else key?.DeleteValue("MariageGateway", false);
        }
        catch { }
    }

    private void TestNas()
    {
        SaveConfig();
        try
        {
            using var server = new GatewayServer(_config);
            server.EnsureTree();
            var test = Path.Combine(_config.NasPath, "Logs", ".test-ecriture");
            File.WriteAllText(test, DateTime.Now.ToString("O"));
            File.Delete(test);
            _nasStatus.Text = "● NAS accessible — lecture et écriture opérationnelles";
            _nasStatus.ForeColor = Color.ForestGreen;
        }
        catch (Exception ex)
        {
            _nasStatus.Text = "● NAS inaccessible — " + ex.Message;
            _nasStatus.ForeColor = Color.Firebrick;
        }
    }

    private async Task StartGateway()
    {
        SaveConfig();
        try
        {
            _server?.Dispose();
            _server = new GatewayServer(_config);
            _server.EnsureTree();
            await _server.StartAsync();
            _serverStatus.Text = $"● Passerelle active sur le port {_config.Port}";
            _serverStatus.ForeColor = Color.ForestGreen;
            TestNas();
        }
        catch (HttpListenerException ex)
        {
            _serverStatus.Text = "● Démarrage impossible — lancez l’application en administrateur";
            _serverStatus.ForeColor = Color.Firebrick;
            MessageBox.Show(ex.Message, "Erreur de démarrage", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        catch (Exception ex)
        {
            _serverStatus.Text = "● Démarrage impossible — " + ex.Message;
            _serverStatus.ForeColor = Color.Firebrick;
        }
    }

    private void StopGateway()
    {
        _server?.Dispose();
        _server = null;
        UpdateStatuses();
    }

    private void OpenNas()
    {
        try
        {
            Directory.CreateDirectory(_nas.Text);
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(_nas.Text) { UseShellExecute = true });
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "Dossier inaccessible", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private void UpdateStatuses()
    {
        _nasStatus.Text = "● NAS non testé";
        _nasStatus.ForeColor = Color.DarkGoldenrod;
        _serverStatus.Text = "● Passerelle arrêtée";
        _serverStatus.ForeColor = Color.Firebrick;
    }
}

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        ApplicationConfiguration.Initialize();
        Application.Run(new MainForm());
    }
}
