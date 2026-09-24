# Six-screen Canvas source inspection

Status: **the assembler remains inspection-only and not deployable**. Separate
native Studio implementation is now verified in the saved Stage and Prod draft
exports described below. This comparison neither publishes the drafts nor
activates API security enforcement.

`scripts/assemble_broker_canvas.py` copies an exported PAC `SourceCode` baseline
into a new, empty directory. In the YAML, it replaces six screen child lists,
their `OnVisible` handlers, `App.OnStart`, `App.StartScreen` and the
`AppEnvironment` named formula. Other named formulas, app properties, native
control versions, resource containers and media are retained. The unused
`Screen1` scaffold is omitted only when it contains no behavior; other unexpected
screens cause a refusal.

Control versions come from the native source. A new Classic CheckBox must have
native template evidence: either the baseline already contains that control, or
`--checkbox-metadata` points to a native MSAPP/MSAPR with its template. The script
checks the template's identifier and matching JSON/XML version. It does not invent
resource IDs or flow bindings.

Use a baseline exported after the matching broker flow and a Classic CheckBox
have been added in Studio to inspect those native dependencies. This does not
turn the assembled YAML into an executable replacement. Stage and Prod baselines
and resources cannot be interchanged.

```powershell
.\.venv\Scripts\python.exe scripts\assemble_broker_canvas.py `
  --baseline "$env:LOCALAPPDATA\MILSTRIP\ui\stage-bound-baseline" `
  --profile stage `
  --output "$env:LOCALAPPDATA\MILSTRIP\ui\stage-broker-inspection"
```

The output directory must be new or empty and cannot overlap its baseline.
Repeat for Prod using its native baseline and `--profile prod`. Store native
exports and inspection copies privately; they retain the original connection
metadata. Every generated directory includes `INSPECTION_ONLY.txt`, and its
evidence records `deployable: false`.

## Native implementation path

Insert the generated `controls.yaml` into each existing app through Studio, then
set its App and screen formulas there. Apply **all six** `screen-events.json`
entries: Intake, Results, Review and History explicitly use `OnVisible = false`
to clear their old direct-connector handlers; both administration screens use
their generated handlers. Replacing child controls alone does not clear screen
events. Remove the direct connector from the
app's Data sources and retain only that app's broker dependency. Save, export
and inspect the native `LocalConnectionReferences` and `DataSources` to confirm
the matching broker binding and absence of the direct connector. Verify cloud
App IDs against the actual Studio/deployment target; a native `Properties.Id`
is not evidence of cloud App ID preservation.

Native App Checker and runtime acceptance must cover startup, allowed/denied
users, configuration recovery, sharing retries, and successful and failed
business operations before publication or API enforcement cutover.

## Current native evidence — September 24

The private `MILSTRIP-Stage-20260924-admin-draft-v2.msapp` and
`MILSTRIP-Prod-20260924-admin-draft-v2.msapp` exports were inspected directly,
including their executable `Controls/` JSON. Each matches all **679 generated
properties across 81 controls**, including 36 behavior handlers, all six screen
events and the three App properties. Comparison ignores formula whitespace
outside quoted strings; it preserves string contents. The gallery item labels
are stored on native `galleryTemplate` children and also match.

Both exports contain the four latest fixes: the protected Owner displays `OWNER`
in the disabled role dropdown, editable users retain only `OPERATOR`/`ADMIN`,
and entry into either administration screen replaces unrelated messages while
preserving pending commands and drafts. Twenty focused Canvas/assembly checks
passed after those changes.

Each app has only its matching broker as a service data source. The native
connection metadata contains that workflow, and the direct API connector is
absent from executable formulas and connection/data-source metadata. These
checks establish saved draft contents, not the cloud App ID or published version.

| Export | SHA-256 |
| --- | --- |
| Stage v2 | `5c19b5284245f5f5eeadad4b26293a225a56a41d02ba9fea8fecb4d0bd2897df` |
| Prod v2 | `bb40a74aab3f8cf643ca94ec54c8b45502026bf3eb30495cdbb840faaab24a82` |

The contemporaneous native flow readbacks report both brokers `Started`, with
definition modification times of 18:16:55 and 18:17:02 local. Both match the
reviewed diagnostic package: eight protected diagnostic Compose actions and
39 protected broker calls per flow, with matching connection references and
runtime sources. The sole definition normalization is the platform-generated
invoker authentication expression. Identity, sharing, pagination and pacing
guards match the package. This is activation/configuration evidence, not a
successful sharing or business-operation test; later flow revisions need their
own readback.

The exported App Checker reports two literal-predicate findings and 66
accessibility findings. `Properties.json` still records `ParserErrorCount=1`
and `BindingErrorCount=0`, although the SARIF has no parser-error finding.
The metadata discrepancy remains unresolved; these exports do not establish a
zero parser-error count. See the [accessibility evidence](CANVAS_ACCESSIBILITY_2026-09-24.md)
for the remaining native keyboard and screen-reader checks.

## Earlier inspection evidence and limits

On September 24, PAC 2.12.2 packed and unpacked both variants from the original
Stage baseline. Each contained six YAML screens and 81 controls. Parsed YAML was
equal after the roundtrip, and all nine native reference/media entries checked
were byte-identical. The source assembler retained the entire MSAPR container
byte-for-byte. Thirteen focused Canvas/assembly tests passed.
The subsequent default-safe full suite passed **311 tests**, with **73 database
opt-in tests skipped** and two upstream deprecation warnings, in 60.84 seconds.
This run did not connect to or write the live database.

That baseline had no broker flow data source or checkbox. The packaging probes
used checkbox version **2.0.1**, read from the actual checkbox template in
Microsoft's [AccountPlanReviewerMaster test app](https://github.com/microsoft/PowerApps-Tooling/blob/master/src/PAModelTests/Apps/AccountPlanReviewerMaster.msapp).
This is evidence for that version, not a claim that it is the current Studio
default. The richer native Studio export takes precedence.

The earlier Stage broker baseline export was unpacked read-only. It contained
native `Classic/CheckBox@2.1.0`, the correct Stage broker workflow, and a `Run`
operation with required string arguments `operation` and `payload_json`.
At that snapshot, `MILSTRIPLocalDevAPI` remained in both native data-source and
connection metadata, and the six-screen implementation was incomplete. The v2
exports above supersede that content snapshot; the assembler limitation remains.

Inspection of the probes confirmed that native `Controls/` and connector
resources still contain the original app. The check for direct connector calls
scans only the replacement YAML; it does not remove native data-source entries.
The probe MSAPP files are not deployment candidates. Their successful roundtrip
neither implements nor type-checks the replacement app.

Microsoft documents [PAC SourceCode pack/unpack](https://learn.microsoft.com/en-us/power-platform/developer/cli/reference/canvas)
as deprecated preview tooling and requires Studio validation of packed sources.
The [official YAML schema](https://github.com/microsoft/PowerApps-Tooling/blob/master/schemas/pa-yaml/v3.0/pa.schema.yaml)
defines the control identifier/version syntax; packaging success alone is not
native application acceptance.
