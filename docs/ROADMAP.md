# Roadmap

Details live in their owning specification/design. This file only defines
sequence, outcome and gate.

| Phase | Outcome | Status / gate |
|---|---|---|
| 1 | Deterministic parser, validation, canonical 80-character record, CLI/`.bat` | **ACCEPTED 2026-08-14**; 46 regression tests |
| 1.5 | Additional evidence-backed repair rules | Deferred until more real anomalies provide a unique safe interpretation |
| 2A | Native Windows app: paste/`.txt`, analyze and guided review | **CODE ACCEPTED:** Windows packaging/accessibility/EDR release gate remains |
| 2B | Official 76-field pipe-delimited `.txt` | Layout/extension confirmed; **blocked:** field-source map, byte edge cases and golden/ACK |
| 2C | Controlled Rainbow transfer | **Blocked:** protocol, credentials, test endpoint, retry/duplicate/ACK contract |
| 3 | Application database and approved reference validation | **Blocked:** owner-supplied layout and database inputs |
| 4 | Private Edge/Chrome/Brave extension | Approved as deferred; after stable parser/file contract |
| 5 | Direct Freshservice/Outlook intake | Deferred; requires sanitized samples, authentication and privacy design |

## Phase 2 release rule

Local analysis, review-file creation and confirmed Rainbow delivery are three
different states. The UI must never present one as another.

Production release requires:

1. deterministic/golden and failure-path tests;
2. signed Windows package built from a clean tagged commit;
3. install/upgrade/uninstall and OneDrive Desktop tests on managed Windows;
4. IT/EDR validation;
5. independent Full audit; and
6. explicit HOC GO.

## End boundary

The application's future responsibility ends at the acknowledgement defined by
the Rainbow transfer contract. Everything after that handoff remains the
existing operational process.
