"""Assemble inspection-only six-screen YAML beside unchanged native resources.

This does not implement the executable app. PAC pack/unpack can roundtrip the
YAML while native controls and data sources still contain the old app. Apply the
generated controls and formulas through Studio; never deploy these copies.
"""
from argparse import ArgumentParser
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from xml.etree import ElementTree
from zipfile import ZipFile

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_broker_canvas import OUTPUT, SCREENS, stages

DEFAULT_BASELINE = Path(os.environ.get("LOCALAPPDATA", ".")) / "MILSTRIP/ui/stage-source-baseline"
VERSIONED = re.compile(r"^([A-Za-z][A-Za-z0-9/]*)@(\d+\.\d+\.\d+)$")


def digest(content):
    return hashlib.sha256(content).hexdigest()


def walk_controls(children):
    for item in children:
        if not isinstance(item, dict) or len(item) != 1:
            raise ValueError("Each child must contain exactly one named control")
        name, control = next(iter(item.items()))
        yield name, control
        yield from walk_controls(control.get("Children", []))


def native_checkbox_version(path):
    """Read an actual native template, including its matching XML version."""
    with ZipFile(path) as archive:
        candidates = [name for name in archive.namelist() if name in (
            "References/Templates.json", "msapp/References/Templates.json")]
        if len(candidates) != 1:
            raise ValueError("Native control metadata must contain one template inventory")
        templates = json.loads(archive.read(candidates[0]))["UsedTemplates"]
    versions = set()
    for template in templates:
        if template.get("Name") == "checkbox":
            version = template["Version"]
            element = ElementTree.fromstring(template["Template"])
            if (element.attrib.get("version") != version or
                    element.attrib.get("id") != "http://microsoft.com/appmagic/checkbox"):
                raise ValueError("Checkbox template identity or version mismatch")
            if not re.fullmatch(r"\d+\.\d+\.\d+", version):
                raise ValueError("Invalid native checkbox version")
            versions.add(version)
    if len(versions) != 1:
        raise ValueError("Native checkbox metadata must identify exactly one version")
    return next(iter(versions))


def yaml_bytes(value):
    return yaml.safe_dump(value, sort_keys=False, allow_unicode=True, width=120).encode("utf-8")


def assemble_entries(baseline, profile, *, generated=OUTPUT, checkbox_metadata=None):
    baseline, generated = Path(baseline), Path(generated)
    if profile not in {"stage", "prod"}:
        raise ValueError("Profile must be stage or prod")
    files = {}
    for path in sorted(baseline.rglob("*")):
        if path.is_symlink():
            raise ValueError("Native baseline may not contain symbolic links")
        if path.is_file():
            files[path.relative_to(baseline).as_posix()] = path.read_bytes()
    resources = [name for name in files if name.endswith(".msapr")]
    if len(resources) != 1 or "Src/App.pa.yaml" not in files:
        raise ValueError("Expected PAC SourceCode baseline with one native resource container")
    screens, versions, named_versions = {}, {}, {}
    screen_files = []
    for name, content in files.items():
        if name.startswith("Src/") and name.endswith(".pa.yaml"):
            document = yaml.safe_load(content)
            if not isinstance(document, dict):
                raise ValueError("Invalid native YAML document")
            if "Screens" not in document:
                continue
            screen_files.append(name)
            for screen_name, screen in document["Screens"].items():
                if screen_name in screens:
                    raise ValueError("Duplicate native screen")
                screens[screen_name] = screen
                for control_name, control in walk_controls(screen.get("Children", [])):
                    match = VERSIONED.fullmatch(control["Control"])
                    if not match:
                        raise ValueError("Native controls must specify their actual version")
                    kind, version = match.groups()
                    versions.setdefault(kind, set()).add(version)
                    named_versions[control_name] = (kind, version)
    if "scrIntake" not in screens:
        raise ValueError("Native intake screen is required")
    extras = set(screens).difference(SCREENS)
    if extras - {"Screen1"}:
        raise ValueError("Unexpected extra native screen; review before replacing it")
    if "Screen1" in extras:
        boilerplate = screens["Screen1"]
        properties = [boilerplate.get("Properties", {})]
        properties += [control.get("Properties", {}) for _, control in walk_controls(boilerplate.get("Children", []))]
        if any(key.startswith("On") and value not in ("=", "", "=false") for props in properties for key, value in props.items()):
            raise ValueError("Screen1 contains behavior; removal requires an explicit review")
    checkbox_evidence = None
    if "Classic/CheckBox" not in versions:
        metadata = Path(checkbox_metadata) if checkbox_metadata else baseline / resources[0]
        version = native_checkbox_version(metadata)
        versions["Classic/CheckBox"] = {version}
        checkbox_evidence = {"native_metadata_sha256": digest(metadata.read_bytes()), "version": version}
    for name in screen_files:
        del files[name]
    events = json.loads((generated / profile / "screen-events.json").read_text(encoding="utf-8"))
    if set(events) != set(SCREENS) or any("OnVisible" not in events[name] for name in SCREENS):
        raise ValueError("Every screen must explicitly replace its native OnVisible behavior")
    used_names = set()
    used_versions = set()
    for screen_name in SCREENS:
        screen = deepcopy(screens.get(screen_name, {"Properties": {
            key: value for key, value in screens["scrIntake"].get("Properties", {}).items()
            if key in {"Fill", "LoadingSpinnerColor"}}}))
        screen.setdefault("Properties", {}).pop("OnVisible", None)
        screen["Properties"]["OnVisible"] = "=" + (events[screen_name]["OnVisible"].lstrip("=") or "false")
        screen["Children"] = yaml.safe_load((generated / profile / f"{screen_name}.controls.yaml").read_text(encoding="utf-8"))
        for control_name, control in walk_controls(screen["Children"]):
            if control_name in used_names:
                raise ValueError("Control names must be unique across the app")
            used_names.add(control_name)
            kind = control["Control"]
            preferred = named_versions.get(control_name)
            if preferred and preferred[0] == kind:
                version = preferred[1]
            elif len(versions.get(kind, set())) == 1:
                version = next(iter(versions[kind]))
            else:
                raise ValueError("Missing or ambiguous native control version: " + kind)
            control["Control"] = kind + "@" + version
            used_versions.add(control["Control"])
        files[f"Src/{screen_name}.pa.yaml"] = yaml_bytes({"Screens": {screen_name: screen}})
    app = yaml.safe_load(files["Src/App.pa.yaml"])
    properties = app["App"].setdefault("Properties", {})
    existing = properties.get("Formulas", "").lstrip("=")
    retained = [part for part in stages(existing) if not re.match(r"^AppEnvironment\s*=", part)]
    environment = (generated / profile / "app-environment.fx").read_text(encoding="utf-8").strip()
    properties["Formulas"] = "=" + "; ".join(retained + [environment.rstrip(";")]) + ";"
    properties["OnStart"] = "=" + (generated / profile / "app-onstart.fx").read_text(encoding="utf-8").strip().lstrip("=")
    properties["StartScreen"] = "=scrIntake"
    files["Src/App.pa.yaml"] = yaml_bytes(app)
    editor = yaml.safe_load(files.get("Src/_EditorState.pa.yaml", b"EditorState: {}"))
    editor["EditorState"]["ScreensOrder"] = list(SCREENS)
    files["Src/_EditorState.pa.yaml"] = yaml_bytes(editor)
    source = "\n".join(content.decode("utf-8") for name, content in files.items() if name.startswith("Src/") and name.endswith(".pa.yaml"))
    if "MILSTRIPLocalDevAPI" in source or "MILSTRIP" + ({"stage": "Prod", "prod": "Stage"}[profile]) + "Broker.Run" in source:
        raise ValueError("Unexpected direct connector or opposite-profile flow in assembled source")
    evidence = {"artifact_kind": "inspection_only", "deployable": False,
                "executable_controls_changed": False,
                "profile": profile, "screens": list(SCREENS), "controls": len(used_names),
                "control_versions": sorted(used_versions), "resource_sha256": digest(files[resources[0]]),
                "resource_file": resources[0], "supplemental_checkbox": checkbox_evidence,
                "validation": "YAML inspection only. Native executable controls and data sources remain unchanged; do not deploy."}
    files["assembly-evidence.json"] = (json.dumps(evidence, indent=2, sort_keys=True) + "\n").encode()
    files["INSPECTION_ONLY.txt"] = (
        "DO NOT DEPLOY. This directory changes review YAML only.\n"
        "Native executable controls and data-source dependencies remain the baseline app.\n"
        "Implement controls, formulas and matching flow dependencies in Power Apps Studio.\n"
    ).encode()
    return files, evidence


def write_assembly(baseline, output, profile, **kwargs):
    baseline, output = Path(baseline).resolve(), Path(output).resolve()
    if output == baseline or output in baseline.parents or baseline in output.parents:
        raise ValueError("Assembly output must be separate from the immutable native baseline")
    files, evidence = assemble_entries(baseline, profile, **kwargs)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Assembly output must be empty; existing output is never overwritten")
    output.mkdir(parents=True, exist_ok=True)
    for name, content in sorted(files.items()):
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    return evidence


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--profile", choices=("stage", "prod"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkbox-metadata", type=Path, help="Native MSAPP/MSAPR with a verified checkbox template when absent from baseline")
    args = parser.parse_args()
    try:
        evidence = write_assembly(args.baseline, args.output, args.profile, checkbox_metadata=args.checkbox_metadata)
    except (OSError, ValueError, KeyError, yaml.YAMLError) as exc:
        parser.exit(1, "Assembly refused: " + str(exc) + "\n")
    print(f"Assembled {args.profile}: {len(evidence['screens'])} screens, {evidence['controls']} controls.")
    print("INSPECTION ONLY: executable controls and data sources are unchanged. Do not deploy.")


if __name__ == "__main__":
    main()
