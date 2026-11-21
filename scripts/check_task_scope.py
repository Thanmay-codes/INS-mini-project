"""Report task edits outside a role's documented ownership; never mutate Git."""

import argparse
import fnmatch
import json
from pathlib import Path
import re
import subprocess
import sys


def matches_rule(path: str, rule: str) -> bool:
    if rule.endswith("/"):
        return path.startswith(rule)
    return fnmatch.fnmatchcase(path, rule)


def git(repo: Path, *arguments: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments], capture_output=True, check=False
    )
    if result.returncode:
        detail = result.stderr.decode(errors="replace").strip()
        raise ValueError(detail or "Git inspection failed")
    return result.stdout


def changed_paths(repo: Path, base: str) -> list[str]:
    git(repo, "rev-parse", "--verify", f"{base}^{{commit}}")
    tracked = git(repo, "diff", "--name-only", "-z", "--no-renames", base, "--")
    untracked = git(repo, "ls-files", "--others", "--exclude-standard", "-z")
    return sorted(
        {item.decode(errors="surrogateescape") for item in (tracked + untracked).split(b"\0") if item}
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", required=True, choices=("A", "B", "C", "D"))
    parser.add_argument("--base", required=True, help="Full fixed SHA at task start")
    args = parser.parse_args()
    if re.fullmatch(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", args.base) is None:
        parser.error("--base must be a full fixed commit SHA, not HEAD or a moving branch")
    repo = Path(__file__).resolve().parents[1]
    try:
        manifest = json.loads((repo / "docs/workflow/tasks.json").read_text())
        rules = manifest["roles"][args.role]["allowed"]
        paths = changed_paths(repo, args.base)
    except (OSError, ValueError, KeyError) as error:
        print(f"Scope check could not run: {error}", file=sys.stderr)
        return 2
    violations = [p for p in paths if not any(matches_rule(p, r) for r in rules)]
    if violations:
        print(f"OUT OF SCOPE for role {args.role}:")
        for path in violations:
            print(f"  {path}")
        print("Request a change from the owner; preserve unrelated existing work.")
        return 1
    print(f"Scope OK: {len(paths)} changed path(s) fit role {args.role}'s allowlist.")
    print("This checks file ownership only; run the task's functional checks separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
