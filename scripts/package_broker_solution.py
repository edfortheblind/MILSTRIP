"""Build an Off-only broker delta for the existing unmanaged MILSTRIP solution.

Uses the native export as its XML authority and the deterministic flow builder
as its only workflow source. It never deploys or alters Canvas/connector files.
Connection IDs and tenant bindings remain in an explicitly private output path.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import sys
from uuid import UUID
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_broker_flows import API_PREFIX, APIS, build, validate_bindings

STAGE_ID = "04d6229f-5ab8-f111-aaac-7ced8d6f317c"
BASELINE_NAME = "MILSTRIP-broker-baseline-20260924.zip"
PACKAGE_NAME = "MILSTRIP-broker-flows.zip"
CONTENT_NAMESPACE = "http://schemas.openxmlformats.org/package/2006/content-types"
ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")


def baseline_path():
    return Path(os.environ["LOCALAPPDATA"]) / "MILSTRIP" / "backups" / BASELINE_NAME


def xml_bytes(element):
    ET.indent(element, space="  ")
    return ET.tostring(element, encoding="utf-8", xml_declaration=True) + b"\n"


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def required(parent, path):
    node = parent.find(path)
    if node is None:
        raise ValueError("Native solution structure is incomplete")
    return node


def binding_rows(bindings):
    rows = []
    for key, api in APIS.items():
        entry = bindings["shared_connections"][key]
        rows.append({"LogicalName": entry["logical_name"], "ConnectionId": entry["connection_name"],
                     "ConnectorId": API_PREFIX + api, "display_name": "MILSTRIP " + key.title()})
    for profile in ("stage", "prod"):
        entry = bindings["profiles"][profile]
        rows.append({"LogicalName": entry["broker_reference"], "ConnectionId": entry["broker_connection"],
                     "ConnectorId": bindings["connector_api_id"], "display_name": "MILSTRIP " + profile.title() + " Broker"})
    if len({row["LogicalName"].casefold() for row in rows}) != 6:
        raise ValueError("All six connection references must have distinct logical names")
    if any(not row["LogicalName"].lower().startswith("tab_") for row in rows):
        raise ValueError("Connection references must use the existing TAB publisher prefix")
    return sorted(rows, key=lambda row: row["LogicalName"])


def prepare_entries(baseline, bindings):
    """Return native ZIP members and settings without writing any files."""
    validate_bindings(bindings)
    if str(UUID(bindings["profiles"]["stage"]["flow_id"])) != STAGE_ID:
        raise ValueError("Stage must reuse the existing workflow ID")
    with zipfile.ZipFile(baseline) as archive:
        # Parse the native metadata only; no Canvas, connector, image or prior
        # flow definition is copied into the delta.
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("Duplicate native package entries are not supported")
        solution = ET.fromstring(archive.read("solution.xml"))
        customizations = ET.fromstring(archive.read("customizations.xml"))
    manifest = required(solution, "SolutionManifest")
    publisher = required(manifest, "Publisher")
    if (required(manifest, "UniqueName").text != "MILSTRIP" or required(manifest, "Managed").text != "0"
            or required(publisher, "UniqueName").text != "TAB"
            or required(publisher, "CustomizationPrefix").text != "tab"):
        raise ValueError("Baseline must be the existing unmanaged MILSTRIP/TAB solution")
    roots = required(manifest, "RootComponents")
    if not any(node.get("type") == "29" and node.get("id", "").strip("{}").lower() == STAGE_ID for node in roots):
        raise ValueError("The native baseline does not contain the existing Stage workflow")
    workflows = required(customizations, "Workflows")
    matches = [node for node in workflows if node.get("WorkflowId", "").strip("{}").lower() == STAGE_ID]
    if len(matches) != 1:
        raise ValueError("Stage workflow metadata is ambiguous")
    template = deepcopy(matches[0])
    if required(template, "Category").text != "5" or required(template, "Type").text != "1":
        raise ValueError("Stage baseline must be a native cloud flow definition")
    rows = binding_rows(bindings)
    # Keep only inert native skeleton elements plus flow/ref/language metadata.
    # Unexpected populated components are dropped, never copied into a delta.
    for child in list(customizations):
        if child.tag in {"CanvasApps", "Connectors"}:
            customizations.remove(child)
        elif child.tag not in {"Workflows", "connectionreferences", "Languages"} and len(child):
            customizations.remove(child)
    workflows.clear()
    connections = customizations.find("connectionreferences")
    if connections is None:
        connections = ET.SubElement(customizations, "connectionreferences")
    connections.clear()
    roots.clear()
    dependencies = manifest.find("MissingDependencies")
    if dependencies is not None:
        # The native baseline includes the connector itself. The delta relies
        # on that already-installed connector instead of replacing it.
        dependencies.clear()
    entries = {}
    flows = build(bindings)
    for profile in ("stage", "prod"):
        flow_id = str(UUID(bindings["profiles"][profile]["flow_id"]))
        display = "MILSTRIP " + profile.title() + " Broker"
        filename = "Workflows/MILSTRIP" + profile.title() + "Broker-" + flow_id.upper() + ".json"
        workflow = deepcopy(template)
        workflow.set("WorkflowId", "{" + flow_id + "}")
        workflow.set("Name", display)
        for tag, value in {"JsonFileName": "/" + filename, "StateCode": "0", "StatusCode": "1"}.items():
            required(workflow, tag).text = value
        localized = required(workflow, "LocalizedNames")
        for name in localized:
            name.set("description", display)
        workflows.append(workflow)
        ET.SubElement(roots, "RootComponent", type="29", id="{" + flow_id + "}", behavior="0")
        entries[filename] = json_bytes(flows[profile])
    for row in rows:
        reference = ET.SubElement(connections, "connectionreference", connectionreferencelogicalname=row["LogicalName"])
        for tag, value in {"connectionreferencedisplayname": row["display_name"], "connectorid": row["ConnectorId"],
                           "iscustomizable": "1", "promptingbehavior": "0", "statecode": "0", "statuscode": "1"}.items():
            ET.SubElement(reference, tag).text = value
    # Native exports include dependent connection references in customizations,
    # without inventing extra RootComponent IDs (same shape as this baseline).
    content_types = ET.Element("Types", xmlns=CONTENT_NAMESPACE)
    for extension in ("xml", "json"):
        ET.SubElement(content_types, "Default", Extension=extension, ContentType="application/octet-stream")
    entries.update({"solution.xml": xml_bytes(solution), "customizations.xml": xml_bytes(customizations),
                    "[Content_Types].xml": xml_bytes(content_types)})
    settings = {"EnvironmentVariables": [], "ConnectionReferences": [
        {key: row[key] for key in ("LogicalName", "ConnectionId", "ConnectorId")} for row in rows]}
    return entries, settings


def package_bytes(entries):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            info.create_system = 3
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return stream.getvalue()


def private_path(path):
    absolute = path.absolute()
    resolved = absolute.resolve()
    if ".cred" not in resolved.parts or absolute != resolved:
        raise ValueError("Bindings and output must be inside a real private .cred directory")
    return resolved


def write_package(baseline, bindings, output):
    output = private_path(Path(output))
    entries, settings = prepare_entries(baseline, bindings)
    content = package_bytes(entries)
    output.mkdir(parents=True, exist_ok=True)
    package = output / PACKAGE_NAME
    package.write_bytes(content)
    (output / "deployment-settings.json").write_bytes(json_bytes(settings))
    evidence = {"status": "PACKAGED_OFF_NOT_IMPORTED", "solution": "MILSTRIP", "publisher": "TAB",
        "package_sha256": hashlib.sha256(content).hexdigest(),
        "baseline_sha256": hashlib.sha256(Path(baseline).read_bytes()).hexdigest(),
        "flow_count": 2, "connection_reference_count": 6, "initial_state": "Off",
        "excluded": ["CanvasApps", "Connectors"],
        "members": {key: hashlib.sha256(value).hexdigest() for key, value in sorted(entries.items())}}
    (output / "package-evidence.json").write_bytes(json_bytes(evidence))
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=baseline_path())
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        bindings = json.loads(private_path(args.bindings).read_text(encoding="utf-8"))
        evidence = write_package(args.baseline, bindings, args.output)
    except (OSError, ValueError, KeyError, ET.ParseError, zipfile.BadZipFile):
        print("Package not created. Verify the native baseline, reviewed bindings and private output directory.")
        return 1
    print("Packaged two Off workflows and six connection references; no deployment performed.")
    print("SHA256: " + evidence["package_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
