"""Build per-environment Canvas controls for the trusted Power Automate broker.

The existing four-screen source remains the rollback artifact. This generator
does not upload, publish, bind connections or enable server enforcement.
"""
from argparse import ArgumentParser
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "powerapps" / "canvas"
OUTPUT = BASE / "broker"
SCREENS = ("scrIntake", "scrResults", "scrReview", "scrHistory", "scrConfiguration", "scrUsers")


def quoted(text):
    return '"' + text.replace('"', '""') + '"'


def invoke(operation, payload="{}", raw="varRaw", *, serialized=False):
    payload = payload if serialized else f"JSON({payload},JSONFormat.Compact)"
    return (f'Set(varFlow,__FLOW__.Run("{operation}",{payload})); varFlow; '
            'If(!varFlow.ok,Error({Kind:ErrorKind.Custom,Message:"Request failed"})); '
            f'Set({raw},ParseJSON(varFlow.result_json)); {raw}')


def stages(formula):
    """Split behavior chaining only at the outer Power Fx expression level."""
    result, start, stack, in_string, index = [], 0, [], False, 0
    while index < len(formula):
        char = formula[index]
        if char == '"':
            if in_string and index + 1 < len(formula) and formula[index + 1] == '"':
                index += 2
                continue
            in_string = not in_string
        elif not in_string:
            if char in "({[":
                stack.append(char)
            elif char in ")}]":
                stack.pop()
            elif char == ";" and not stack:
                result.append(formula[start:index].strip())
                start = index + 1
        index += 1
    result.append(formula[start:].strip())
    return [value for value in result if value]


def guarded(body, failure):
    # A semicolon chain continues after an error in Power Fx. Every external
    # result and subsequent state change therefore has an explicit success
    # branch. IsError avoids IfError's mixed record/boolean return coercion.
    failure = ('If(IsError(varFlow),Set(varFlow,{ok:false,status:0,error_code:"TRANSPORT_UNKNOWN",'
               'error_message:"",request_id:"",result_json:""})); ' + failure)
    result = "true"
    for step in reversed(stages(body)):
        result = f"If(IsError({step}),{failure}; false,{result})"
    return result


def action(body, failure, *, business=False, capability=None):
    guard = "!Coalesce(varBusy,false)"
    if business:
        guard += " && Coalesce(varEnvironmentReady,false)"
    if capability:
        guard += f' && "{capability}" in colCapabilities.Value'
    return (f'=If({guard},Set(varBusy,true); Set(varFlow,Blank()); '
            + guarded(body, failure) + '; Set(varBusy,false))')


def message(text):
    return f"Set(varMessage,{quoted(text)})"


def request_record(raw):
    return ("{request_id:Text(" + raw + ".request_id),source_type:Text(" + raw + ".source_type),"
            "source_id:Text(" + raw + ".source_id),status:Text(" + raw + ".status),"
            "received_at:DateTimeValue(Text(" + raw + ".received_at)),"
            "completed_at:If(IsBlank(Text(" + raw + ".completed_at)),Blank(),DateTimeValue(Text(" + raw + ".completed_at)))}")


def records(raw):
    return (f"ForAll(Table({raw}.items) As row,{{record_id:Text(row.Value.record_id),"
            "request_id:Text(row.Value.request_id),record_sequence:Value(row.Value.record_sequence),"
            "canonical_record:Text(row.Value.canonical_record),normalized_record:Text(row.Value.normalized_record),"
            "raw_candidate:Text(row.Value.raw_candidate),status:Text(row.Value.status),"
            "review_version:Value(row.Value.review_version),"
            "issues:ForAll(Table(row.Value.issues) As issue,{issue_id:Value(issue.Value.issue_id),"
            "issue_code:Text(issue.Value.issue_code),severity:Text(issue.Value.severity),"
            "field_name:Text(issue.Value.field_name),position_start:Value(issue.Value.position_start),"
            "position_end:Value(issue.Value.position_end),message:Text(issue.Value.message)}),"
            "latest_review:{decision:Text(row.Value.latest_review.decision),reason:Text(row.Value.latest_review.reason),"
            "decided_by:Text(row.Value.latest_review.decided_by),"
            "decided_at:If(IsBlank(Text(row.Value.latest_review.decided_at)),Blank(),DateTimeValue(Text(row.Value.latest_review.decided_at))),"
            "review_version:Value(row.Value.latest_review.review_version)}})")


def events(raw):
    return (f"ForAll(Table({raw}.items) As row,{{event_id:Value(row.Value.event_id),"
            "aggregate_type:Text(row.Value.aggregate_type),aggregate_id:Text(row.Value.aggregate_id),"
            "event_type:Text(row.Value.event_type),actor:Text(row.Value.actor),"
            "occurred_at:DateTimeValue(Text(row.Value.occurred_at))})")


def profiles(raw):
    return (f"ForAll(Table({raw}.profiles) As row,{{profile_id:Text(row.Value.profile_id),revision:Text(row.Value.revision),"
            "provider:Text(row.Value.provider),label:Text(row.Value.label),enabled:Boolean(row.Value.enabled),"
            "runtime_state:Text(row.Value.runtime_state),editable:Boolean(row.Value.editable),"
            "target:Text(row.Value.target)})")


def user_rows(raw):
    return (f"ForAll(Table({raw}.items) As row,{{object_id:Text(row.Value.object_id),upn:Text(row.Value.upn),"
            "display_name:Text(row.Value.display_name),role:Text(row.Value.role),"
            "desired_active:Boolean(row.Value.desired_active),access_state:Text(row.Value.access_state)})")


def control(name, kind, **props):
    return {name: {"Control": kind, "Properties": {key: value if str(value).startswith("=") else "=" + str(value)
                                                  for key, value in props.items()}}}


def button(name, text, x, y, formula, *, width=210, disabled="Coalesce(varBusy,false)", visible=None):
    props = dict(X=x, Y=y, Width=width, Height=44, Text=quoted(text), OnSelect=formula,
                 DisplayMode=f"If({disabled},DisplayMode.Disabled,DisplayMode.Edit)")
    if visible:
        props["Visible"] = visible
    return control(name, "Classic/Button", **props)


def label(name, text, x, y, width="Parent.Width-48", height=44, **props):
    return control(name, "Label", X=x, Y=y, Width=width, Height=height, Text=text, **props)


def properties(controls, name):
    for item in controls:
        if name in item:
            return item[name]["Properties"]
    raise KeyError(name)


def identity():
    return (invoke("GetCurrentUser", raw="varIdentityRaw") + "; "
            "Set(varCurrentUser,{display_name:Text(varIdentityRaw.display_name),role:Text(varIdentityRaw.role),"
            "environment:Text(varIdentityRaw.environment)}); "
            "If(varCurrentUser.environment<>AppEnvironment,Error({Kind:ErrorKind.Custom,Message:\"Wrong environment\"})); "
            "ClearCollect(colCapabilities,ForAll(Table(varIdentityRaw.capabilities),{Value:Text(Value)}))")


def health():
    return (invoke("GetHealth", raw="varHealthRaw") + "; "
            "Set(varEnvironment,{environment:Text(varHealthRaw.environment),target_label:Text(varHealthRaw.target_label),"
            "ready:Boolean(varHealthRaw.ready)}); "
            "Set(varEnvironmentReady,varEnvironment.environment=AppEnvironment && varEnvironment.ready)")


def load_profiles():
    return (invoke("GetRuntimeProfiles") + f"; ClearCollect(colProfiles,{profiles('varRaw')}); "
            "Set(varActiveProfile,LookUp(colProfiles,profile_id=AppEnvironment)); "
            "Reset(ddProvider); Reset(txtTargetLabel); Reset(chkEnabled)")


def build_business():
    screens = {name: yaml.safe_load((BASE / (name + ".controls.yaml")).read_text(encoding="utf-8"))
               for name in SCREENS[:4]}
    intake = screens["scrIntake"]
    properties(intake, "IntakeTitle")["Width"] = "=Parent.Width-600"
    intake += [button("btnConfiguration", "Configuration", "Parent.Width-464", 22,
                      '=Navigate(scrConfiguration)', visible='"runtime.configure" in colCapabilities.Value'),
               button("btnUsers", "Users", "Parent.Width-234", 22,
                      '=Navigate(scrUsers)', visible='"users.manage" in colCapabilities.Value')]
    properties(intake, "btnCheckEnvironment")["OnSelect"] = action(
        'Set(varEnvironmentReady,false); Clear(colCapabilities); ' + identity() + '; ' + health() + '; ' + invoke('GetIntakeWorkflow',raw='varWorkflowRaw') + '; Set(varActiveIntake,Text(varWorkflowRaw.active_request_id))' +
        '; ' + message("Connection checked."),
        'Set(varEnvironmentReady,false); ' + message("Connection unavailable. Configuration and Users remain available to authorized administrators."))
    properties(intake, "btnSubmit")["OnSelect"] = action(
        'Set(varSourceId,Text(GUID())); ' + invoke("CreateIntakeRequest", '{source_type:"PASTE",source_id:varSourceId,source_text:txtSource.Text,duplicate_override_reason:If(chkDuplicateOverride.Value,txtOverrideReason.Text,Blank())}') +
        '; Set(varAck,{request_id:Text(varRaw.request_id),status:Text(varRaw.status),received_at:DateTimeValue(Text(varRaw.received_at)),'
        'records:Value(varRaw.records),rejected:Value(varRaw.rejected),requires_review:Value(varRaw.requires_review)}); '
        'Set(varRequestId,varAck.request_id); Set(varActiveIntake,varAck.request_id); Set(varIntakeUncertain,false); Reset(chkDuplicateOverride); Reset(txtOverrideReason); ' + message("Intake saved. Load results to inspect validation.") + '; Navigate(scrResults)',
        'Set(varIntakeUncertain,!(Coalesce(varFlow.status,0) in [400,401,403,409,422])); Set(varMessage,If(Coalesce(varFlow.status,0)=409,"Intake blocked. Resume your unfinished intake, or ask an administrator to override a duplicate submitted within 2 hours.","Submission outcome is unknown. Keep the text and compare this source ID in recent requests: " & varSourceId))', business=True)
    workflow = (invoke("GetIntakeWorkflow", '{source_id:If(Coalesce(varIntakeUncertain,false),varSourceId,Blank())}', raw="varWorkflowRaw") +
                '; Set(varActiveIntake,Text(varWorkflowRaw.active_request_id))')
    retry = properties(intake, "btnIntakeRetryConfirm")
    retry["Text"] = '= "Resume / new intake"'
    retry["DisplayMode"] = '=If(Coalesce(varBusy,false) || !Coalesce(varEnvironmentReady,false),DisplayMode.Disabled,DisplayMode.Edit)'
    retry["OnSelect"] = action(workflow +
        '; If(Coalesce(varIntakeUncertain,false),'
        'If(Text(varWorkflowRaw.source_resolution)="matched" && CountRows(Table(varWorkflowRaw.source_receipts))=1,'
        'Set(varRecoveredIntake,First(Table(varWorkflowRaw.source_receipts)).Value); '
        'If(Text(varRecoveredIntake.source_id)=varSourceId,'
        'Set(varAck,{request_id:Text(varRecoveredIntake.request_id),status:Text(varRecoveredIntake.status),'
        'received_at:DateTimeValue(Text(varRecoveredIntake.received_at)),records:Value(varRecoveredIntake.records),'
        'rejected:Value(varRecoveredIntake.rejected),requires_review:Value(varRecoveredIntake.requires_review)}); '
        'Set(varRequestId,varAck.request_id); Set(varIntakeUncertain,false); '
        'Reset(chkDuplicateOverride); Reset(txtOverrideReason); '
        'Set(varMessage,"Saved intake confirmed by its source ID. Load results to inspect it."); Navigate(scrResults),'
        'Set(varMessage,"Receipt did not match this source ID. Keep the submission and contact an administrator.")),'
        'Set(varMessage,"Submission remains unconfirmed. Keep the text and source ID: " & varSourceId & ". Check again later or contact an administrator; the original request may still be running.")),'
        'If(!Boolean(varWorkflowRaw.can_start),Set(varRequestId,varActiveIntake); Navigate(scrResults),'
        'Reset(txtSource); Reset(chkDuplicateOverride); Reset(txtOverrideReason); '
        'Set(varSourceId,Blank()); Set(varAck,Blank()); Set(varRequestId,Blank()); '
        'Set(varMessage,"Ready for a new intake. Identical content is blocked for 2 hours.")))',
        message("Workflow status unavailable. Keep the current intake and retry."), business=True)
    properties(intake,"txtSource")["Height"] = "=244"
    properties(intake,"txtSource")["DisplayMode"] = '=If(Coalesce(varBusy,false) || !Coalesce(varEnvironmentReady,false) || Coalesce(varIntakeUncertain,false) || !IsBlank(varActiveIntake),DisplayMode.Disabled,DisplayMode.Edit)'
    properties(intake,"btnSubmit")["DisplayMode"] = '=If(Coalesce(varBusy,false) || !Coalesce(varEnvironmentReady,false) || Coalesce(varIntakeUncertain,false) || !IsBlank(varActiveIntake) || IsBlank(Trim(txtSource.Text)) || (chkDuplicateOverride.Value && IsBlank(Trim(txtOverrideReason.Text))),DisplayMode.Disabled,DisplayMode.Edit)'
    intake += [control("chkDuplicateOverride","Classic/CheckBox",X=24,Y=416,Width=290,Height=44,
                       Text='"Override 2-hour duplicate block"',Default="false",
                       Visible='"runtime.configure" in colCapabilities.Value',DisplayMode='If(Coalesce(varBusy,false) || Coalesce(varIntakeUncertain,false),DisplayMode.Disabled,DisplayMode.Edit)'),
               control("txtOverrideReason","Classic/TextInput",X=330,Y=416,Width="Parent.Width-354",Height=44,
                       Default='""',HintText='"Required override reason (recorded in audit)"',MaxLength=1000,
                       Visible='"runtime.configure" in colCapabilities.Value && chkDuplicateOverride.Value',DisplayMode='If(Coalesce(varBusy,false) || Coalesce(varIntakeUncertain,false),DisplayMode.Disabled,DisplayMode.Edit)')]
    for name, more in (("btnRecent", False), ("btnMoreRequests", True)):
        payload = '{limit:50,cursor:varRequestsCursor}' if more else '{limit:50}'
        method = "Collect" if more else "ClearCollect"
        body = invoke("ListIntakeRequests", payload) + f'; {method}(colRequests,ForAll(Table(varRaw.items) As row,{request_record("row.Value")})); Set(varRequestsCursor,Text(varRaw.next_cursor))'
        properties(intake, name)["OnSelect"] = action(body, message("Requests unavailable. Input and pagination retained."), business=True)

    results = screens["scrResults"]
    properties(results, "btnLoadResults")["OnSelect"] = action(
        invoke("GetIntakeRequest", "{request_id:varRequestId}", "varDetailRaw") + f'; Set(varRequestDetail,{request_record("varDetailRaw")}); ' +
        invoke("ListRecordResults", "{request_id:varRequestId,limit:50}") +
        f'; ClearCollect(colRecords,{records("varRaw")}); Set(varRecordsCursor,Text(varRaw.next_cursor)); '
        'Set(varRecordPageCursor,Blank()); Set(varLoadedRequest,varRequestId); Set(varMessage,"")',
        'Set(varLoadedRequest,Blank()); ' + message("Results unavailable. Reload before reviewing."), business=True)
    properties(results, "btnNextRecords")["OnSelect"] = action(
        invoke("ListRecordResults", "{request_id:varRequestId,limit:50,cursor:varRecordsCursor}") +
        f'; Set(varRecordPageCursor,varRecordsCursor); ClearCollect(colRecords,{records("varRaw")}); Set(varRecordsCursor,Text(varRaw.next_cursor))',
        message("Next page failed. Results and cursor retained."), business=True)

    review = screens["scrReview"]
    review_call = invoke("CreateReviewDecision", '{record_id:varPendingRecord,command_id:varPending.command_id,decision:varPending.decision,expected_version:varPending.expected_version,reason:varPending.reason}')
    refresh = invoke("ListRecordResults", "{request_id:varRequestId,limit:50,cursor:varRecordPageCursor}") + f'; ClearCollect(colRefreshedRecords,{records("varRaw")})'
    success = ('; Set(varReloaded,LookUp(colRefreshedRecords,record_id=varPendingRecord)); '
               'If(IsBlank(varReloaded.record_id),Error({Kind:ErrorKind.Custom,Message:"Record missing"})); '
               'Set(varRecord,varReloaded); Set(varPending,Blank()); Set(varConflict,false); ' + message("Review saved. Delivery is not connected."))
    failure = 'Set(varConflict,Coalesce(varFlow.status,0)=409); Set(varMessage,If(varConflict,"Conflict. Reload and inspect the current version.","Review outcome unknown. Retry the same command; reason and decision are retained."))'
    for name in ("btnSaveReview", "btnRetryReview"):
        prefix = ('Set(varPending,{decision:ddDecision.Selected.Value,reason:txtReason.Text,expected_version:varRecord.review_version,command_id:Text(GUID())}); Set(varPendingRecord,varRecord.record_id); '
                  if name == "btnSaveReview" else "")
        properties(review, name)["OnSelect"] = action(prefix + review_call + '; ' + refresh + success, failure, business=True)
    properties(review, "btnReconcile")["OnSelect"] = action(refresh +
        '; Set(varReloaded,LookUp(colRefreshedRecords,record_id=varRecord.record_id)); '
        'If(IsBlank(varReloaded.record_id),' + message("Record absent from this page. Pending command retained.") +
        ',Set(varRecord,varReloaded); Set(varPending,Blank()); Set(varConflict,false); ' + message("Current version loaded. Inspect it before saving a new decision.") + ')',
        message("Reload failed. Pending command retained."), business=True)

    history = screens["scrHistory"]
    for name, more in (("btnLoadHistory", False), ("btnMoreHistory", True)):
        payload = '{request_id:varRequestId,limit:50' + (',cursor:varEventsCursor}' if more else '}')
        method = "Collect" if more else "ClearCollect"
        properties(history, name)["OnSelect"] = action(invoke("ListAuditEvents", payload) +
            f'; {method}(colEvents,{events("varRaw")}); Set(varEventsCursor,Text(varRaw.next_cursor)); Set(varHistoryRequest,varRequestId); Set(varMessage,"")',
            message("History unavailable. Current events and cursor retained."), business=True)
    return screens


def admin_heading(prefix, title):
    return [label(prefix + "Title", quoted(title) + ' & " | " & Upper(AppEnvironment)', 24, 18, width="Parent.Width-282", height=50, Size=24),
            label(prefix + "Message", 'Coalesce(varMessage,"")', 24, 82, height=60),
            button(prefix + "Back", "Intake", "Parent.Width-234", 20, "=Navigate(scrIntake)")]


def admin_result():
    # GetAdministrationOperation wraps the original result. Normal calls do not.
    return ('If(varAdminOperation="SaveRuntimeDraft",Set(varDraft,{draft_id:Text(varAdminRaw.draft_id),draft_revision:Text(varAdminRaw.draft_revision),base_revision:Text(varAdminRaw.base_revision),target:Text(varAdminRaw.target)}); Set(varTest,Blank()),'
            'varAdminOperation="TestRuntimeDraft",Set(varTest,{test_id:Text(varAdminRaw.test_id),status:Text(varAdminRaw.status),expires_at:DateTimeValue(Text(varAdminRaw.expires_at))}),'
            'varAdminOperation="ApplyRuntimeDraft",Set(varEnvironmentReady,false); Set(varDraft,Blank()); Set(varTest,Blank())); '
            'Set(varAdminCommand,Blank()); Reset(txtConnectionString); '
            'Set(varMessage,"Configuration command: " & Text(varAdminRaw.status))')


def admin_submit(operation, payload):
    return ('Set(varAdminOperation,"' + operation + '"); Set(varAdminCommandId,Text(GUID())); '
            'Set(varAdminCommand,{command_id:varAdminCommandId,payload_json:JSON(' + payload + ',JSONFormat.Compact)}); '
            'Reset(txtConnectionString); ' + invoke(operation, "varAdminCommand.payload_json", "varAdminRaw", serialized=True) + '; ' + admin_result())


def build_configuration():
    busy = 'Coalesce(varBusy,false) || !("runtime.configure" in colCapabilities.Value)'
    pending = busy + ' || !IsBlank(varAdminCommand.command_id)'
    editing = pending + ' || !IsBlank(varDraft.draft_id)'
    controls = admin_heading("Configuration", "Database configuration")
    controls += [button("btnLoadConfiguration", "Load configuration", 24, 148,
        action('If(!IsBlank(varDraft.draft_id),Error({Kind:ErrorKind.Custom,Message:"Draft exists"})); ' + load_profiles() + '; Set(varMessage,"")', message("Configuration unavailable. Discard any saved draft before reloading."), capability="runtime.configure"), disabled=editing),
        label("ActiveConfiguration", '"Active: " & Coalesce(varActiveProfile.label,"Load configuration") & " | " & Coalesce(varActiveProfile.provider,"") & " | " & If(Coalesce(varActiveProfile.enabled,false),"Enabled","Disabled") & Char(10) & "Revision: " & Coalesce(varActiveProfile.revision,"")', 254, 146, width="Parent.Width-278", height=66),
        control("ddProvider", "Classic/DropDown", X=24,Y=236,Width=240,Height=44,Items='["auto"]',Default='"auto"',DisplayMode=f'If({editing},DisplayMode.Disabled,DisplayMode.Edit)'),
        control("txtTargetLabel", "Classic/TextInput", X=284,Y=236,Width=440,Height=44,Default='Coalesce(varActiveProfile.label,"")',HintText='"Target label"',MaxLength=80,DisplayMode=f'If({editing},DisplayMode.Disabled,DisplayMode.Edit)'),
        control("chkEnabled", "Classic/CheckBox", X=748,Y=236,Width=200,Height=44,Text='"Enabled"',Default='Coalesce(varActiveProfile.enabled,false)',DisplayMode=f'If({editing},DisplayMode.Disabled,DisplayMode.Edit)'),
        label("ConnectionGuidance", '"Replacement connection string (optional). Saved credentials are never displayed. Disable the environment before changing its database target."', 24, 300, height=64),
        control("txtConnectionString", "Classic/TextInput", X=24,Y=376,Width="Parent.Width-48",Height=44,Default='""',Mode="TextMode.Password",HintText='"Leave blank to keep the saved connection"',DisplayMode=f'If({editing},DisplayMode.Disabled,DisplayMode.Edit)'),
        label("DraftState", '"Draft: " & Coalesce(varDraft.draft_id,"none") & " | Test: " & Coalesce(varTest.status,"not run") & If(!IsBlank(varTest.expires_at)," | Expires: " & Text(varTest.expires_at,DateTimeFormat.ShortDateTime),"")',24,436,height=54)]
    failed = ('If(!Coalesce(varFlow.ok,false) && Coalesce(varFlow.status,0) in [400,401,403,404,409,412,422],'
              'Set(varAdminCommand,Blank()); Reset(txtConnectionString); ' + message("Command rejected. Reload configuration and check the proposed settings.") +
              ',' + message("Outcome unknown. Check command status or retry the same command before another change.") + ')')
    payload = '{command_id:varAdminCommandId,expected_active_revision:varActiveProfile.revision,provider:ddProvider.Selected.Value,label:txtTargetLabel.Text,enabled:chkEnabled.Value,replacement_connection_string:If(IsBlank(txtConnectionString.Text),Blank(),txtConnectionString.Text)}'
    controls += [button("btnSaveDraft","Save draft",24,508,action(admin_submit("SaveRuntimeDraft",payload),failed,capability="runtime.configure"),disabled=editing+' || IsBlank(varActiveProfile.revision) || IsBlank(Trim(txtTargetLabel.Text))'),
        button("btnTestDraft","Test draft",254,508,action(admin_submit("TestRuntimeDraft",'{command_id:varAdminCommandId,draft_id:varDraft.draft_id,draft_revision:varDraft.draft_revision}'),failed,capability="runtime.configure"),disabled=pending+' || IsBlank(varDraft.draft_id)'),
        button("btnApplyDraft","Apply draft",484,508,action(admin_submit("ApplyRuntimeDraft",'{command_id:varAdminCommandId,draft_id:varDraft.draft_id,draft_revision:varDraft.draft_revision,expected_active_revision:varDraft.base_revision,test_id:If(IsBlank(varTest.test_id),Blank(),varTest.test_id)}')+'; '+guarded(load_profiles(),message("Configuration applied. Reload configuration to refresh the display.")),failed,capability="runtime.configure"),disabled=pending+' || IsBlank(varDraft.draft_id)'),
        button("btnEditDraft","Discard draft",714,508,'=Set(varDraft,Blank()); Set(varTest,Blank()); Reset(ddProvider); Reset(txtTargetLabel); Reset(chkEnabled); Reset(txtConnectionString); Set(varMessage,"Draft discarded. Enter the new settings and any replacement connection string.")',disabled=pending+' || IsBlank(varDraft.draft_id)'),
        button("btnRecoverConfiguration","Check command status",24,570,action(invoke("GetAdministrationOperation",'{command_id:varAdminCommand.command_id}',"varOperationRaw")+'; Set(varAdminRaw,varOperationRaw.result); '+admin_result()+'; If(varAdminOperation="ApplyRuntimeDraft",'+guarded(load_profiles(),message("Command result confirmed. Reload configuration to refresh the display."))+')',message("No confirmed result. Retry the retained command if its outcome is still unknown."),capability="runtime.configure"),disabled=busy+' || IsBlank(varAdminCommand.command_id)'),
        button("btnRetryConfiguration","Retry same command",254,570,action('Set(varFlow,__FLOW__.Run(varAdminOperation,varAdminCommand.payload_json)); varFlow; If(!varFlow.ok,Error({Kind:ErrorKind.Custom,Message:"Request failed"})); Set(varAdminRaw,ParseJSON(varFlow.result_json)); varAdminRaw; '+admin_result()+'; If(varAdminOperation="ApplyRuntimeDraft",'+guarded(load_profiles(),message("Configuration applied. Reload configuration to refresh the display."))+')',failed,capability="runtime.configure"),disabled=busy+' || IsBlank(varAdminCommand.command_id)'),
        label("ConfigurationCommand", 'If(!IsBlank(varAdminCommand.command_id),"Pending command: " & varAdminCommand.command_id,"")',24,634,height=46)]
    controls += [control("txtInitializeTarget","Classic/TextInput",X=484,Y=570,Width=440,Height=44,
                        Default='""',HintText='"Type saved draft target to confirm initialization"',
                        DisplayMode=f'If({pending},DisplayMode.Disabled,DisplayMode.Edit)'),
                 button("btnInitializeDatabase","Initialize database",954,570,
                        action(admin_submit("InitializeRuntimeDraft",'{command_id:varAdminCommandId,draft_id:varDraft.draft_id,draft_revision:varDraft.draft_revision,confirm_target:txtInitializeTarget.Text}'),failed,capability="runtime.configure"),
                        disabled=pending+' || IsBlank(varDraft.draft_id) || varActiveProfile.enabled || txtInitializeTarget.Text<>varDraft.target')]
    properties(controls,"DraftState")["Text"] = '= "Draft target: " & Coalesce(varDraft.target,"none") & " | Test: " & Coalesce(varTest.status,"not run")'
    return controls


def build_users():
    busy = 'Coalesce(varBusy,false) || !("users.manage" in colCapabilities.Value)'
    pending = busy + ' || !IsBlank(varUserCommand.command_id)'
    protected = pending + ' || varSelectedUser.role="OWNER"'
    load = invoke("ListUsers") + f'; ClearCollect(colUsers,{user_rows("varRaw")}); Set(varUsersRevision,Text(varRaw.revision))'
    result = ('Set(varMessage,"Access: " & Text(varUserRaw.membership.access_state) & " | Sharing: " & Text(varUserRaw.sharing_plan.status)); '
              'If(Text(varUserRaw.sharing_plan.status)="completed",Set(varUserCommand,Blank())); ' + guarded(load,message("Access result confirmed. Reload users to refresh the list.")))
    # A flow can fail after SaveUserAccess already committed (for example while
    # acquiring the sharing lease). A status lookup can also race an original
    # execution that has not reached SaveUserAccess yet. Keep the same command.
    fail = ('If(!Coalesce(varUserSaveReturned,false) && '
            '((varFlow.error_code="REQUEST_FAILED" && Coalesce(varFlow.status,0) in [400,401,403,404,422]) || '
            'varFlow.error_code in ["INVALID_TARGET","INVALID_COMMAND"] || '
            '(varFlow.error_code="ACCESS_DENIED" && Coalesce(varFlow.status,0) in [401,403])),'
            'Set(varUserCommand,Blank()); ' + message("Access command rejected. Reload users and check the account and role.") + ',' +
            message("Access change is unconfirmed. Check status or retry the same command.") + ')')
    recover_fail = message("No confirmed result yet. The original flow may still be running; retry the same command.")
    controls = admin_heading("Users", "User access")
    controls += [button("btnLoadUsers", "Load users", 24,148,action(load,message("User list unavailable."),capability="users.manage"),disabled=busy),
        button("btnNewUser", "New user",254,148,'=Set(varSelectedUser,Blank()); Reset(txtUserUPN); Reset(ddUserRole)',disabled=pending),
        label("UserPolicy", '"Owners are protected. Admins can manage users and configuration. Operators can submit and review intake."',24,204,height=50),
        control("txtUserUPN","Classic/TextInput",X=24,Y=270,Width=440,Height=44,Default='Coalesce(varSelectedUser.upn,"")',HintText='"name@austinlighthouse.org"',DisplayMode=f'If({protected},DisplayMode.Disabled,DisplayMode.Edit)'),
        control("ddUserRole","Classic/DropDown",X=484,Y=270,Width=220,Height=44,Items='If(varSelectedUser.role="OWNER",["OWNER"],["OPERATOR","ADMIN"])',Default='If(varSelectedUser.role="OWNER","OWNER",varSelectedUser.role="ADMIN","ADMIN","OPERATOR")',DisplayMode=f'If({protected},DisplayMode.Disabled,DisplayMode.Edit)')]
    for name,title,active,x in (("btnGrantUser","Save access",True,724),("btnRemoveUser","Remove access",False,954)):
        body = ('Set(varUserCommandId,Text(GUID())); Set(varUserCommand,{command_id:varUserCommandId,payload_json:JSON('
                '{command_id:varUserCommandId,expected_revision:varUsersRevision,target_upn:txtUserUPN.Text,role:ddUserRole.Selected.Value,active:' + str(active).lower() +
                '},JSONFormat.Compact)}); Set(varUserSaveReturned,false); ' + invoke("SaveUserAccess","varUserCommand.payload_json","varUserRaw",serialized=True) + '; Set(varUserSaveReturned,true); ' + result)
        controls.append(button(name,title,x,270,action(body,fail,capability="users.manage"),disabled=protected+' || IsBlank(varUsersRevision) || IsBlank(Trim(txtUserUPN.Text))'+(' || IsBlank(varSelectedUser.object_id)' if not active else '')))
    controls += [button("btnRetryUser","Retry sharing",24,330,action('Set(varUserSaveReturned,false); '+invoke("SaveUserAccess","varUserCommand.payload_json","varUserRaw",serialized=True)+'; Set(varUserSaveReturned,true); '+result,fail,capability="users.manage"),disabled=busy+' || IsBlank(varUserCommand.command_id)'),
        button("btnRecoverUser","Check command status",254,330,action(invoke("GetAdministrationOperation",'{command_id:varUserCommand.command_id}',"varOperationRaw")+'; Set(varUserRaw,varOperationRaw.result); '+result,recover_fail,capability="users.manage"),disabled=busy+' || IsBlank(varUserCommand.command_id)')]
    gallery = control("galUsers","Gallery",X=24,Y=396,Width="Parent.Width-48",Height="Parent.Height-414",Items="colUsers",TemplateSize=70)
    gallery["galUsers"].update(Variant="Vertical",Children=[button("UserRow", "",0,0,'=Set(varSelectedUser,ThisItem); Reset(txtUserUPN); Reset(ddUserRole)',width="Parent.TemplateWidth",disabled=pending)])
    properties(gallery["galUsers"]["Children"],"UserRow")["Text"] = '=ThisItem.display_name & " | " & ThisItem.role & " | " & ThisItem.access_state & If(ThisItem.role="OWNER"," | protected","")'
    controls.append(gallery)
    return controls


def apply_accessibility(screens):
    """Add supported classic-control metadata without changing app behavior.

    Native Button 2.2.0 and CheckBox 2.1.0 use Text as their accessible name;
    neither exposes AccessibleLabel. Labels already default to TabIndex -1.
    """
    labels = {
        "txtSource": "Original email or ticket text",
        "txtCanonical": "Canonical MILSTRIP record, read only",
        "txtReason": "Review reason, required",
        "ddDecision": "Review decision",
        "ddProvider": "Database provider, automatically detected",
        "txtInitializeTarget": "Confirm saved draft target for database initialization",
        "txtOverrideReason": "Audited duplicate override reason",
        "txtTargetLabel": "Database target label",
        "txtConnectionString": "Replacement connection string, optional. Leave blank to keep the saved connection.",
        "txtUserUPN": "Corporate user email address",
        "ddUserRole": "Application role",
        "galRequests": "Recent intake requests",
        "galRecords": "Validation results",
        "galHistory": "Request audit history",
        "galUsers": "Application users and access status",
    }
    item_labels = {
        "galRequests": '"Request " & ThisItem.request_id & ", " & ThisItem.status & If(!IsBlank(ThisItem.source_id),", source " & ThisItem.source_id,"")',
        "galRecords": '"Record " & Text(ThisItem.record_sequence) & ", " & ThisItem.status & ", " & Text(CountRows(ThisItem.issues)) & " validation issues"',
        "galHistory": 'ThisItem.event_type & ", " & Text(ThisItem.occurred_at,DateTimeFormat.ShortDateTime) & ", actor " & Coalesce(ThisItem.actor,"not recorded")',
        "galUsers": 'ThisItem.display_name & ", " & ThisItem.role & ", " & ThisItem.access_state',
    }
    row_text = {
        "RequestRow": '"Open request " & Coalesce(ThisItem.source_id,ThisItem.request_id) & " | " & ThisItem.status',
        "btnOpenReview": '"Review record " & Text(ThisItem.record_sequence)',
        "UserRow": '"Select " & ThisItem.display_name & " | " & ThisItem.role & " | " & ThisItem.access_state & If(ThisItem.role="OWNER"," | protected","")',
        "chkEnabled": '"Enable database"',
    }
    messages = {"IntakeMessage", "ResultsMessage", "ReviewMessage", "HistoryMessage", "ConfigurationMessage", "UsersMessage"}
    keyboard = {"Classic/Button", "Classic/TextInput", "Classic/DropDown", "Classic/CheckBox"}

    def visit(controls):
        for item in controls:
            name, node = next(iter(item.items()))
            props = node["Properties"]
            kind = node["Control"]
            if name in labels:
                props["AccessibleLabel"] = "=" + quoted(labels[name])
            if name in item_labels:
                props["ItemAccessibleLabel"] = "=" + item_labels[name]
            if name in row_text:
                props["Text"] = "=" + row_text[name]
            if kind in keyboard:
                props["TabIndex"] = "=0"
                props["FocusedBorderThickness"] = "=3"
                # Buttons use the existing foreground/background contrast pair;
                # white input surfaces and the checkbox use a dark indicator.
                props["FocusedBorderColor"] = "=Self.Color" if kind == "Classic/Button" else "=RGBA(0,0,0,1)"
            if name in messages:
                props["Live"] = "=Live.Polite"
            visit(node.get("Children", []))

    for controls in screens.values():
        visit(controls)


def render():
    screens = build_business()
    screens["scrConfiguration"] = build_configuration()
    screens["scrUsers"] = build_users()
    apply_accessibility(screens)
    files = {}
    startup = ('Set(varBusy,true); Set(varEnvironmentReady,false); '
               + guarded(identity(), 'Clear(colCapabilities); ' + message("Sign-in or app access could not be verified.")) + '; '
               'If("business" in colCapabilities.Value,' + guarded(health() + '; ' + invoke('GetIntakeWorkflow',raw='varWorkflowRaw') + '; Set(varActiveIntake,Text(varWorkflowRaw.active_request_id))','Set(varEnvironmentReady,false)') + '); Set(varBusy,false)')
    for profile in ("stage","prod"):
        flow = "MILSTRIP" + profile.title() + "Broker"
        for name,controls in screens.items():
            text = yaml.safe_dump(controls,sort_keys=False,allow_unicode=True,width=110)
            files[f"{profile}/{name}.controls.yaml"] = text.replace("__FLOW__",flow)
        files[f"{profile}/app-environment.fx"] = f'AppEnvironment = "{profile}";\n'
        files[f"{profile}/app-onstart.fx"] = startup.replace("__FLOW__",flow) + ";\n"
        files[f"{profile}/screen-events.json"] = json.dumps({
            "scrIntake":{"OnVisible":"false"},
            "scrResults":{"OnVisible":"false"},
            "scrReview":{"OnVisible":"false"},
            "scrHistory":{"OnVisible":"false"},
            "scrConfiguration":{"OnVisible":'Set(varMessage,If(!IsBlank(varAdminCommand.command_id),"Configuration change is pending. Check command status or retry the same command.","")); If(!IsBlank(varAdminCommand.command_id) || !IsBlank(varDraft.draft_id),false,Select(btnLoadConfiguration))'},
            "scrUsers":{"OnVisible":'Set(varMessage,If(!IsBlank(varUserCommand.command_id),"Access change is pending. Check command status or retry sharing.","")); Select(btnLoadUsers)'}},indent=2) + "\n"
    files["manifest.json"] = json.dumps({"version":1,"status":"SOURCE_REQUIRES_NATIVE_COMPILATION_AND_ACCEPTANCE",
        "screens":list(SCREENS),"profiles":{p:{"flow":"MILSTRIP"+p.title()+"Broker","directory":p} for p in ("stage","prod")},
        "app_properties":{"Formulas":"app-environment.fx","OnStart":"app-onstart.fx","StartScreen":"scrIntake"},
        "requirements":["Bind only the matching broker flow", "Apply screen-events.json OnVisible properties",
                        "Enable formula-level error management", "Compile and test in Power Apps Studio",
                        "Complete trusted broker acceptance before enforcing broker-only access"]},indent=2)+"\n"
    return files


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    for relative,text in render().items():
        path=OUTPUT/relative
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8")!=text:
                raise SystemExit("Canvas broker source differs: "+relative)
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(text,encoding="utf-8",newline="\n")
    print("Canvas broker source matches" if args.check else "Built broker Canvas source; no deployment performed")


if __name__=="__main__":
    main()
