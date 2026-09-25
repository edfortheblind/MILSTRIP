"""Generated Canvas contract checks; native Studio compilation is a separate gate."""
import importlib.util
import json
from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("broker_canvas", ROOT / "scripts/build_broker_canvas.py")
CANVAS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CANVAS)


def props(files, profile, screen, name):
    controls = yaml.safe_load(files[f"{profile}/{screen}.controls.yaml"])
    return next(item[name]["Properties"] for item in controls if name in item)


def test_generated_sources_are_current_and_have_one_environment_flow_each():
    files = CANVAS.render()
    for relative, expected in files.items():
        assert (CANVAS.OUTPUT / relative).read_text(encoding="utf-8") == expected
    manifest = json.loads(files["manifest.json"])
    assert len(manifest["screens"]) == 6
    for profile in ("stage", "prod"):
        combined = "\n".join(value for path, value in files.items() if path.startswith(profile + "/"))
        assert set(re.findall(r"(MILSTRIP\w+)\.Run\(", combined)) == {"MILSTRIP" + profile.title() + "Broker"}
        assert "MILSTRIPLocalDevAPI" not in combined and "__FLOW__" not in combined
        assert "RecordSharingResult" not in combined and "AcquireSharingLease" not in combined
        assert "submitted_by:" not in combined and "object_id:" not in combined.replace("object_id:Text(row.Value.object_id)", "")
        assert "FirstError.Message" not in combined
        assert "SaveData(" not in combined and "LoadData(" not in combined


def test_screen_events_explicitly_replace_all_legacy_business_onvisible_formulas():
    files = CANVAS.render()
    for profile in ("stage", "prod"):
        events = json.loads(files[f"{profile}/screen-events.json"])
        assert set(events) == set(CANVAS.SCREENS)
        for screen in ("scrIntake", "scrResults", "scrReview", "scrHistory"):
            assert events[screen]["OnVisible"] == "false"
        assert events["scrUsers"]["OnVisible"].endswith("Select(btnLoadUsers)")
        assert "Select(btnLoadConfiguration)" in events["scrConfiguration"]["OnVisible"]


def test_business_records_and_dates_are_explicitly_converted():
    files = CANVAS.render()
    formula = props(files, "stage", "scrResults", "btnLoadResults")["OnSelect"]
    for text in ("Value(row.Value.review_version)", "Text(row.Value.canonical_record)",
                 "ForAll(Table(row.Value.issues)", "DateTimeValue(Text(row.Value.latest_review.decided_at))",
                 "Set(varRecordsCursor,Text(varRaw.next_cursor))"):
        assert text in formula
    submit = props(files, "stage", "scrIntake", "btnSubmit")["OnSelect"]
    assert "Set(varIntakeUncertain,!(Coalesce(varFlow.status,0) in [400,401,403,409,422]))" in submit
    assert submit.index("If(!varFlow.ok") < submit.index("Set(varAck,")
    retry = props(files, "stage", "scrReview", "btnRetryReview")["OnSelect"]
    save = props(files, "stage", "scrReview", "btnSaveReview")["OnSelect"]
    assert "GUID()" in save and "GUID()" not in retry
    assert "command_id:varPending.command_id" in retry
    assert "Coalesce(varFlow.status,0)=409" in retry


def test_admin_navigation_is_capability_based_even_if_business_database_is_down():
    files = CANVAS.render()
    for name, capability in (("btnConfiguration", "runtime.configure"), ("btnUsers", "users.manage")):
        values = props(files, "stage", "scrIntake", name)
        assert capability in values["Visible"]
        assert "varEnvironmentReady" not in str(values)
    for screen, button in (("scrConfiguration", "btnLoadConfiguration"), ("scrUsers", "btnLoadUsers")):
        assert "varEnvironmentReady" not in props(files, "stage", screen, button)["OnSelect"]


def test_config_secrets_are_write_only_and_uncertain_commands_keep_their_identity():
    files = CANVAS.render()
    values = props(files, "stage", "scrConfiguration", "txtConnectionString")
    assert values["Mode"] == "=TextMode.Password" and values["Default"] == '=\"\"'
    save = props(files, "stage", "scrConfiguration", "btnSaveDraft")["OnSelect"]
    assert "replacement_connection_string:" in save and "Reset(txtConnectionString)" in save
    retry = props(files, "stage", "scrConfiguration", "btnRetryConfiguration")["OnSelect"]
    assert "GUID()" not in retry and "varAdminCommand.payload_json" in retry
    assert 'varAdminOperation="ApplyRuntimeDraft"' in retry and '"GetRuntimeProfiles"' in retry
    recovery = props(files, "stage", "scrConfiguration", "btnRecoverConfiguration")["OnSelect"]
    assert "GetAdministrationOperation" in recovery and "command_id:varAdminCommand.command_id" in recovery
    for name in ("ddProvider", "txtTargetLabel", "chkEnabled", "txtConnectionString"):
        assert "!IsBlank(varDraft.draft_id)" in props(files,"stage","scrConfiguration",name)["DisplayMode"]
    assert "Set(varDraft,Blank())" in props(files,"stage","scrConfiguration","btnEditDraft")["OnSelect"]
    for path, source in files.items():
        if path.endswith(".controls.yaml"):
            for item in yaml.safe_load(source):
                for value in item.values():
                    if value["Control"] == "Label":
                        assert "payload_json" not in value["Properties"]["Text"]
                        assert "txtConnectionString" not in value["Properties"]["Text"]


def test_config_conflicts_release_commands_but_busy_and_user_conflicts_remain_frozen():
    files = CANVAS.render()
    for profile in ("stage", "prod"):
        for screen, name in (("scrConfiguration", "btnSaveDraft"),
                             ("scrConfiguration", "btnRetryConfiguration"),
                             ("scrUsers", "btnGrantUser"), ("scrUsers", "btnRetryUser")):
            formula = props(files, profile, screen, name)["OnSelect"]
            rejection_lists = re.findall(r"Coalesce\(varFlow.status,0\) in \[([^\]]+)\]", formula)
            assert rejection_lists and all("503" not in values.split(",") for values in rejection_lists)
            if screen == "scrConfiguration":
                assert all("409" in values.split(",") for values in rejection_lists)
            else:
                assert all("409" not in values.split(",") for values in rejection_lists)


def test_unknown_intake_requires_exact_receipt_and_keeps_source_and_override_frozen():
    files = CANVAS.render()
    for profile in ("stage", "prod"):
        formula = props(files, profile, "scrIntake", "btnIntakeRetryConfirm")["OnSelect"]
        assert "source_id:If(Coalesce(varIntakeUncertain,false),varSourceId,Blank())" in formula
        assert 'Text(varWorkflowRaw.source_resolution)="matched"' in formula
        assert "Text(varRecoveredIntake.source_id)=varSourceId" in formula
        assert "Set(varIntakeUncertain,false)" in formula
        assert formula.index("Text(varRecoveredIntake.source_id)=varSourceId") < formula.index("Set(varIntakeUncertain,false)")
        assert "original request may still be running" in formula
        assert "If(!Coalesce(varIntakeUncertain,false),Reset(txtSource)); Set(varIntakeUncertain,false)" not in formula
        for name in ("txtSource", "chkDuplicateOverride", "txtOverrideReason", "btnSubmit"):
            assert "Coalesce(varIntakeUncertain,false)" in props(files, profile, "scrIntake", name)["DisplayMode"]


def test_users_keep_pending_grants_retryable_and_owner_controls_disabled():
    files = CANVAS.render()
    for name in ("btnGrantUser", "btnRemoveUser", "txtUserUPN", "ddUserRole"):
        assert 'varSelectedUser.role="OWNER"' in props(files,"stage","scrUsers",name)["DisplayMode"]
    formula = props(files,"stage","scrUsers","btnRetryUser")["OnSelect"]
    assert "GUID()" not in formula and "varUserCommand.payload_json" in formula
    assert 'Text(varUserRaw.sharing_plan.status)="completed"' in formula
    assert 'target_upn:txtUserUPN.Text' in props(files,"stage","scrUsers","btnGrantUser")["OnSelect"]
    assert 'varFlow.error_code="REQUEST_FAILED"' in formula
    assert "!Coalesce(varUserSaveReturned,false)" in formula
    assert "Coalesce(varFlow.status,0)=404" not in props(files,"stage","scrUsers","btnRecoverUser")["OnSelect"]


def test_protected_owner_role_is_displayed_without_becoming_an_editable_option():
    files = CANVAS.render()
    for profile in ("stage", "prod"):
        role = props(files, profile, "scrUsers", "ddUserRole")
        # The current Owner gets a matching display value; all editable rows
        # and New user still offer only the two assignable roles.
        assert role["Items"] == '=If(varSelectedUser.role="OWNER",["OWNER"],["OPERATOR","ADMIN"])'
        assert role["Default"] == '=If(varSelectedUser.role="OWNER","OWNER",varSelectedUser.role="ADMIN","ADMIN","OPERATOR")'
        for name in ("ddUserRole", "txtUserUPN", "btnGrantUser", "btnRemoveUser"):
            assert 'varSelectedUser.role="OWNER"' in props(files, profile, "scrUsers", name)["DisplayMode"]
        assert "Reset(ddUserRole)" in props(files, profile, "scrUsers", "btnNewUser")["OnSelect"]


def test_admin_entry_clears_other_screen_messages_without_discarding_recovery_state():
    files = CANVAS.render()
    for profile in ("stage", "prod"):
        events = json.loads(files[f"{profile}/screen-events.json"])
        for screen, command in (("scrUsers", "varUserCommand"), ("scrConfiguration", "varAdminCommand")):
            formula = events[screen]["OnVisible"]
            first, follow_up = CANVAS.stages(formula)
            assert first.startswith(f"Set(varMessage,If(!IsBlank({command}.command_id),")
            assert first.endswith(',""))')
            assert "pending" in first and "retry" in first
            # Entry mutates only presentation text. A pending command, draft,
            # test and serialized payload survive navigation for recovery.
            assert re.findall(r"Set\(\s*(\w+)\s*,", formula) == ["varMessage"]
            assert not any(name + "(" in formula for name in ("Reset", "Clear", "ClearCollect"))
            if screen == "scrUsers":
                assert follow_up == "Select(btnLoadUsers)"
            else:
                assert follow_up == "If(!IsBlank(varAdminCommand.command_id) || !IsBlank(varDraft.draft_id),false,Select(btnLoadConfiguration))"


def test_every_generated_formula_has_balanced_delimiters_outside_literals():
    # Catches generator escaping defects before native compilation. This is a
    # lexical guard, not a replacement for the Power Fx type checker.
    def check(formula):
        stack = []
        quoted = False
        index = 0
        pairs = {")": "(", "}": "{", "]": "["}
        while index < len(formula):
            char = formula[index]
            if char == '"':
                if quoted and index + 1 < len(formula) and formula[index + 1] == '"':
                    index += 2
                    continue
                quoted = not quoted
            elif not quoted:
                if char in "({[":
                    stack.append(char)
                elif char in ")}]":
                    assert stack and stack.pop() == pairs[char], formula
            index += 1
        assert not quoted and not stack, formula

    def visit(value):
        if isinstance(value, dict):
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, str) and value.startswith("="):
            check(value)

    for path, source in CANVAS.render().items():
        if path.endswith(".controls.yaml"):
            visit(yaml.safe_load(source))
        elif path.endswith(".fx"):
            check(source)


def test_failed_steps_have_explicit_success_gates_before_later_side_effects():
    assert CANVAS.stages('Set(a,"semicolon; inside"); If(x,Set(b,1); Set(c,2)); Navigate(s)') == [
        'Set(a,"semicolon; inside")', 'If(x,Set(b,1); Set(c,2))', 'Navigate(s)']
    formula=CANVAS.action(CANVAS.invoke("GetCurrentUser")+'; Navigate(scrResults)', 'Set(varMessage,"failed")')
    assert "IfError(" not in formula
    assert "If(IsError(varFlow)" in formula
    assert "If(IsError(varRaw)" in formula
    assert "If(IsError(Navigate(scrResults))" in formula
    assert "TRANSPORT_UNKNOWN" in formula
    files=CANVAS.render()
    for path,text in files.items():
        if path.endswith(".controls.yaml") or path.endswith("app-onstart.fx"):
            assert "IfError(" not in text


def test_admin_controls_fit_native_tablet_canvas_and_reserved_button_space():
    import ast
    import operator

    files = CANVAS.render()
    def number(formula, width=1366, height=768):
        expression = formula.lstrip("=").replace("Parent.Width", str(width)).replace("Parent.Height", str(height))
        def evaluate(node):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            if isinstance(node, ast.BinOp) and type(node.op) in (ast.Add, ast.Sub):
                return {ast.Add: operator.add, ast.Sub: operator.sub}[type(node.op)](evaluate(node.left), evaluate(node.right))
            raise AssertionError("Unexpected layout expression: " + formula)
        return evaluate(ast.parse(expression, mode="eval").body)

    for profile in ("stage", "prod"):
        for screen in ("scrConfiguration", "scrUsers"):
            for item in yaml.safe_load(files[f"{profile}/{screen}.controls.yaml"]):
                name, control = next(iter(item.items()))
                values = control["Properties"]
                x, y, width, height = (number(values[key]) for key in ("X", "Y", "Width", "Height"))
                assert 0 <= x and 0 <= y and width > 0 and height > 0, name
                assert x + width <= 1366 and y + height <= 768, name
            prefix = "Configuration" if screen == "scrConfiguration" else "Users"
            title = props(files, profile, screen, prefix + "Title")
            back = props(files, profile, screen, prefix + "Back")
            assert number(title["X"]) + number(title["Width"]) + 24 <= number(back["X"])
        active = props(files, profile, "scrConfiguration", "ActiveConfiguration")
        load = props(files, profile, "scrConfiguration", "btnLoadConfiguration")
        assert number(load["X"]) + number(load["Width"]) + 20 <= number(active["X"])


def test_accessibility_preserves_types_behavior_and_secret_boundaries():
    from copy import deepcopy

    screens = CANVAS.build_business()
    screens["scrConfiguration"] = CANVAS.build_configuration()
    screens["scrUsers"] = CANVAS.build_users()
    original = deepcopy(screens)
    CANVAS.apply_accessibility(screens)
    additions = {"AccessibleLabel", "ItemAccessibleLabel", "TabIndex", "FocusedBorderThickness", "FocusedBorderColor", "Live"}
    text_changes = {"RequestRow", "btnOpenReview", "UserRow", "chkEnabled"}
    def compare(before, after):
        assert len(before) == len(after)
        for old, new in zip(before, after):
            assert old.keys() == new.keys()
            name = next(iter(old))
            a, b = old[name], new[name]
            assert a["Control"] == b["Control"]
            for key, value in a["Properties"].items():
                if key == "Text" and name in text_changes:
                    continue
                assert b["Properties"][key] == value, (name, key)
            assert set(b["Properties"]) - set(a["Properties"]) <= additions
            if a["Control"] in {"Classic/Button", "Classic/CheckBox"}:
                assert "AccessibleLabel" not in b["Properties"]
            if a["Control"] == "Label":
                assert "TabIndex" not in b["Properties"]
            compare(a.get("Children", []), b.get("Children", []))
    for name in screens:
        compare(original[name], screens[name])
    password = CANVAS.properties(screens["scrConfiguration"], "txtConnectionString")
    assert password["AccessibleLabel"].startswith('="Replacement connection string')
    assert "txtConnectionString.Text" not in password["AccessibleLabel"]
    assert password["Mode"] == "=TextMode.Password" and password["Default"] == '=\"\"'


def test_keyboard_labels_and_live_messages_cover_both_variants():
    files = CANVAS.render()
    for profile in ("stage", "prod"):
        counts = {"keyboard": 0, "input_labels": 0, "gallery_labels": 0, "live": 0}
        def visit(controls):
            for item in controls:
                name, control = next(iter(item.items()))
                values, kind = control["Properties"], control["Control"]
                if kind in {"Classic/Button", "Classic/TextInput", "Classic/DropDown", "Classic/CheckBox"}:
                    counts["keyboard"] += 1
                    assert values["TabIndex"] == "=0"
                    assert values["FocusedBorderThickness"] == "=3"
                    assert values["FocusedBorderColor"] in {"=Self.Color", "=RGBA(0,0,0,1)"}
                if kind in {"Classic/TextInput", "Classic/DropDown"}:
                    counts["input_labels"] += 1
                    assert values["AccessibleLabel"].startswith('="')
                if kind == "Gallery":
                    counts["gallery_labels"] += 1
                    assert values["AccessibleLabel"].startswith('="')
                    assert "ThisItem." in values["ItemAccessibleLabel"]
                if "Live" in values:
                    counts["live"] += 1
                    assert kind == "Label" and values["Live"] == "=Live.Polite"
                    assert "varMessage" in values["Text"]
                visit(control.get("Children", []))
        for screen in CANVAS.SCREENS:
            visit(yaml.safe_load(files[f"{profile}/{screen}.controls.yaml"]))
        assert counts == {"keyboard": 50, "input_labels": 11, "gallery_labels": 4, "live": 6}
