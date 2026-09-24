"""The assembler changes review YAML, never the native executable app."""
import io
import json
from zipfile import ZipFile

import pytest
import yaml

from scripts.assemble_broker_canvas import assemble_entries, native_checkbox_version, write_assembly
from scripts.build_broker_canvas import SCREENS, render


def template_archive(path, version="2.1.0", xml_version=None):
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("msapp/References/Templates.json", json.dumps({"UsedTemplates": [{
            "Name": "checkbox", "Version": version, "Template":
            f'<widget id="http://microsoft.com/appmagic/checkbox" version="{xml_version or version}" />'}]}))
        archive.writestr("msapp/References/DataSources.json", '{"flow":"retained-native-flow"}')
        archive.writestr("msapp/Controls/1.json", '{"OnStart":"LegacySharedConnector.GetHealth()"}')
        archive.writestr("msapp/Assets/icon.png", b"native-media-bytes")
    path.write_bytes(buffer.getvalue())


@pytest.fixture
def baseline(tmp_path):
    root = tmp_path / "native"
    source = root / "Src"
    source.mkdir(parents=True)
    template_archive(root / "native.msapr")
    app = {"App": {"Properties": {"Theme": "=NativeTheme", "Formulas": '=AppEnvironment="stage"; Brand="Keep; me";'}}}
    (source / "App.pa.yaml").write_text(yaml.safe_dump(app), encoding="utf-8")
    types = {"Classic/Button": "2.2.0", "Classic/DropDown": "2.3.1", "Classic/TextInput": "2.3.2",
             "Gallery": "2.15.0", "Image": "2.2.3", "Label": "2.5.1"}
    controls = [{f"Baseline{i}": {"Control": f"{kind}@{version}", "Properties": {}}}
                for i, (kind, version) in enumerate(types.items())]
    screen = {"Screens": {"scrIntake": {"Properties": {"Fill": "=NativeFill", "OnVisible": "=MILSTRIPLocalDevAPI.GetHealth()"}, "Children": controls}}}
    (source / "scrIntake.pa.yaml").write_text(yaml.safe_dump(screen), encoding="utf-8")
    (source / "Screen1.pa.yaml").write_text(yaml.safe_dump({"Screens": {"Screen1": {"Properties": {}, "Children": []}}}), encoding="utf-8")
    (source / "_EditorState.pa.yaml").write_text(yaml.safe_dump({"EditorState": {"ScreensOrder": ["Screen1", "scrIntake"], "OtherNativeState": True}}), encoding="utf-8")
    (root / "native-manifest.json").write_bytes(b'{"preserve":"exact bytes"}')
    return root


@pytest.mark.parametrize("profile", ["stage", "prod"])
def test_assembly_preserves_native_app_and_changes_only_review_yaml(baseline, profile):
    before = {p.relative_to(baseline).as_posix(): p.read_bytes() for p in baseline.rglob("*") if p.is_file()}
    files, evidence = assemble_entries(baseline, profile)
    assert files == assemble_entries(baseline, profile)[0]
    assert files["native.msapr"] == before["native.msapr"]
    assert files["native-manifest.json"] == before["native-manifest.json"]
    assert before == {p.relative_to(baseline).as_posix(): p.read_bytes() for p in baseline.rglob("*") if p.is_file()}
    assert "Src/Screen1.pa.yaml" not in files
    assert evidence["screens"] == list(SCREENS)
    assert evidence["artifact_kind"] == "inspection_only"
    assert evidence["deployable"] is False and evidence["executable_controls_changed"] is False
    assert b"DO NOT DEPLOY" in files["INSPECTION_ONLY.txt"]
    with ZipFile(io.BytesIO(files["native.msapr"])) as archive:
        assert b"LegacySharedConnector.GetHealth()" in archive.read("msapp/Controls/1.json")
    assert "Classic/CheckBox@2.1.0" in evidence["control_versions"]
    app = yaml.safe_load(files["Src/App.pa.yaml"])["App"]["Properties"]
    assert app["Theme"] == "=NativeTheme"
    assert f'AppEnvironment = "{profile}"' in app["Formulas"]
    assert 'Brand="Keep; me"' in app["Formulas"]
    assert app["Formulas"].count("AppEnvironment") == 1
    assert app["StartScreen"] == "=scrIntake"
    assert "MILSTRIP" + profile.title() + "Broker.Run" in app["OnStart"]
    intake = yaml.safe_load(files["Src/scrIntake.pa.yaml"])["Screens"]["scrIntake"]
    assert intake["Properties"] == {"Fill": "=NativeFill", "OnVisible": "=false"}
    users = yaml.safe_load(files["Src/scrUsers.pa.yaml"])["Screens"]["scrUsers"]
    expected_events = json.loads(render()[f"{profile}/screen-events.json"])
    assert users["Properties"]["OnVisible"] == "=" + expected_events["scrUsers"]["OnVisible"]
    editor = yaml.safe_load(files["Src/_EditorState.pa.yaml"])["EditorState"]
    assert editor["ScreensOrder"] == list(SCREENS) and editor["OtherNativeState"]


def test_all_four_old_business_screen_events_are_replaced_in_review_yaml(baseline):
    for screen in ("scrResults", "scrReview", "scrHistory"):
        document = {"Screens": {screen: {"Properties": {"OnVisible": "=MILSTRIPLocalDevAPI.GetHealth()"}, "Children": []}}}
        (baseline / "Src" / f"{screen}.pa.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")
    files, _ = assemble_entries(baseline, "stage")
    for screen in ("scrIntake", "scrResults", "scrReview", "scrHistory"):
        properties = yaml.safe_load(files[f"Src/{screen}.pa.yaml"])["Screens"][screen]["Properties"]
        assert properties["OnVisible"] == "=false"


def test_native_checkbox_metadata_version_must_match_xml(tmp_path):
    path = tmp_path / "native.msapr"
    template_archive(path, "2.1.0", "2.0.1")
    with pytest.raises(ValueError, match="mismatch"):
        native_checkbox_version(path)


def test_missing_native_control_version_is_rejected(baseline):
    path = baseline / "Src/scrIntake.pa.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["Screens"]["scrIntake"]["Children"] = [item for item in document["Screens"]["scrIntake"]["Children"]
                                                       if next(iter(item.values()))["Control"] != "Classic/DropDown@2.3.1"]
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ValueError, match="Missing or ambiguous native control version"):
        assemble_entries(baseline, "stage")


def test_extra_screen_with_behavior_is_not_silently_removed(baseline):
    path = baseline / "Src/Screen1.pa.yaml"
    path.write_text(yaml.safe_dump({"Screens": {"Screen1": {"Properties": {"OnVisible": "=Set(important,true)"}}}}), encoding="utf-8")
    with pytest.raises(ValueError, match="contains behavior"):
        assemble_entries(baseline, "stage")


def test_write_is_separate_and_never_overwrites_existing_output(baseline, tmp_path):
    for path in (baseline, baseline.parent, baseline / "child"):
        with pytest.raises(ValueError, match="separate"):
            write_assembly(baseline, path, "stage")
    output = tmp_path / "assembled"
    write_assembly(baseline, output, "stage")
    with pytest.raises(ValueError, match="never overwritten"):
        write_assembly(baseline, output, "stage")
