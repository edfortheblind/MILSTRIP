# MILSTRIP Intake Tool — Windows Operator SOP

**Scope clarification (2026-09-23):** this file describes the accepted CLI tool.
For the implemented Power Apps draft, use the [current canvas operator SOP and
chart](operations-guide/guide.md#4-end-user-sop-current-development-app).
The [visual package](operations-guide/index.html) separates current behavior from
the proposed published Phase 2 Azure SQL / PostgreSQL periods.

**Current release:** Phase 1 local validation only

**Future release:** Phase 2 Rainbow CSV creation and secure transfer

**Audience:** first-time Windows operators and support personnel

## 1. Read this first

This project was developed in a GitHub Codespace. A Codespace is a remote
computer hosted by GitHub. Files visible there do not automatically exist on
the operator's Windows computer.

Before the tool can run on Windows, the complete approved project must be:

1. committed and pushed from the Codespace to GitHub by the release manager;
2. downloaded or cloned onto the Windows computer; and
3. run from the real downloaded folder—not from `C:\Users\<username>` or a
   sample path such as `C:\path\to\MILSTRIP`.

The current launcher validates input and displays a report. It does **not**
create a Rainbow CSV, upload a file, use a database or send anything over the
network. Diagnostic JSON is not a Rainbow deliverable.

## 2. Responsibilities

**Release manager:** run tests, obtain approval, commit and push the approved
files, and provide the exact release/tag or Git commit ID. Do not distribute an
unpublished Codespace working folder.

**Operator:** download the approved version, prepare input, run
`run_milstrip.bat`, review every result and escalate exceptions. The operator
does not edit Python source code.

## 3. Required handoff information

The release manager must provide:

- repository: `https://github.com/edfortheblind/MILSTRIP`;
- approved release/tag or full commit ID;
- confirmation that the operator can access the private repository;
- sanitized known-valid and known-rejected test files;
- internal support contact; and
- confirmation of whether the release is Phase 1 only or includes Phase 2.

## 4. Windows requirements

- Windows 10 or 11 and Python 3.10 or later.
- Repository access or an approved release ZIP.
- A writable folder such as `Documents\MILSTRIP`; do not use `Program Files`.
- Phase 1 needs no database driver, FTP client, GitHub CLI or third-party
  Python package.

## 5. Install and verify Python

1. Press the Windows key, type `cmd`, and press **Enter**.
2. Run:

   ```bat
   python --version
   ```

3. If it reports Python 3.10 or later, continue to Section 6.
4. Otherwise install Python from <https://www.python.org/downloads/>.
5. If asked `Add commands directory to your PATH now? [y/N]`, type `y` and
   press **Enter**.
6. Close all terminals, open a new Command Prompt and rerun
   `python --version`.

Running `python` without `--version` opens the Python prompt. Type `exit()` and
press **Enter** to leave it.

## 6. Copy the application from GitHub to Windows

Use one method only. Method A is recommended. GitHub CLI is optional.

### Method A — Approved ZIP (recommended)

1. Obtain the approved ZIP from the release manager, or sign in at
   <https://github.com/edfortheblind/MILSTRIP> with an authorized account.
2. On GitHub select **Code** → **Download ZIP**.
3. In Downloads, right-click the ZIP and select **Extract All**.
4. Extract it under `C:\Users\<your-user>\Documents\MILSTRIP`.
5. GitHub may name the extracted folder `MILSTRIP-main`; this is normal.
6. Open folders until these items are visible together:

   ```text
   run_milstrip.bat
   README.md
   milstrip\
   docs\
   tests\
   ```

If they are not together, the wrong folder is open or the ZIP is incomplete.
Stop and contact support.

### Method B — `git clone`

Use this only if Git is installed.

```bat
git --version
cd /d "%USERPROFILE%\Documents"
git clone https://github.com/edfortheblind/MILSTRIP.git
cd /d "%USERPROFILE%\Documents\MILSTRIP"
git rev-parse HEAD
```

If Git is unavailable, use Method A or install Git for Windows from
<https://git-scm.com/download/win>. Authenticate in the browser if prompted;
never put a password or token in the command. The final commit ID must match
the approved ID supplied by the release manager.

### Method C — GitHub CLI from Command Prompt

This is the complete CMD flow for connecting to GitHub, cloning into the
recommended folder and running the included smoke test.

1. Open Command Prompt and verify the required commands:

   ```bat
   git --version
   gh --version
   ```

2. If either command is missing, install it, close Command Prompt and open a
   new one:

   ```bat
   winget install --id Git.Git --exact
   winget install --id GitHub.cli --exact
   ```

3. Authenticate through the browser:

   ```bat
   gh auth login --web --git-protocol https
   gh auth status
   ```

4. Clone and enter the application folder:

   ```bat
   cd /d "%USERPROFILE%\Documents"
   gh repo clone edfortheblind/MILSTRIP MILSTRIP
   cd /d "%USERPROFILE%\Documents\MILSTRIP"
   ```

5. Verify the folder and approved commit:

   ```bat
   dir run_milstrip.bat
   dir milstrip
   git rev-parse HEAD
   ```

6. Run the included smoke test:

   ```bat
   run_milstrip.bat samples\known_valid.txt
   ```

The result must show one detected record, `VALID`, zero rejected records and
`Phase 1 only: no Rainbow CSV was created or uploaded.`

### Method D — GitHub CLI from PowerShell

This is the equivalent complete PowerShell flow.

1. Open PowerShell and verify/install Git and GitHub CLI as described in Method
   C. Then close and reopen PowerShell.
2. Authenticate:

   ```powershell
   gh auth login --web --git-protocol https
   gh auth status
   ```

3. Clone into Documents and enter the repository:

   ```powershell
   Set-Location "$HOME\Documents"
   gh repo clone edfortheblind/MILSTRIP MILSTRIP
   Set-Location "$HOME\Documents\MILSTRIP"
   ```

4. Verify the folder and approved commit:

   ```powershell
   Get-Item .\run_milstrip.bat
   Get-Item .\milstrip
   git rev-parse HEAD
   ```

5. Run the included smoke test and capture its exit code:

   ```powershell
   & .\run_milstrip.bat .\samples\known_valid.txt
   $LASTEXITCODE
   ```

The expected exit code is `0`. The displayed result requirements are the same
as Method C.

For both methods, choose GitHub.com, HTTPS and browser authentication. Never
place a token in this repository, a ticket, an input file or the `.bat` file.
If the target `MILSTRIP` folder already exists, do not clone over it; follow
Section 16 or ask support which copy is approved.

## 7. Open Command Prompt in the correct folder

1. In File Explorer, open the folder containing `run_milstrip.bat`.
2. Click the address bar, type `cmd`, and press **Enter**.
3. Verify:

   ```bat
   dir run_milstrip.bat
   dir milstrip
   ```

Both must succeed. Never type the literal example
`cd C:\path\to\MILSTRIP`; it is a placeholder, not a real path.

## 8. Prepare the input

1. Preserve the original email or ticket.
2. Paste the complete request into Notepad. Do not add, delete or guess
   MILSTRIP characters to make it pass.
3. Select **File** → **Save As**.
4. Name it `request.txt`, select **All files**, and choose **UTF-8** encoding.
5. For the first run, save it beside `run_milstrip.bat`.

Screenshots, images and PDFs are not direct input. Export or transcribe the
actual text while preserving every character.

## 9. Run it — recommended method

1. In File Explorer, drag `request.txt` onto `run_milstrip.bat`.
2. Keep the Command Prompt open.
3. Confirm it shows `Records detected`, `Valid`, `Requires review` and
   `Rejected`.
4. Review every numbered record, not only the totals.
5. Current Phase 1 must also display:

   ```text
   Phase 1 only: no Rainbow CSV was created or uploaded.
   ```

6. Record the result, then press any key to close the window.

Alternatively, from the correct folder run:

```bat
run_milstrip.bat request.txt
```

For an input elsewhere, use its real quoted path:

```bat
run_milstrip.bat "C:\Users\ed.lopez\Documents\Requests\request.txt"
```

## 10. Interpret the result

- **`VALID`:** passed local structural validation and has an 80-character
  canonical value. It was not database-validated or sent to Rainbow.
- **`REQUIRES_REVIEW`:** a person must resolve every warning by comparing the
  received and canonical values. This is not automatic approval.
- **`REJECTED`:** must not proceed. Correct it only from an authoritative
  source. Never guess or remove an NSN digit, DODAAC, quantity, priority,
  condition code or other character.

## 11. Exit codes

| Code | Meaning | Required action |
|---:|---|---|
| `0` | Processed; none rejected | Still resolve every `REQUIRES_REVIEW` |
| `1` | One or more rejected | Correct from authoritative data and rerun |
| `2` | Input failure | Check file, encoding, contents and path |
| `9` | Python unavailable | Repeat Section 5 in a new terminal |

## 12. Common problems

### `The system cannot find the path specified`

A sample path was typed or the folder is elsewhere. Follow Section 7; do not
guess the path.

### `'run_milstrip.bat' is not recognized`

The terminal is not in the application folder. Follow Section 7 and verify
with `dir run_milstrip.bat`.

### Python is not found

Repeat Section 5 and open a new terminal after installation.

### GitHub says repository not found or access denied

Use the authorized GitHub account and ask the release manager to confirm
access. Do not create or share access tokens in chat or email.

### No candidate is detected

Confirm the file is not empty and contains actual text beginning with an A2_,
A5_ or AF6-like DIC. Images are not parsed.

### The record exceeds 80 characters or has an invalid identifier

Do not delete characters. Verify the source and obtain corrected data from
DLA/source personnel.

### Dots or ellipses appear in the record

Never replace all punctuation globally. The tool only permits its
evidence-backed case and marks it for review.

## 13. Diagnostic JSON — developers only

```bat
python -m milstrip.cli request.txt --json
```

This is not the Rainbow CSV. Never rename it, convert it manually or upload it.

## 14. Future Phase 2 — not active

After the official contract, tests, audit and owner GO, the launcher will
validate eligible records, create the exact Rainbow CSV without silent
overwrite, show its path and row count, transfer it through the approved secure
protocol, and distinguish local creation from confirmed remote delivery.

Until a released launcher explicitly reports those steps, stop after Phase 1.
Do not construct a guessed CSV or store FTP credentials in this repository.

## 15. New-workstation acceptance

Support must record Windows version, `python --version`, approved commit ID,
tester and date, then verify:

1. `samples\known_valid.txt` → exit `0`, `VALID` and canonical length 80;
2. known-rejected input → exit `1` and no canonical;
3. empty input → exit `2` and `MIL-INTAKE-001`;
4. missing file → exit `2` and `MIL-INTAKE-002`; and
5. no CSV, database write or network transfer occurred in Phase 1.

The workstation is not accepted until all checks match.

## 16. Update an existing Git clone

Only support or a trained operator should update it:

```bat
cd /d "%USERPROFILE%\Documents\MILSTRIP"
git status --short
```

If output appears, stop; do not discard files. If it is empty:

```bat
git pull --ff-only
git rev-parse HEAD
```

Verify the approved commit ID. For ZIP installations, extract a newly approved
ZIP into a new versioned folder; do not overwrite the working folder.

## 17. Support information

Provide the release/tag or commit ID, Windows/Python versions, command, exit
code, issue codes, installation method, and sanitized input shape. Never send
credentials, tokens, private keys or unnecessary personal information.
