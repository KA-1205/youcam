"""API -> durable worker -> provider transport -> private bytes regression."""
from datetime import timedelta

from sqlalchemy import select

from apps.api import clock
from apps.api.modules.try_on_jobs.live_models import CreditBudget, LiveStep
from apps.api.modules.try_on_jobs.orchestration_models import ChildTaskRow
from apps.api.tests.test_c07_preview_orchestration import enqueue_preview, setup_ready_client


class FakeGateway:
    submissions = 0
    polls = 0
    deletes = 0

    def close(self): pass
    def cost(self, capability): return 1
    def upload(self, data, mime, ring=False): return 'provider-file'
    def submit(self, capability, payload):
        type(self).submissions += 1
        assert payload['src_file_id'] == 'provider-file'
        return 'provider-task'
    def poll(self, capability, task_id):
        type(self).polls += 1
        if type(self).polls == 1:
            return {'task_status': 'running'}
        return {'task_status': 'success', 'results': {'url': 'https://media.s3.amazonaws.com/result'}}
    def download(self, url): return b'\xff\xd8\xffreal-provider-image'
    def delete(self, task_id): type(self).deletes += 1


def activate(monkeypatch):
    monkeypatch.setenv('LIVE_PROVIDERS_ENABLED', 'true')
    monkeypatch.setenv('YOUCAM_API_KEY', 'test-key')
    monkeypatch.setenv('YOUCAM_CREDIT_LIMIT', '2')
    monkeypatch.setenv('YOUCAM_LIVE_CAPABILITIES', 'HAIR_COLOR')
    monkeypatch.setattr('apps.api.modules.try_on_jobs.live_runner.gateway_factory', FakeGateway)
    FakeGateway.submissions = FakeGateway.polls = FakeGateway.deletes = 0


def test_worker_restart_polls_once_without_resubmission(client, db_url, monkeypatch):
    # Switch this service to live using the same public factory as startup.
    activate(monkeypatch)
    from fastapi.testclient import TestClient

    from apps.api.db import Database
    from apps.api.main import create_app
    from apps.worker.runtime import build_runtime
    with TestClient(create_app(db_url), base_url='https://testserver') as browser:
        session, asset = setup_ready_client(browser)
        job = enqueue_preview(browser, session, asset, capability='HAIR_COLOR', selections=[],
                              settings={'preset': 'Burgundy'}).json()
        database = Database(db_url)
        # Every iteration constructs a new service: no provider state can live in memory.
        for _ in range(3):
            with database.unit_of_work() as db:
                rows = db.scalars(select(LiveStep)).all()
                for row in rows:
                    row.next_poll_at = clock.now() - timedelta(seconds=1)
                from apps.api.modules.task_runtime.models import DurableTaskRow
                for task in db.scalars(select(DurableTaskRow)):
                    task.available_at = clock.now() - timedelta(seconds=1)
            build_runtime(Database(db_url)).cycle()
        fetched = browser.get('/api/preview-jobs/' + job['jobId']).json()
        assert fetched['status'] == 'SUCCEEDED', fetched
        assert fetched['executionMode'] == 'LIVE'
        result_id = fetched['children'][0]['resultAssetId']
        content = browser.get('/api/assets/' + result_id + '/content')
        assert content.content == b'\xff\xd8\xffreal-provider-image'
        assert content.headers['content-type'] == 'image/jpeg'
        assert FakeGateway.submissions == 1
        assert FakeGateway.deletes == 1
        with database.unit_of_work() as db:
            budget = db.get(CreditBudget, 'youcam')
            child = db.scalar(select(ChildTaskRow))
            assert budget is not None and budget.reserved_units == 1
            assert child is not None and child.provider_task_id == 'provider-task'
        browser.delete('/api/assets/' + result_id)
        assert browser.get('/api/assets/' + result_id + '/content').status_code == 410


def test_ambiguous_submit_is_parked_without_another_paid_call(db_url, monkeypatch):
    activate(monkeypatch)
    from fastapi.testclient import TestClient

    from apps.api.db import Database
    from apps.api.errors import ApiError
    from apps.api.main import create_app
    from apps.worker.runtime import build_runtime

    def ambiguous(self, capability, payload):
        type(self).submissions += 1
        raise ApiError(503, 'PROVIDER_OUTAGE', 'Timed out after submission.')
    monkeypatch.setattr(FakeGateway, 'submit', ambiguous)
    with TestClient(create_app(db_url), base_url='https://testserver') as browser:
        session, asset = setup_ready_client(browser)
        job = enqueue_preview(browser, session, asset, capability='HAIR_COLOR', selections=[],
                              settings={'preset': 'Burgundy'}).json()
        build_runtime(Database(db_url)).cycle()
        build_runtime(Database(db_url)).cycle()
        result = browser.get('/api/preview-jobs/' + job['jobId']).json()
        assert result['status'] == 'TIMED_OUT'
        assert result['children'][0]['unknownChargeReserved']
        assert FakeGateway.submissions == 1


def test_credit_budget_blocks_submission_before_upload(db_url, monkeypatch):
    activate(monkeypatch)
    from fastapi.testclient import TestClient

    from apps.api.db import Database
    from apps.api.main import create_app
    from apps.worker.runtime import build_runtime

    with TestClient(create_app(db_url), base_url='https://testserver') as browser:
        session, asset = setup_ready_client(browser)
        job = enqueue_preview(browser, session, asset, capability='HAIR_COLOR', selections=[],
                              settings={'preset': 'Burgundy'}).json()
        database = Database(db_url)
        with database.unit_of_work() as db:
            budget = db.get(CreditBudget, 'youcam')
            assert budget is not None
            budget.reserved_units = 2
        build_runtime(database).cycle()
        result = browser.get('/api/preview-jobs/' + job['jobId']).json()
        assert result['status'] == 'FAILED'
        assert result['error']['code'] == 'CREDIT_LIMIT'
        assert FakeGateway.submissions == 0
