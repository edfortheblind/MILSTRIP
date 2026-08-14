using System.Drawing;
using System.Runtime.InteropServices;

namespace Milstrip.Desktop;

internal sealed class MainForm : Form
{
    internal const int MaximumInputCharacters = 1_000_000;

    private readonly IAnalysisAdapter _analysis;
    private readonly TextBox _input = new();
    private readonly DataGridView _results = new();
    private readonly TextBox _canonical = new();
    private readonly TextBox _issues = new();
    private readonly Label _summary = new();
    private readonly Button _analyzeButton = new();
    private readonly List<Control> _actions = [];
    private string _lastAcceptedInput = string.Empty;
    private bool _changingInput;

    internal MainForm(IAnalysisAdapter analysis)
    {
        _analysis = analysis;
        Text = "MILSTRIP Intake Tool";
        StartPosition = FormStartPosition.CenterScreen;
        MinimumSize = new Size(900, 680);
        Size = new Size(1100, 780);
        AutoScaleMode = AutoScaleMode.Dpi;
        AllowDrop = true;

        Controls.Add(BuildLayout());
        DragEnter += OnDragEnter;
        DragDrop += OnDragDrop;
    }

    private Control BuildLayout()
    {
        var root = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            Padding = new Padding(16),
            ColumnCount = 1,
            RowCount = 6,
        };
        root.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        root.RowStyles.Add(new RowStyle(SizeType.Percent, 35));
        root.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        root.RowStyles.Add(new RowStyle(SizeType.Percent, 40));
        root.RowStyles.Add(new RowStyle(SizeType.Percent, 25));
        root.RowStyles.Add(new RowStyle(SizeType.AutoSize));

        var banner = new Label
        {
            Text = "Phase 2A review only — no file created or uploaded",
            AutoSize = true,
            Font = new Font(Font, FontStyle.Bold),
            ForeColor = Color.DarkRed,
            AccessibleName = "Phase limitation notice",
            Margin = new Padding(0, 0, 0, 10),
        };
        root.Controls.Add(banner, 0, 0);

        var inputGroup = new GroupBox
        {
            Text = "Request or email text",
            Dock = DockStyle.Fill,
            AccessibleName = "Request or email input",
        };
        _input.Multiline = true;
        _input.ScrollBars = ScrollBars.Both;
        _input.AcceptsReturn = true;
        _input.AcceptsTab = false;
        _input.WordWrap = false;
        _input.Dock = DockStyle.Fill;
        _input.AccessibleName = "Request or email text";
        _input.AccessibleDescription = "Paste text here, or open or drop a TXT file.";
        _input.AllowDrop = true;
        _input.DragEnter += OnDragEnter;
        _input.DragDrop += OnDragDrop;
        _input.TextChanged += OnInputChanged;
        inputGroup.Controls.Add(_input);
        root.Controls.Add(inputGroup, 0, 1);

        var actions = new FlowLayoutPanel
        {
            AutoSize = true,
            Dock = DockStyle.Fill,
            FlowDirection = FlowDirection.LeftToRight,
            WrapContents = true,
            Padding = new Padding(0, 8, 0, 8),
        };
        actions.Controls.Add(RegisterAction(CreateButton("&Paste Clipboard", "Paste text from the clipboard", PasteClipboard)));
        actions.Controls.Add(RegisterAction(CreateButton("&Open TXT...", "Open a plain-text request file", OpenFile)));
        _analyzeButton.Text = "&Analyze";
        _analyzeButton.AutoSize = true;
        _analyzeButton.AccessibleName = "Analyze input";
        _analyzeButton.Click += async (_, _) => await AnalyzeInputAsync();
        actions.Controls.Add(RegisterAction(_analyzeButton));
        actions.Controls.Add(RegisterAction(CreateButton("&Clear", "Clear input and analysis results", ClearAll)));
        root.Controls.Add(actions, 0, 2);

        ConfigureResultsGrid();
        root.Controls.Add(_results, 0, 3);

        var details = new SplitContainer
        {
            Dock = DockStyle.Fill,
            Orientation = Orientation.Horizontal,
            SplitterDistance = 72,
            AccessibleName = "Selected record details",
        };
        details.Panel1.Controls.Add(BuildDetailGroup("Canonical 80-character record", _canonical,
            "Canonical record for the selected result"));
        details.Panel2.Controls.Add(BuildDetailGroup("Issues and review notes", _issues,
            "Issues and review notes for the selected result"));
        root.Controls.Add(details, 0, 4);

        _summary.Text = "Ready. Paste text or open a TXT file.";
        _summary.AutoSize = true;
        _summary.AccessibleName = "Analysis summary";
        _summary.AccessibleRole = AccessibleRole.StatusBar;
        _summary.Margin = new Padding(0, 8, 0, 0);
        root.Controls.Add(_summary, 0, 5);
        AcceptButton = _analyzeButton;
        return root;
    }

    private T RegisterAction<T>(T control) where T : Control
    {
        _actions.Add(control);
        return control;
    }

    private static Button CreateButton(string text, string accessibleDescription, EventHandler click)
    {
        var button = new Button { Text = text, AutoSize = true, AccessibleName = text, AccessibleDescription = accessibleDescription };
        button.Click += click;
        return button;
    }

    private static GroupBox BuildDetailGroup(string title, TextBox box, string accessibleName)
    {
        var group = new GroupBox { Text = title, Dock = DockStyle.Fill };
        box.Dock = DockStyle.Fill;
        box.ReadOnly = true;
        box.Multiline = true;
        box.ScrollBars = ScrollBars.Vertical;
        box.WordWrap = title.StartsWith("Issues", StringComparison.Ordinal);
        box.Font = title.StartsWith("Canonical", StringComparison.Ordinal)
            ? new Font(FontFamily.GenericMonospace, 10)
            : SystemFonts.MessageBoxFont;
        box.AccessibleName = accessibleName;
        group.Controls.Add(box);
        return group;
    }

    private void ConfigureResultsGrid()
    {
        _results.Dock = DockStyle.Fill;
        _results.ReadOnly = true;
        _results.AllowUserToAddRows = false;
        _results.AllowUserToDeleteRows = false;
        _results.AllowUserToOrderColumns = true;
        _results.AutoGenerateColumns = false;
        _results.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill;
        _results.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
        _results.MultiSelect = false;
        _results.AccessibleName = "Analysis results";
        _results.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "#", DataPropertyName = nameof(AnalysisRow.Number), FillWeight = 30 });
        _results.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "Status", DataPropertyName = nameof(AnalysisRow.Status), FillWeight = 85 });
        _results.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "ERP Order", DataPropertyName = nameof(AnalysisRow.ErpOrder) });
        _results.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "Effective DODAAC", DataPropertyName = nameof(AnalysisRow.EffectiveDodaac) });
        _results.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "NSN", DataPropertyName = nameof(AnalysisRow.NationalStockNumber), FillWeight = 110 });
        _results.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "Quantity", DataPropertyName = nameof(AnalysisRow.Quantity), FillWeight = 60 });
        _results.SelectionChanged += (_, _) => ShowSelectedResult();
    }

    private async Task AnalyzeInputAsync()
    {
        if (string.IsNullOrWhiteSpace(_input.Text))
        {
            MessageBox.Show(this, "Paste request text or open a TXT file before analyzing.", "No input",
                MessageBoxButtons.OK, MessageBoxIcon.Information);
            _input.Focus();
            return;
        }

        ClearAnalysis();
        try
        {
            SetBusy(true);
            SetStatus("Analyzing input...");
            var inputSnapshot = _input.Text;
            var rows = await Task.Run(() => _analysis.Analyze(inputSnapshot));
            _results.DataSource = rows.ToList();
            var valid = rows.Count(row => row.Status == "VALID");
            var review = rows.Count(row => row.Status == "REQUIRES_REVIEW");
            var rejected = rows.Count(row => row.Status == "REJECTED");
            SetStatus($"Records: {rows.Count}   Valid: {valid}   Requires review: {review}   Rejected: {rejected}");
            if (rows.Count == 0)
            {
                _canonical.Clear();
                _issues.Text = "No MILSTRIP records were detected.";
            }
        }
        catch (Exception)
        {
            // Request content must not be written to logs or diagnostic files.
            ClearAnalysis();
            MessageBox.Show(this, "The input could not be analyzed. Clear it and try again, or contact support.",
                "Analysis failed", MessageBoxButtons.OK, MessageBoxIcon.Error);
            SetStatus("Analysis failed. No file was created or uploaded.");
        }
        finally
        {
            SetBusy(false);
        }
    }

    private void PasteClipboard(object? sender, EventArgs e)
    {
        string text;
        try
        {
            if (!Clipboard.ContainsText())
            {
                MessageBox.Show(this, "The clipboard does not contain text.", "Nothing to paste",
                    MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            text = Clipboard.GetText(TextDataFormat.UnicodeText);
        }
        catch (ExternalException)
        {
            MessageBox.Show(this, "The clipboard is busy. Wait a moment and try again.", "Clipboard unavailable",
                MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        if (text.Length > MaximumInputCharacters)
        {
            ShowInputTooLarge();
            return;
        }
        SetInput(text);
    }

    private void OpenFile(object? sender, EventArgs e)
    {
        using var dialog = new OpenFileDialog
        {
            Title = "Open request text",
            Filter = "Text files (*.txt)|*.txt",
            CheckFileExists = true,
            Multiselect = false,
            RestoreDirectory = true,
        };
        if (dialog.ShowDialog(this) == DialogResult.OK)
        {
            LoadTextFile(dialog.FileName);
        }
    }

    private void OnDragEnter(object? sender, DragEventArgs e)
    {
        e.Effect = TryGetSingleTxtPath(e.Data, out _) ? DragDropEffects.Copy : DragDropEffects.None;
    }

    private void OnDragDrop(object? sender, DragEventArgs e)
    {
        if (TryGetSingleTxtPath(e.Data, out var path))
        {
            LoadTextFile(path);
        }
    }

    private static bool TryGetSingleTxtPath(IDataObject? data, out string path)
    {
        path = string.Empty;
        if (data?.GetData(DataFormats.FileDrop) is not string[] { Length: 1 } paths ||
            !string.Equals(Path.GetExtension(paths[0]), ".txt", StringComparison.OrdinalIgnoreCase))
        {
            return false;
        }
        path = paths[0];
        return true;
    }

    private void LoadTextFile(string path)
    {
        try
        {
            using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
            if (stream.Length > MaximumInputCharacters * 4L)
            {
                SetInput(string.Empty);
                ShowInputTooLarge();
                return;
            }
            using var reader = new StreamReader(stream, detectEncodingFromByteOrderMarks: true);
            var buffer = new char[MaximumInputCharacters + 1];
            var count = 0;
            while (count < buffer.Length)
            {
                var read = reader.Read(buffer, count, buffer.Length - count);
                if (read == 0) break;
                count += read;
            }
            if (count > MaximumInputCharacters || reader.Peek() >= 0)
            {
                SetInput(string.Empty);
                ShowInputTooLarge();
                return;
            }
            SetInput(new string(buffer, 0, count));
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            SetInput(string.Empty);
            MessageBox.Show(this, "The TXT file could not be opened. Check access and try again.", "Open failed",
                MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private void SetInput(string text)
    {
        if (text.Length > MaximumInputCharacters)
        {
            ShowInputTooLarge();
            return;
        }
        _changingInput = true;
        _input.Text = text;
        _lastAcceptedInput = text;
        _changingInput = false;
        ClearAnalysis();
        SetStatus(string.IsNullOrEmpty(text) ? "Ready. Paste text or open a TXT file." : "Input loaded. Select Analyze.");
        _input.Focus();
    }

    private void OnInputChanged(object? sender, EventArgs e)
    {
        if (_changingInput) return;
        if (_input.Text.Length > MaximumInputCharacters)
        {
            _changingInput = true;
            _input.Text = _lastAcceptedInput;
            _input.SelectionStart = _input.TextLength;
            _changingInput = false;
            ShowInputTooLarge();
            return;
        }
        _lastAcceptedInput = _input.Text;
        ClearAnalysis();
        SetStatus(string.IsNullOrEmpty(_input.Text)
            ? "Ready. Paste text or open a TXT file."
            : "Input changed. Select Analyze.");
    }

    private void ShowInputTooLarge() => MessageBox.Show(this,
        $"Input is limited to {MaximumInputCharacters:N0} characters. Split the request into smaller TXT files.",
        "Input too large", MessageBoxButtons.OK, MessageBoxIcon.Warning);

    private void ShowSelectedResult()
    {
        if (_results.CurrentRow?.DataBoundItem is not AnalysisRow row)
        {
            return;
        }
        _canonical.Text = row.Canonical;
        _issues.Text = row.Issues.Count == 0 ? "No issues." : string.Join(Environment.NewLine, row.Issues.Select(issue => $"• {issue}"));
    }

    private void ClearAll(object? sender, EventArgs e)
    {
        SetInput(string.Empty);
        _input.Focus();
    }

    private void ClearAnalysis()
    {
        _results.DataSource = null;
        _canonical.Clear();
        _issues.Clear();
    }

    private void SetBusy(bool busy)
    {
        UseWaitCursor = busy;
        _input.Enabled = !busy;
        foreach (var action in _actions) action.Enabled = !busy;
    }

    private void SetStatus(string text)
    {
        _summary.Text = text;
        _summary.AccessibleDescription = text;
    }
}
