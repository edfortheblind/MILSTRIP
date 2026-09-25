"""Preview the reviewed canceled run; explicit apply always recollects via TAB SSO.

Captured JSON is accepted only with --offline-evidence for a read-only preview.
This command never grants permissions or activates app access.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.control import ControlError, ControlStore
from api.sharing_recovery import (HISTORICAL, REASON, NativeRecoveryCollector,
                                 RecoveryRequest, RecoveryService, preview_captured_evidence)


def read_projection(path):
    if path.stat().st_size > 2_097_152:
        raise ControlError(422, "Recovery metadata exceeds its fixed size bound")
    return json.loads(path.read_text(encoding="utf-8-sig"))


class PowerShellRecoveryCollector(NativeRecoveryCollector):
    """Fixed live script invocation; no evidence input or alternate URL path."""

    def collect(self):
        shell = shutil.which("powershell.exe") or shutil.which("pwsh")
        if shell is None:
            raise ControlError(503, "Microsoft-authenticated PowerShell collection is unavailable")
        with tempfile.TemporaryDirectory(prefix="milstrip-recovery-metadata-") as directory:
            output = Path(directory) / "fresh-evidence.json"
            result = subprocess.run([shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                str(ROOT / "scripts" / "Read-SharingRecoveryEvidence.ps1"), "-OutputFile", str(output)],
                capture_output=True, text=True, timeout=180,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if result.returncode != 0 or not output.is_file():
                # Native diagnostics/payloads are never forwarded by recovery.
                raise ControlError(503, "Fresh authenticated recovery collection did not complete")
            return read_projection(output)


def request_for_state(state):
    plan = state["sharing_plans"].get(HISTORICAL["plan_id"])
    if plan is None:
        raise ControlError(404, "The reviewed historical sharing plan was not found")
    return RecoveryRequest(**{key: HISTORICAL[key] for key in
        ("command_id", "plan_id", "execution_id", "lease_id")}, revision=plan["revision"], intent=REASON)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-file", type=Path)
    parser.add_argument("--offline-evidence", type=Path, help="Read-only qualification of captured metadata; never permits apply")
    parser.add_argument("--apply", action="store_true", help="Recollect live proof and apply the exact reviewed transition")
    parser.add_argument("--expected-control-revision")
    parser.add_argument("--evidence-digest")
    args = parser.parse_args(argv)
    if args.apply and args.offline_evidence:
        parser.error("--offline-evidence is read-only and cannot be combined with --apply")
    if args.apply and (not args.expected_control_revision or not args.evidence_digest):
        parser.error("--apply requires the control revision and evidence digest from a live preview")
    if not args.apply and (args.expected_control_revision or args.evidence_digest):
        parser.error("Preview does not accept apply approval values")
    try:
        store = ControlStore(args.control_file)
        state = store.read()
        request = request_for_state(state)
        if args.offline_evidence:
            result = preview_captured_evidence(state, request, read_projection(args.offline_evidence))
        else:
            service = RecoveryService(store, PowerShellRecoveryCollector())
            result = (service.apply(request, expected_revision=args.expected_control_revision,
                                    evidence_digest=args.evidence_digest) if args.apply else service.preview(request))
    except ControlError as error:
        print(json.dumps({"changed": None if args.apply else False, "error": "RECOVERY_NOT_CONFIRMED", "status": error.status_code,
                          "detail": error.message}))
        return 1
    except Exception:
        print(json.dumps({"changed": None if args.apply else False, "error": "RECOVERY_NOT_CONFIRMED", "status": 503,
                          "detail": "Check current authority, retained command and fresh native evidence"}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
