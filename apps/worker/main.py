"""Anchor Fit worker: leased dispatch, outbox publishing and reconciliation.

--check verifies boot without touching a database (used by CI and containers).
--once runs a single cycle; --loop runs cycles on an interval.
"""
import argparse
import json
import os
import time

from apps.api.db import Database


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--loop', action='store_true')
    parser.add_argument('--interval', type=float, default=2.0)
    args = parser.parse_args()
    if args.check:
        dispatch_enabled = bool(os.getenv('DATABASE_URL'))
        print(json.dumps({'status': 'READY', 'dispatchEnabled': dispatch_enabled}))
        return
    if args.loop == args.once:
        parser.error('choose exactly one of --once or --loop')

    from apps.worker.runtime import build_runtime

    runtime = build_runtime(Database())
    if args.once:
        print(json.dumps(runtime.cycle()))
        return
    while True:
        print(json.dumps(runtime.cycle()), flush=True)
        time.sleep(args.interval)


if __name__ == '__main__':
    main()
