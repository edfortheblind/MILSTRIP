# Pending Decisions

There are no owner decisions blocking Phase 2A development.

## Confirmed 2026-08-14

- Native C# WinForms/.NET 10 application.
- Paste plus `.txt` open/drag-and-drop intake.
- No provisional review CSV.
- Default output location: Windows/OneDrive Desktop with Browse.
- Private Chromium extension remains deferred to Phase 4.
- Initial development has no installer/signing approval and no authentication.
- Azure/Entra SSO may be evaluated when a later phase requires identity; it
  does not replace application code signing or IT/EDR approval.
- Shawn confirmed that the supplied 76-field pipe-delimited artifact is the
  file layout and that `.txt` is the correct operational extension.

## Deferred — blocks Phase 2B output, not Phase 2A UI

Before generating the operational `.txt`, obtain:

1. names and source mapping for all 76 fields, especially enriched
   address/contact values not present in the 80-character MILSTRIP;
2. confirmation of byte edge cases: encoding, final CRLF, significant spaces,
   quoting/escape rules and invalid characters; and
3. one sanitized accepted file plus its Rainbow result/ACK.

## Deferred — later phases

- Installer format, code-signing owner, IT deployment and managed-endpoint EDR
  validation.
- Whether Azure/Entra SSO is needed and what resource it protects.
- Rainbow transfer protocol, endpoint, credentials, paths, retry, duplicate
  and acknowledgement rules.
- Application database layout, platform, retention and reference contracts.
- Freshservice/Outlook authentication and sanitized samples.
