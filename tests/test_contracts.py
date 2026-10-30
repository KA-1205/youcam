import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate
from pydantic import ValidationError

from contracts.runtime import models as m
from contracts.runtime.mock import app as mock
from contracts.runtime.transport import create_app

SOURCE = Path('reference/Anchor-Fit-Final-v3.3')
FIXTURE = Path('contracts/runtime/fixtures')
SID = '00000000-0000-4000-8000-000000000001'
JID = '00000000-0000-4000-8000-000000000002'
KEY = '00000000-0000-4000-8000-000000000003'


def load(path):
    return json.loads(path.read_text())


def validator(name):
    schema = load(SOURCE / name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def test_original_output_examples():
    v = validator('stylist-output.schema.json')
    fixtures = load(SOURCE / 'stylist-contract-fixtures.json')
    for sample in fixtures['schemaValid']:
        v.validate(sample)
    for sample in fixtures['schemaInvalid']:
        assert not v.is_valid(sample)


@pytest.mark.parametrize('mode,look,valid', [('PROPOSE', None, True), ('REVIEW', SID, True),
                                         ('PROPOSE', SID, False), ('REVIEW', None, False)])
def test_source_and_runtime_request_parity(mode, look, valid):
    body = {'sessionId': SID, 'expectedSessionVersion': 1, 'mode': mode, 'lookId': look}
    assert validator('stylist-request.schema.json').is_valid(body) == valid
    if valid:
        m.StylistRequest.model_validate(body)
    else:
        with pytest.raises(ValidationError):
            m.StylistRequest.model_validate(body)


@pytest.mark.parametrize('change', [{'tenantId': 'foreign'}, {'sessionId': 'not-uuid'},
                                    {'expectedSessionVersion': 0}, {'expectedSessionVersion': True},
                                    {'expectedSessionVersion': '1'}, {'lookId': SID}])
def test_reject_authority_injection_and_invalid_requests(change):
    body = dict(sessionId=SID, expectedSessionVersion=1, mode='PROPOSE', lookId=None)
    body.update(change)
    with TestClient(create_app()) as client:
        r = client.post('/api/stylist-jobs', json=body, headers={'Idempotency-Key': KEY})
    assert r.status_code == 422
    assert r.json()['error']['code'] == 'VALIDATION_ERROR'
    assert 'foreign' not in r.text  # no sensitive input echo


def test_idempotency_header_required_and_valid():
    body = dict(sessionId=SID, expectedSessionVersion=1, mode='PROPOSE', lookId=None)
    with TestClient(create_app()) as client:
        assert client.post('/api/stylist-jobs', json=body).status_code == 422
        assert client.post('/api/stylist-jobs', json=body, headers={'Idempotency-Key': 'bad'}).status_code == 422
        assert client.post('/api/stylist-jobs', json=body, headers={'Idempotency-Key': KEY}).status_code == 501


@pytest.mark.parametrize('status,error_code', [('CANCELLED', 'CANCELLED'),
                                             ('FAILED', 'INVALID_OUTPUT'),
                                             ('TIMED_OUT', 'STYLIST_UNAVAILABLE')])
def test_terminal_envelopes(status, error_code):
    job = load(FIXTURE / 'stylist_job.json')
    job.update(status=status, error={'code': error_code, 'message': 'Unavailable',
                                    'details': {'reason': 'TIMEOUT'} if status == 'TIMED_OUT' else {}})
    m.StylistJob.model_validate(job)
    job['result'] = {'kind': 'NEEDS_CLARIFICATION', 'question': 'Choose form', 'reason': 'SEARCH_LIMIT'}
    with pytest.raises(ValidationError):
        m.StylistJob.model_validate(job)


def test_fallback_search_limit_is_not_infeasibility():
    job = load(FIXTURE / 'stylist_job.json')
    job.update(status='SUCCEEDED', source='RULE_BASED', result={'kind': 'NEEDS_CLARIFICATION',
               'question': 'Narrow your selection', 'reason': 'SEARCH_LIMIT'})
    m.StylistJob.model_validate(job)
    job['result'] = {'kind': 'NO_ELIGIBLE_COMBINATION', 'proofCode': 'SEARCH_LIMIT',
                     'affectedSlots': [], 'evaluatedCatalogVersion': 'v1', 'constraintEvidence': ['limit']}
    with pytest.raises(ValidationError):
        m.StylistJob.model_validate(job)


def test_pending_job_cannot_claim_ai_success():
    job = load(FIXTURE / 'stylist_job.json')
    job['source'] = 'AI'
    with pytest.raises(ValidationError):
        m.StylistJob.model_validate(job)


def test_unknown_price_is_nullable_not_zero():
    look = {'lookId': SID, 'items': [{'slot': 'TOP', 'refType': 'OWNED', 'refId': 'owned-top'}],
            'reasons': [{'text': 'Confirmed owned top', 'evidenceIds': ['owned-top'], 'kind': 'CATALOG_FACT'}],
            'warnings': [], 'merchandiseTotalMinor': None, 'currency': 'INR',
            'budgetVerified': False, 'completeness': 'CATEGORY_SET'}
    assert m.Look.model_validate(look).merchandiseTotalMinor is None
    for value in (-1, 1.5, True):
        with pytest.raises(ValidationError):
            m.Look.model_validate({**look, 'merchandiseTotalMinor': value})


def test_seven_consent_controls_are_independent():
    controls = dict.fromkeys(m.ConsentControls.model_fields, False)
    assert len(controls) == 7
    controls['processPhotos'] = True
    consent = m.ConsentControls.model_validate(controls)
    assert consent.processPhotos and not consent.savePhotosAndRenders and not consent.savePaymentToken


def test_synthetic_transport_version_conflict_and_unknown_id():
    with TestClient(mock) as client:
        r = client.get(f'/api/sessions/{SID}')
        assert r.headers['X-Anchor-Fit-Mode'] == 'FIXTURE'
        m.SessionSnapshot.model_validate(r.json())
        assert client.get(f'/api/sessions/{KEY}').status_code == 404
        body = dict(sessionId=SID, expectedSessionVersion=2, mode='PROPOSE', lookId=None)
        assert client.post('/api/stylist-jobs', json=body, headers={'Idempotency-Key': KEY}).status_code == 409
        body['expectedSessionVersion'] = 1
        accepted = client.post('/api/stylist-jobs', json=body, headers={'Idempotency-Key': KEY})
        assert accepted.status_code == 202
        m.JobAccepted.model_validate(accepted.json())
        m.StylistJob.model_validate(client.get(accepted.json()['statusUrl']).json())
        cancelled = client.delete(f'/api/stylist-jobs/{JID}')
        assert cancelled.json()['status'] == 'CANCELLED'
        m.StylistJob.model_validate(cancelled.json())


def test_openapi_valid_and_all_operations_typed():
    schema = create_app().openapi()
    validate(schema)
    for path, item in schema['paths'].items():
        for method, operation in item.items():
            if path == '/healthz':
                continue
            assert operation['security'] == [{'sessionCookie': []}]
            assert operation['x-required-scope']
            assert operation['responses']['422']['content']['application/json']['schema']['$ref'].endswith('/ErrorEnvelope')
            assert operation['responses']['501']
            if method in ('post', 'put'):
                assert operation['requestBody']['content']['application/json']['schema']
                assert any(p['name'] == 'Idempotency-Key' and p['required'] for p in operation['parameters'])


def test_contracts_match_checked_in_export():
    assert load(Path('contracts/runtime/openapi.json')) == create_app().openapi()


def test_sources_have_complete_story_coverage():
    rows = load(Path('policy/traceability.json'))
    assert {x['id'] for x in rows} == {f'FR-{i:03}' for i in range(1, 98)} | {f'US-{i:03}' for i in range(1, 190)}
    assert all(x['tickets'] and x['status'] == 'PLANNED_NOT_IMPLEMENTED' for x in rows)


def test_module_dependency_graph_is_acyclic():
    graph = load(Path('policy/modules.json'))
    def visit(node, ancestors):
        assert node not in ancestors
        for dependency in graph[node]['depends']:
            visit(dependency, ancestors | {node})
    assert len(graph) == 10
    for node in graph:
        visit(node, set())


def test_checkout_does_not_accept_client_payment_success_or_card_data():
    confirm = dict(quoteId=SID, expectedQuoteVersion=1, expectedSessionVersion=1,
                   confirmedTotalMinor=100, confirmPurchase=True,
                   addressReference='demo-address', paymentReference='demo-method')
    m.CheckoutConfirm.model_validate(confirm)
    for field in ['status', 'cardNumber', 'tenantId', 'ownerId']:
        with pytest.raises(ValidationError):
            m.CheckoutConfirm.model_validate({**confirm, field: 'forged'})
    with pytest.raises(ValidationError):
        m.CheckoutConfirm.model_validate({**confirm, 'confirmPurchase': False})


def test_exported_schema_preserves_original_mode_condition():
    request_schema = create_app().openapi()['components']['schemas']['StylistRequest']
    v = Draft202012Validator(request_schema, format_checker=FormatChecker())
    assert not v.is_valid({'sessionId': SID, 'expectedSessionVersion': 1, 'mode': 'REVIEW', 'lookId': None})
    assert not v.is_valid({'sessionId': SID, 'expectedSessionVersion': 1, 'mode': 'PROPOSE', 'lookId': SID})


def test_api_security_headers_and_sanitized_unexpected_error():
    app = create_app()

    @app.get('/test-crash')
    def crash():
        raise RuntimeError('private details must never be returned')

    with TestClient(app, raise_server_exceptions=False) as client:
        health = client.get('/healthz')
        assert health.headers['X-Content-Type-Options'] == 'nosniff'
        response = client.get('/test-crash')
        assert response.status_code == 500
        assert response.json()['error']['code'] == 'INTERNAL_ERROR'
        assert 'private details' not in response.text
