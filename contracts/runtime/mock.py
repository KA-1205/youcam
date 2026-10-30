"""Local synthetic transport for parallel work. No persistence, auth or paid calls.

Known fixture IDs only. Run on localhost:8001; never deploy as the production API.
"""
import json
from pathlib import Path
from uuid import UUID

from fastapi import Header, Request
from fastapi.responses import JSONResponse

from .models import JobAccepted, SessionSnapshot, StylistJob, StylistRequest
from .transport import create_app, error

FIXTURES = Path(__file__).with_name('fixtures')
app = create_app()
app.title = 'Anchor Fit local fixture transport'
# Replace only explicitly supported fixtures. Remaining operations retain 501.
_mocked = {'getSession', 'createStylistJob', 'getStylistJob', 'cancelStylistJob'}
app.router.routes = [r for r in app.router.routes if getattr(r, 'operation_id', None) not in _mocked]


def read_fixture(name: str) -> dict:
    return json.loads((FIXTURES / f'{name}.json').read_text())


@app.middleware('http')
async def label_fixture(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Anchor-Fit-Mode'] = 'FIXTURE'
    return response


@app.get('/api/sessions/{sessionId}', response_model=SessionSnapshot)
def get_session(sessionId: UUID):
    value = read_fixture('session')
    if str(sessionId) != value['sessionId']:
        return error(404, 'NOT_FOUND', 'Unknown fixture session.')
    return value


@app.post('/api/stylist-jobs', response_model=JobAccepted, status_code=202)
def create_job(body: StylistRequest, idempotency_key: UUID = Header(alias='Idempotency-Key')):
    session = read_fixture('session')
    if str(body.sessionId) != session['sessionId']:
        return error(404, 'NOT_FOUND', 'Unknown fixture session.')
    if body.expectedSessionVersion != session['sessionVersion']:
        return error(409, 'STALE_SESSION', 'Refresh this session.')
    # Static contract scenario, not a production idempotency implementation.
    return read_fixture('accepted')


@app.get('/api/stylist-jobs/{jobId}', response_model=StylistJob)
def get_job(jobId: UUID):
    value = read_fixture('stylist_job')
    if str(jobId) != value['jobId']:
        return error(404, 'NOT_FOUND', 'Unknown fixture job.')
    return value


@app.delete('/api/stylist-jobs/{jobId}', response_model=StylistJob)
def cancel_job(jobId: UUID):
    value = read_fixture('stylist_job')
    if str(jobId) != value['jobId']:
        return error(404, 'NOT_FOUND', 'Unknown fixture job.')
    value.update(status='CANCELLED', result=None, source=None,
                 error={'code': 'CANCELLED', 'message': 'Fixture cancellation.', 'details': {}})
    return JSONResponse(value)
