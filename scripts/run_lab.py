"""Run both local Flask starters; stop both when interrupted or one exits."""

import subprocess
import sys
import time


def main() -> int:
    processes: list[subprocess.Popen] = []
    try:
        for module in ("kerberos_lab.kdc.app", "kerberos_lab.resource_server.app"):
            processes.append(subprocess.Popen([sys.executable, "-m", module]))
        print("Starting lab on 127.0.0.1 ports 5000 and 5001. Ctrl+C stops both.", flush=True)
        while True:
            for process in processes:
                if process.poll() is not None:
                    print("A server exited; stopping the lab.", file=sys.stderr)
                    return process.returncode or 1
            time.sleep(0.2)
    except KeyboardInterrupt:
        return 0
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


if __name__ == "__main__":
    raise SystemExit(main())
