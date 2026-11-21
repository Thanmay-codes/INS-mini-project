"""Run the local KDC and resource server; stop both on interruption or failure."""

import argparse
from pathlib import Path
import signal
import subprocess
import sys
import time

from kerberos_lab.common.errors import LabError, MalformedRequest
from kerberos_lab.common.settings import load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True, type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--kdc-port', type=int)
    parser.add_argument('--resource-port', type=int)
    for role in ('kdc', 'resource'):
        parser.add_argument(f'--{role}-clock-offset-seconds', type=int, default=0)
        parser.add_argument(f'--{role}-frozen-time-seconds', type=int)
    parser.add_argument('--defense-mode', choices=('authenticator_cache', 'authenticator_no_cache'))
    args = parser.parse_args()
    try:
        settings = [load_settings(
            args.config, run_dir=args.run_dir, role=role,
            port=getattr(args, f'{role}_port'),
            clock_offset_seconds=getattr(args, f'{role}_clock_offset_seconds'),
            frozen_time_seconds=getattr(args, f'{role}_frozen_time_seconds'),
            defense_mode=args.defense_mode if role == 'resource' else None,
        ) for role in ('kdc', 'resource')]
        if settings[0].port == settings[1].port:
            raise MalformedRequest('server_ports_must_differ')
    except LabError as error:
        print(f'Lab configuration failed: {error.reason or error.code}', file=sys.stderr)
        return 2

    processes: list[subprocess.Popen] = []

    def interrupt(_signum, _frame):
        raise KeyboardInterrupt

    signals = [signal.SIGTERM]
    if hasattr(signal, 'SIGBREAK'):
        signals.append(signal.SIGBREAK)
    previous = {number: signal.signal(number, interrupt) for number in signals}
    try:
        for module, config in zip(('kerberos_lab.kdc.app', 'kerberos_lab.resource_server.app'), settings):
            command = [sys.executable, '-m', module, '--run-dir', str(config.run_dir),
                       '--port', str(config.port), '--clock-offset-seconds', str(config.clock_offset_seconds)]
            if args.config is not None:
                command.extend(['--config', str(args.config)])
            if config.frozen_time_seconds is not None:
                command.extend(['--frozen-time-seconds', str(config.frozen_time_seconds)])
            if config.role == 'resource':
                command.extend(['--defense-mode', config.defense_mode])
            processes.append(subprocess.Popen(command))
        print(f'Starting lab on 127.0.0.1 ports {settings[0].port} and {settings[1].port}. Ctrl+C stops both.', flush=True)
        while True:
            for process in processes:
                if process.poll() is not None:
                    print('A server exited; stopping the lab.', file=sys.stderr)
                    return process.returncode if process.returncode > 0 else 1
            time.sleep(0.1)
    except KeyboardInterrupt:
        return 0
    except OSError:
        print('Could not start a lab server.', file=sys.stderr)
        return 2
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for number, handler in previous.items():
            signal.signal(number, handler)


if __name__ == '__main__':
    raise SystemExit(main())
