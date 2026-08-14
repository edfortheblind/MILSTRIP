# MILSTRIP Review Toolkit — Pilot User SOP

## 1. What this pilot does

The Windows application lets an operator:

1. paste request/email text or open a `.txt` file;
2. analyze MILSTRIP records;
3. review `VALID`, `REQUIRES_REVIEW` and `REJECTED` results; and
4. view the canonical 80-character record and issues.

This Phase 2A pilot does **not** create the 76-field Rainbow `.txt`, upload a
file, connect to a database or read an Outlook mailbox.

## 2. Download

1. Sign in to GitHub with an account authorized for the private MILSTRIP repo.
2. Open <https://github.com/edfortheblind/MILSTRIP/releases>.
3. Open the approved release marked **Pre-release**.
4. Under **Assets**, download:

   ```text
   MILSTRIP-Setup-<version>.exe
   ```

5. Do not download **Source code**. Operators do not need the repository,
   Python, Git, GitHub CLI, Visual Studio or the .NET SDK.

The pilot installer is unsigned. Windows SmartScreen or company security tools
may warn, block or quarantine it. If that happens, stop and contact IT. Never
disable antivirus, EDR or SmartScreen and never create your own exclusion.

## 3. Install

1. Double-click the downloaded `MILSTRIP-Setup-<version>.exe`.
2. Confirm the installer name is **MILSTRIP Review Toolkit**.
3. Keep the default installation folder.
4. Optionally select **Create a desktop shortcut**.
5. Select **Install**.
6. Select **Finish** to open the application.

The pilot installs only for the current Windows user and should not require
administrator rights.

## 4. Analyze a request

### Paste text

1. Copy the complete request/email text.
2. Open **MILSTRIP Review Toolkit** from Start Menu or its Desktop shortcut.
3. Select **Paste Clipboard**.
4. Select **Analyze**.

### Open a text file

1. Save the original request as a UTF-8 `.txt` file.
2. Select **Open TXT** and choose the file, or drag it onto the application.
3. Select **Analyze**.

Do not remove, insert or guess characters to make a request pass. Screenshots,
PDFs, `.msg` and `.eml` files are not supported by this pilot.

## 5. Review results

Review every row, not only the totals.

- **VALID:** passed local structural validation. It was not database-validated
  or sent to Rainbow.
- **REQUIRES_REVIEW:** a person must resolve every warning before the record
  can proceed.
- **REJECTED:** must not proceed. Obtain corrected information from an
  authoritative source and analyze it again.

Select a row to see its canonical record and issue details. Never guess or
silently remove an NSN digit, DODAAC, quantity, priority, condition code or
other character.

The red banner must always say:

```text
Phase 2A review only — no file created or uploaded
```

If the application implies that it created, delivered or uploaded a file,
stop using it and contact support; that is not approved Phase 2A behavior.

## 6. Clear sensitive content

After recording the approved result, select **Clear** before processing another
request or leaving the workstation. The pilot has no telemetry, payload log,
recent-file history, database or network connection.

Follow the organization's normal handling and retention rules for the original
email and any screenshots or copied results.

## 7. Troubleshooting

### Windows or EDR blocks the installer

Stop and contact IT/support. Provide the release version and exact warning.
Do not bypass the warning or disable security controls.

### The clipboard is busy

Wait a moment and select **Paste Clipboard** again.

### No records are detected

Confirm that the input contains actual text beginning with an A2_, A5_ or
AF6-like DIC. Images are not parsed.

### Input is too large

Split it into smaller `.txt` files without splitting an individual MILSTRIP
record.

### A record is over 80 characters or has an invalid identifier

Do not delete characters. Verify the source and request corrected data.

### The application does not open or closes unexpectedly

Record the release version, Windows version and displayed message. Do not send
the raw request unless the approved support process allows it.

## 8. Uninstall

1. Open Windows **Settings** → **Apps** → **Installed apps**.
2. Find **MILSTRIP Review Toolkit**.
3. Select **Uninstall** and confirm.

## 9. Support information

Provide:

- installer/release version;
- Windows version;
- status or MILSTRIP issue codes;
- whether input was pasted, opened or dragged; and
- exact installer/application error message.

Never send passwords, tokens, private keys or unnecessary personal data.
