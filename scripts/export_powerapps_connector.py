"""Deterministic, deliberately scoped OpenAPI 3.1 to Swagger 2 projection.

Only this API's schema subset is supported. Reject new unions rather than
silently changing their meaning. HTTPValidationError.loc is the sole mixed
union: connector diagnostics represent its integer indices as strings.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api.app import app

TARGET = ROOT / "powerapps/connectors/MILSTRIP-Local-Dev-API.swagger.json"


def schema(value, location=""):
    if isinstance(value, list):
        return [schema(item, location) for item in value]
    if not isinstance(value, dict):
        return value
    value = dict(value)
    if "anyOf" in value:
        variants = value.pop("anyOf")
        nonnull = [item for item in variants if item.get("type") != "null"]
        if len(nonnull) == 1:
            value.update(nonnull[0])
            value["x-nullable"] = True
        elif location == "ValidationError.properties.loc.items":
            value["type"] = "string"
        else:
            raise ValueError(f"Unsupported schema union at {location}")
    if "const" in value:
        value["enum"] = [value.pop("const")]
    if "$ref" in value:
        value["$ref"] = value["$ref"].replace("#/components/schemas/", "#/definitions/")
        if len(value) > 1:
            value["allOf"] = [{"$ref": value.pop("$ref")}]
    return {key: schema(item, f"{location}.{key}" if location else key)
            for key, item in value.items()
            if key not in {"title", "examples"} and not (key == "default" and item is None)}


def build():
    source = app.openapi()
    result = dict(swagger="2.0", info={**source["info"], "title": "MILSTRIP Local Dev API"},
                  host="127.0.0.1:8000", basePath="/api/v1", schemes=["http"],
                  consumes=["application/json"], produces=["application/json"],
                  security=[{"basic-auth": []}], securityDefinitions={"basic-auth": {"type": "basic"}},
                  paths={}, definitions={name: schema(item, name) for name, item in source["components"]["schemas"].items()})
    for path, methods in source["paths"].items():
        result["paths"][path.removeprefix("/api/v1")] = converted = {}
        for method, operation in methods.items():
            parameters = []
            for parameter in operation.get("parameters", []):
                parameters.append({**{k: v for k, v in parameter.items() if k != "schema"}, **schema(parameter["schema"])})
            if "requestBody" in operation:
                body = operation["requestBody"]
                parameters.append(dict(name="body", **{"in": "body"}, required=body.get("required", False), schema=schema(body["content"]["application/json"]["schema"])))
            responses = {}
            for code, response in operation["responses"].items():
                responses[code] = {"description": response["description"]}
                if "content" in response:
                    responses[code]["schema"] = schema(response["content"]["application/json"]["schema"])
            for code, description in {"401": "Missing or invalid API credentials", "403": "Loopback gateway peer required", "404": "Not found", "409": "Review conflict; reload before a new command", "503": "Runtime configuration or database unavailable"}.items():
                responses[code] = {"description": description, "schema": {"type": "object", "properties": {"detail": {"type": "string"}}}}
            converted[method] = dict(operationId=operation["operationId"], summary=operation.get("summary", operation["operationId"]), parameters=parameters, responses=responses)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = json.dumps(build(), indent=2, sort_keys=True) + "\n"
    if args.check:
        if TARGET.read_text(encoding="utf-8") != content:
            raise SystemExit("Connector artifact differs; run scripts/export_powerapps_connector.py")
        print("Connector artifact matches runtime projection")
    else:
        TARGET.write_text(content, encoding="utf-8", newline="\n")
        print("Exported existing MILSTRIP connector definition")


if __name__ == "__main__":
    main()
