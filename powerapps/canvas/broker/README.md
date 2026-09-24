# Broker Canvas source

Status: generated source; requires native Power Apps compilation and acceptance.
The four files directly under `powerapps/canvas` remain the pre-cutover source.

Run `.venv\Scripts\python.exe scripts/build_broker_canvas.py` to rebuild.
Use `--check` to check reproducibility without changing files.

Each environment directory contains six control files, `App.Formulas`,
`App.OnStart`, and the screen events listed in `screen-events.json`.
The Stage variant references only `MILSTRIPStageBroker`; Prod references only
`MILSTRIPProdBroker`. Bind that flow before native compilation. The image resource
`milstrip-app` and the four original screen names are retained.

Intake, results, review and history retain receipt, pagination and review-command
retry behavior. The new Configuration and Users navigation depends on the
verified user's capabilities and remains available when the business database
is unavailable. Connection strings use a blank password input and are never
read back. Configuration and access commands retain their command ID in memory
for retries and recorded-outcome lookup; closing the app clears that memory.

Before cutover, verify both variants in Studio: sign-in, disabled-Prod
administration, typed results and issue rendering, receipt after commit, review
retry, pending sharing, protected owners, configuration Save/Test/Apply and an
unknown-result recovery. Source tests do not replace native compilation or
tenant acceptance.
