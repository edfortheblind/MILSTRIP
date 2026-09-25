"""Native solution-delta shape and reproducibility; no tenant writes."""
from copy import deepcopy
import io
import json
import os
from pathlib import Path
from uuid import uuid4
import xml.etree.ElementTree as ET
import zipfile

import pytest

from scripts.build_broker_flows import APIS, build, default_bindings
from scripts.package_broker_solution import STAGE_ID, baseline_path, package_bytes, prepare_entries, write_package


def bindings():
    value = default_bindings()
    value.update(tenant_id=str(uuid4()),environment_name="Default-"+str(uuid4()),
                 deployed_owner_object_id=str(uuid4()),management_metadata_verified=True)
    value["shared_connections"] = {key:{"logical_name":"tab_test_"+key,"connection_name":"synthetic-"+key} for key in APIS}
    for profile in ("stage","prod"):
        value["profiles"][profile].update(flow_id=STAGE_ID if profile=="stage" else str(uuid4()),
                                          broker_reference="tab_test_broker_"+profile,broker_connection="synthetic-broker-"+profile)
    return value


@pytest.fixture
def native(tmp_path):
    path=tmp_path/"native.zip"
    solution=f'''<ImportExportXml version="9.2"><SolutionManifest><UniqueName>MILSTRIP</UniqueName><Version>1.0.0.0</Version><Managed>0</Managed><Publisher><UniqueName>TAB</UniqueName><CustomizationPrefix>tab</CustomizationPrefix><CustomizationOptionValuePrefix>92805</CustomizationOptionValuePrefix></Publisher><RootComponents><RootComponent type="29" id="{{{STAGE_ID}}}" behavior="0"/><RootComponent type="300" schemaName="existing_canvas"/><RootComponent type="372" schemaName="existing_connector"/></RootComponents><MissingDependencies/></SolutionManifest></ImportExportXml>'''
    custom=f'''<ImportExportXml><Entities/><Roles/><Workflows><Workflow WorkflowId="{{{STAGE_ID}}}" Name="MILSTRIP Stage Broker"><JsonFileName>/Workflows/existing.json</JsonFileName><Type>1</Type><Category>5</Category><StateCode>1</StateCode><StatusCode>2</StatusCode><PrimaryEntity>none</PrimaryEntity><LocalizedNames><LocalizedName languagecode="1033" description="MILSTRIP Stage Broker"/></LocalizedNames></Workflow></Workflows><CanvasApps><CanvasApp>EXCLUDED_CANVAS</CanvasApp></CanvasApps><Connectors><Connector>EXCLUDED_CONNECTOR</Connector></Connectors><connectionreferences><connectionreference connectionreferencelogicalname="tab_old"/></connectionreferences><Languages><Language>1033</Language></Languages></ImportExportXml>'''
    with zipfile.ZipFile(path,"w") as archive:
        archive.writestr("solution.xml",solution)
        archive.writestr("customizations.xml",custom)
        archive.writestr("CanvasApps/private.msapp",b"EXCLUDED_CANVAS_BINARY")
        archive.writestr("Connector/private.json",b"EXCLUDED_CONNECTOR_BINARY")
    return path


def test_delta_reuses_solution_and_stage_id_and_contains_only_off_flows(native):
    chosen=bindings()
    before=native.read_bytes()
    entries,settings=prepare_entries(native,chosen)
    assert native.read_bytes()==before
    assert len(entries)==5
    assert set(entries)-{"solution.xml","customizations.xml","[Content_Types].xml"}=={
        "Workflows/MILSTRIP"+profile.title()+"Broker-"+chosen["profiles"][profile]["flow_id"].upper()+".json" for profile in ("stage","prod")}
    assert not any(token in b"\n".join(entries.values()) for token in (b"EXCLUDED_CANVAS",b"EXCLUDED_CONNECTOR"))
    solution=ET.fromstring(entries["solution.xml"])
    baseline=ET.fromstring(zipfile.ZipFile(native).read("solution.xml"))
    assert ET.tostring(solution.find("SolutionManifest/Publisher"),encoding="unicode").replace("\n","").replace(" ","")==ET.tostring(baseline.find("SolutionManifest/Publisher"),encoding="unicode").replace("\n","").replace(" ","")
    assert solution.findtext("SolutionManifest/UniqueName")=="MILSTRIP"
    assert solution.findtext("SolutionManifest/Managed")=="0"
    assert {node.get("type") for node in solution.findall("SolutionManifest/RootComponents/RootComponent")}=={"29"}
    custom=ET.fromstring(entries["customizations.xml"])
    assert custom.find("CanvasApps") is None and custom.find("Connectors") is None
    workflows=custom.findall("Workflows/Workflow")
    assert len(workflows)==2
    assert all(node.findtext("StateCode")=="0" and node.findtext("StatusCode")=="1" for node in workflows)
    for profile in ("stage","prod"):
        node=next(node for node in workflows if profile.title() in node.get("Name"))
        assert json.loads(entries[node.findtext("JsonFileName").lstrip("/")])==build(chosen)[profile]
    refs=custom.findall("connectionreferences/connectionreference")
    assert len(refs)==len(settings["ConnectionReferences"])==len(APIS)+2
    assert {node.get("connectionreferencelogicalname") for node in refs}=={row["LogicalName"] for row in settings["ConnectionReferences"]}
    assert all(set(row)=={"LogicalName","ConnectionId","ConnectorId"} for row in settings["ConnectionReferences"])


def test_permissions_connection_is_embedded_and_included_in_package_settings(native):
    chosen=bindings()
    entries,settings=prepare_entries(native,chosen)
    permission=chosen["shared_connections"]["permissions"]
    assert APIS["permissions"]=="shared_webcontents"
    assert next(row for row in settings["ConnectionReferences"] if row["LogicalName"]==permission["logical_name"])=={
        "LogicalName":permission["logical_name"],
        "ConnectionId":permission["connection_name"],
        "ConnectorId":"/providers/Microsoft.PowerApps/apis/shared_webcontents",
    }
    custom=ET.fromstring(entries["customizations.xml"])
    references=custom.findall("connectionreferences/connectionreference")
    packaged=next(node for node in references if node.get("connectionreferencelogicalname")==permission["logical_name"])
    assert packaged.findtext("connectorid")=="/providers/Microsoft.PowerApps/apis/shared_webcontents"
    for name,content in entries.items():
        if name.startswith("Workflows/"):
            reference=json.loads(content)["properties"]["connectionReferences"]["permissions"]
            assert reference=={
                "runtimeSource":"embedded",
                "connection":{"connectionReferenceLogicalName":permission["logical_name"],"name":permission["connection_name"]},
                "api":{"name":"shared_webcontents"},
            }


def test_identical_inputs_make_identical_zip_bytes(native):
    chosen=bindings()
    first,_=prepare_entries(native,chosen)
    second,_=prepare_entries(native,chosen)
    assert package_bytes(first)==package_bytes(second)
    with zipfile.ZipFile(io.BytesIO(package_bytes(first))) as archive:
        assert all(info.date_time==(1980,1,1,0,0,0) for info in archive.infolist())


def test_package_writes_only_under_explicit_private_directory(native,tmp_path):
    chosen=bindings()
    with pytest.raises(ValueError,match="private"):
        write_package(native,chosen,tmp_path/"public")
    output=tmp_path/".cred"/"package"
    result=write_package(native,chosen,output)
    assert result["status"]=="PACKAGED_OFF_NOT_IMPORTED"
    assert result["connection_reference_count"]==len(APIS)+2
    assert result["flow_count"]==2 and result["initial_state"]=="Off"
    assert set(path.name for path in output.iterdir())=={"MILSTRIP-broker-flows.zip","deployment-settings.json","package-evidence.json"}


def test_wrong_stage_id_or_reference_collision_is_rejected(native):
    chosen=bindings()
    chosen["profiles"]["stage"]["flow_id"]=str(uuid4())
    with pytest.raises(ValueError,match="reuse"):
        prepare_entries(native,chosen)
    chosen=bindings()
    chosen["profiles"]["prod"]["broker_reference"]=chosen["shared_connections"]["makers"]["logical_name"]
    with pytest.raises(ValueError,match="distinct"):
        prepare_entries(native,chosen)


@pytest.mark.parametrize("collision",["shared","broker"])
def test_permissions_reference_collision_is_rejected_case_insensitively(native,collision):
    chosen=bindings()
    name=(chosen["shared_connections"]["makers"]["logical_name"] if collision=="shared"
          else chosen["profiles"]["prod"]["broker_reference"])
    chosen["shared_connections"]["permissions"]["logical_name"]=name.upper()
    with pytest.raises(ValueError,match="distinct"):
        prepare_entries(native,chosen)


def test_available_real_native_export_can_be_projected_without_altering_it():
    if not os.environ.get("LOCALAPPDATA") or not baseline_path().is_file():
        pytest.skip("Native local export is not present")
    before=baseline_path().read_bytes()
    entries,settings=prepare_entries(baseline_path(),bindings())
    assert len(entries)==5 and len(settings["ConnectionReferences"])==len(APIS)+2
    assert baseline_path().read_bytes()==before
