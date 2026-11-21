#!/usr/bin/env python3
"""Create a new disposable run; never pass passwords as command-line arguments."""
import argparse
from getpass import getpass
from pathlib import Path
import sys

from kerberos_lab.common.errors import LabError, MalformedRequest
from kerberos_lab.common.material import initialize_run, load_material


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True, type=Path)
    parser.add_argument('--password-stdin', action='store_true', help='Read one UTF-8 password line from stdin instead of prompting')
    args = parser.parse_args()
    try:
        if args.password_stdin:
            raw = sys.stdin.buffer.read(1027)
            if raw.endswith(b'\r\n'):
                raw = raw[:-2]
            elif raw.endswith(b'\n'):
                raw = raw[:-1]
            if b'\n' in raw or b'\r' in raw:
                raise MalformedRequest('one_password_line_required')
            password = raw.decode('utf-8')
        else:
            password = getpass('Synthetic lab password: ')
        initialize_run(args.run_dir, password=password)
        material = load_material(args.run_dir, role='resource')
        print(f'Initialized run {material.run_id} at {args.run_dir.resolve()}')
        return 0
    except (LabError, OSError, UnicodeError, EOFError):
        print('Initialization failed. Use a new directory and a nonempty UTF-8 password of at most 1024 bytes.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
