"""Foundation app: health and shape validation only; no business adapters."""
import os

from contracts.runtime.transport import create_app

if os.getenv('LIVE_PROVIDERS_ENABLED', 'false').lower() != 'false':
    raise RuntimeError('Live providers cannot be enabled in the foundation')

app = create_app()
