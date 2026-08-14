# Windows Desktop Toolkit — Architecture Proposal

**Status:** Phase 2A code accepted; Windows release gate pending

**Profile:** Full/high-risk because the future output enters an operational
supply-chain workflow

## Outcome

Replace the developer-oriented `.bat` workflow with an installable Windows
application that a non-technical operator can open, paste or select request
text, analyze, review and export without Python, Git or GitHub knowledge.

The application can be designed and coded from Codespaces, but its production
installer cannot be accepted until it is built, signed and tested on managed
Windows endpoints under the organization's actual Defender/EDR policies.
No implementation can guarantee that every antivirus product will accept an
executable. Trust comes from conventional packaging, Authenticode signing,
stable publisher identity and IT-managed deployment/allow policy.

## Approved architecture

Use a native C# WinForms application on .NET 10 LTS, distributed as a signed
MSIX through the organization-approved software channel.

Reasons:

- no Python, Git or GitHub CLI on operator workstations;
- conventional Windows process and packaging model;
- accessible keyboard and screen-reader properties;
- clean install, upgrade and uninstall contract;
- a stable signed publisher identity that IT can trust by policy;
- less endpoint friction than an unsigned self-extracting Python executable.

The cost is a controlled port of the deterministic Python parser. Shared
golden fixtures and byte-for-byte canonical parity tests must run against both
implementations until the native parser is proven equivalent. Python remains
the reference implementation during that transition.

The Python packaging alternative was not selected.

## Initial user experience

1. Open **MILSTRIP Intake Tool** from the Start menu.
2. Paste request/email text, drag a `.txt` file, or select a `.txt` file.
3. Select **Analyze**.
4. Review a grid of `VALID`, `REQUIRES_REVIEW` and `REJECTED` records.
5. Select a record to see its canonical value and plain-English issues.
6. Phase 2A stops after review; output remains disabled until Phase 2B.

Direct Outlook/mailbox access, `.msg`, `.eml`, FTP and database access are
separate adapters and are not part of the initial desktop release.

## CSV boundary

The official Rainbow CSV remains blocked by its missing layout and accepted
sample. Until those arrive, the only safe optional export is an explicitly
non-production review artifact such as:

```text
MILSTRIP_REVIEW_NOT_FOR_RAINBOW_20260814T153000Z_AB12.csv
```

The owner declined a provisional review CSV. Phase 2A creates no output file.
Phase 2B will add the confirmed 76-field pipe-delimited `.txt` only after its
field-source map, byte edge cases and accepted golden/ACK are supplied.

## Security and privacy defaults

- no telemetry, network calls, payload logs or recent-file history;
- clipboard/request content remains in memory unless the operator explicitly
  creates an output;
- bounded text input; attachments, links and remote content are never opened;
- Windows Known Folder API resolves redirected/OneDrive Desktop locations;
- safe constant filenames with UTC timestamp and random suffix;
- no silent overwrite, partial final file or automatic resend;
- no credentials embedded in source, installer or command line;
- signed, timestamped package built from a tagged clean commit;
- IT validates Defender, EDR, AppLocker/WDAC, install, upgrade and uninstall.

## Release gates

1. UI/controller and parser parity tests pass.
2. Input, Unicode, size, multi-record and failure-path tests pass.
3. Windows 10/11 testing covers standard user, redirected OneDrive Desktop,
   non-ASCII/long paths and unwritable locations.
4. Signed package passes install, launch, upgrade, rollback and uninstall on a
   clean managed endpoint without Python/Git/GitHub CLI.
5. IT approves publisher trust and actual EDR behavior. Users are never told
   to disable antivirus or create their own exclusions.
6. Independent Full audit and explicit HOC production GO.

## Later browser extension — Phase 4 feasibility

A private Chromium extension for Edge, Chrome and Brave is feasible for a
user-invoked paste/current-page → analyze → review → download workflow:

- Manifest V3 with all executable code packaged locally;
- `activeTab` + `scripting` only for an explicit current-page action, plus
  `downloads`; no `<all_urls>` or persistent mailbox scraping;
- paste remains the stable primary input because Outlook/Gmail DOM extraction
  is brittle across UI changes;
- port the deterministic parser to TypeScript (or a small WASM core) and require
  golden/failure parity against the reference implementation;
- keep content in memory, render with safe text APIs and never retain mail or
  telemetry by default;
- use browser `saveAs` or an enterprise-configured download directory: the
  downloads API cannot choose an arbitrary absolute Desktop path;
- do not implement direct FTP in the extension. Prefer an authenticated IT
  HTTPS gateway later; native messaging would reintroduce a signed installed
  companion and extension-ID policy.

Chrome Web Store `Private` can restrict a pilot to trusted testers/groups;
`Unlisted` is not private. Edge `Hidden` is also link-hidden rather than access
controlled, so enterprise policy deployment is the stronger path. Brave is
largely Chromium-compatible but requires its own certification matrix.

Official references:

- <https://developer.chrome.com/docs/extensions/develop/migrate/what-is-mv3>
- <https://developer.chrome.com/docs/extensions/develop/concepts/activeTab>
- <https://developer.chrome.com/docs/extensions/reference/api/downloads>
- <https://developer.chrome.com/docs/extensions/how-to/distribute>
- <https://developer.chrome.com/docs/webstore/cws-dashboard-distribution>
- <https://learn.microsoft.com/en-us/microsoft-edge/extensions/publish/publish-extension>
- <https://learn.microsoft.com/en-us/deployedge/microsoft-edge-manage-extensions-webstore>
- <https://support.brave.app/hc/en-us/articles/360017909112-How-can-I-add-extensions-to-Brave>
