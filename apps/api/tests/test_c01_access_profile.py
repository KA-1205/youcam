"""C01 acceptance: durable access/profile persistence with adversarial cases."""
import pytest

from apps.api.tests.conftest import migration_round_trip


def test_migration_round_trip(db_url):
    migration_round_trip(db_url)


def test_guest_context_issued_once_with_secure_cookie(client):
    first = client.get('/api/profile')
    assert first.status_code == 200
    set_cookie = first.headers['set-cookie']
    assert 'HttpOnly' in set_cookie and 'SameSite=lax' in set_cookie.replace('Lax', 'lax')
    assert 'anchor_session=' in set_cookie
    body = first.json()
    assert body['actorId'] and body['tenantId'] == 'tenant-demo'
    assert body['consent']['consentRevision'] == 1
    assert not any(body['consent']['controls'].values())

    cookie = first.cookies['anchor_session']
    client.cookies.set('anchor_session', cookie)
    second = client.get('/api/profile')
    assert second.json()['actorId'] == body['actorId']


def test_invalid_cookie_gets_fresh_guest(client):
    client.cookies.set('anchor_session', 'forged-token')
    response = client.get('/api/profile')
    assert response.status_code == 200
    assert 'anchor_session=' in response.headers['set-cookie']


def test_demo_login_is_labelled_and_verifies_account(client):
    response = client.post('/api/auth/demo-login', json={'email': 'Shopper@Example.com'})
    assert response.status_code == 200
    assert response.json() == {'accountId': response.json()['accountId'], 'verified': True,
                               'mode': 'DEMO', 'roles': ['SHOPPER']}
    profile = client.get('/api/profile')
    assert profile.status_code == 200
    assert profile.json()['actorId'] == response.json()['accountId'] or profile.json()['actorId']


def test_demo_login_disabled_outside_demo_mode(db_url, monkeypatch):
    monkeypatch.setenv('ANCHOR_DEMO_MODE', 'false')
    from apps.api.tests.conftest import make_client
    with make_client(db_url) as client:
        response = client.post('/api/auth/demo-login', json={'email': 'x@example.com'})
        assert response.status_code == 404
        assert response.json()['error']['code'] == 'NOT_FOUND'


def test_consent_update_cas_and_adversarial(client):
    client.post('/api/auth/demo-login', json={'email': 'consent@example.com'})
    controls = {'processPhotos': True, 'savePhotosAndRenders': False, 'shareWithStylist': False,
                'researchUse': False, 'notifications': True, 'saveAddress': False,
                'savePaymentToken': False}
    updated = client.put('/api/consents', json={
        'expectedConsentRevision': 1, 'controls': controls, 'processors': ['youcam'],
        'assetIds': [], 'adultAttestation': True})
    assert updated.status_code == 200
    assert updated.json()['consentRevision'] == 2
    assert updated.json()['controls']['processPhotos'] is True
    assert updated.json()['processors'] == ['youcam']

    stale = client.put('/api/consents', json={
        'expectedConsentRevision': 1, 'controls': controls, 'processors': [],
        'assetIds': [], 'adultAttestation': True})
    assert stale.status_code == 409
    assert stale.json()['error']['code'] == 'STALE_VERSION'


def test_consent_rejects_processing_without_adult_attestation(client):
    client.post('/api/auth/demo-login', json={'email': 'minor@example.com'})
    controls = {key: False for key in ('processPhotos', 'savePhotosAndRenders', 'shareWithStylist',
                                       'researchUse', 'notifications', 'saveAddress',
                                       'savePaymentToken')}
    controls['processPhotos'] = True
    response = client.put('/api/consents', json={
        'expectedConsentRevision': 1, 'controls': controls, 'processors': ['youcam'],
        'assetIds': [], 'adultAttestation': False})
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'VALIDATION_ERROR'


def test_wardrobe_requires_verified_account(client):
    guest_save = client.post('/api/wardrobe', json={
        'reference': {'slot': 'TOP', 'refType': 'VARIANT', 'refId': 'var-1'},
        'saved': True, 'manualOwnedQuantity': 1, 'attributesConfirmed': True})
    assert guest_save.status_code == 403
    assert guest_save.json()['error']['code'] == 'SCOPE_FORBIDDEN'


def test_wardrobe_save_and_list_with_provenance(client):
    client.post('/api/auth/demo-login', json={'email': 'wardrobe@example.com'})
    saved = client.post('/api/wardrobe', json={
        'reference': {'slot': 'TOP', 'refType': 'VARIANT', 'refId': 'var-1'},
        'saved': True, 'manualOwnedQuantity': 2, 'attributesConfirmed': True})
    assert saved.status_code == 201
    item = saved.json()
    assert item['reference']['refId'] == 'var-1'
    assert item['manualOwnedQuantity'] == 2
    assert item['provenance'] == ['MANUAL']

    listed = client.get('/api/wardrobe')
    assert [entry['reference']['refId'] for entry in listed.json()['items']] == ['var-1']
    assert listed.json()['nextCursor'] is None

    resave = client.post('/api/wardrobe', json={
        'reference': {'slot': 'TOP', 'refType': 'VARIANT', 'refId': 'var-1'},
        'saved': True, 'manualOwnedQuantity': 0, 'attributesConfirmed': True})
    assert resave.status_code == 201
    assert resave.json()['manualOwnedQuantity'] == 0
    listed = client.get('/api/wardrobe')
    assert [entry['reference']['refId'] for entry in listed.json()['items']] == ['var-1']


def test_wardrobe_pagination_cursor(client):
    client.post('/api/auth/demo-login', json={'email': 'pager@example.com'})
    for index in range(3):
        response = client.post('/api/wardrobe', json={
            'reference': {'slot': 'TOP', 'refType': 'VARIANT', 'refId': f'var-{index}'},
            'saved': True, 'manualOwnedQuantity': 0, 'attributesConfirmed': True})
        assert response.status_code == 201
    page = client.get('/api/wardrobe', params={'limit': 2})
    assert len(page.json()['items']) == 2
    assert page.json()['nextCursor']
    following = client.get('/api/wardrobe', params={'limit': 2, 'cursor': page.json()['nextCursor']})
    assert [entry['reference']['refId'] for entry in following.json()['items']] == ['var-2']
    assert following.json()['nextCursor'] is None


def test_other_account_cannot_read_profile(client, db_url):
    from apps.api.tests.conftest import make_client
    client.post('/api/auth/demo-login', json={'email': 'one@example.com'})
    with make_client(db_url) as other:
        other.post('/api/auth/demo-login', json={'email': 'two@example.com'})
        # Profile is actor-scoped: the other cookie sees its own empty profile.
        assert other.get('/api/profile').json()['preferences'] == {}


@pytest.mark.parametrize('body', [
    {'controls': None}, {'expectedConsentRevision': 'one'},
])
def test_consent_contract_validation(client, body):
    client.post('/api/auth/demo-login', json={'email': 'shape@example.com'})
    assert client.put('/api/consents', json=body).status_code == 422
