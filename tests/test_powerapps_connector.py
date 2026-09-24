import json
from pathlib import Path

from openapi_spec_validator import validate

from api.app import app
from scripts.export_powerapps_connector import build, schema


def test_connector_is_valid_swagger_and_matches_runtime():
    generated = build()
    validate(generated)
    saved = json.loads(Path('powerapps/connectors/MILSTRIP-Local-Dev-API.swagger.json').read_text())
    assert generated == saved
    assert generated['host'] == '127.0.0.1:8000'
    assert generated['basePath'] == '/api/v1'
    assert generated['schemes'] == ['http']
    operations = [(path, method, op) for path, methods in generated['paths'].items() for method, op in methods.items()]
    expected = {'GetHealth', 'ListIntakeRequests', 'CreateIntakeRequest', 'GetIntakeRequest',
                'ListRecordResults', 'ListAuditEvents', 'CreateReviewDecision', 'InvokeBroker'}
    assert len(operations) == len(expected)
    assert {op['operationId'] for _, _, op in operations} == expected
    for path, method, op in operations:
        source = app.openapi()['paths']['/api/v1' + path][method]
        assert source['operationId'] == op['operationId']
        assert source['security'] == generated['security']
        for code, response in source['responses'].items():
            if 'content' in response:
                assert op['responses'][code]['schema'] == schema(response['content']['application/json']['schema'])


def test_projection_rejects_unrecognized_union():
    import pytest
    with pytest.raises(ValueError, match='Unsupported schema union'):
        schema({'anyOf': [{'type': 'string'}, {'type': 'integer'}]}, 'NewField')
