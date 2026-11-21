# Private local run setup (A03)

From the repository root with the editable project installed:

```bash
python -m pip install -e '.[dev]'
python scripts/init_demo.py --run-dir data/private/demo-001
```

The CLI prompts for a synthetic password without echoing it. For automated use,
`--password-stdin` accepts one UTF-8 line from a secure input source. Do not put
passwords in shell arguments, committed scripts or recorded terminal commands.
Spaces are preserved; only the final line terminator is removed. No default
password exists. Use the same password when the future client requests a TGT.

Setup exclusively creates a new run directory (0700) with files (0600), subject
to platform support. It generates independent 32-byte TGS/service keys, a salted
Scrypt verifier for `alice`, separate TGS/resource SQLite databases, and a public
manifest identifying the run and `files` service. These runtime files belong in
ignored `data/private/`; never copy them into public fixtures. Console output
contains only the run ID and directory. The supplied contract fixtures remain
public disposable test material, separate from generated runtime secrets.

An existing directory is refused. To reset an experiment, stop its processes and
choose a new directory, e.g. `data/private/demo-002`. There is no destructive reset
flag. A failed initialization may leave an incomplete private directory; preserve
it for diagnosis and use a new name. The manifest is written last. Never repair
missing replay state by creating an empty database while continuing the same run.

## Store behavior and integration

Use the public APIs in `python-api-v1.md`. A store is bound to the run ID and
namespace. Every operation opens its own SQLite connection in existing-file mode;
writes acquire `BEGIN IMMEDIATE`, wait up to the configured timeout, and commit
with `synchronous=FULL` using the DELETE rollback journal. Schemas, metadata and
SQLite quick checks are verified. Records remain for the entire run; capacity
exhaustion rejects new identities. Duplicate classification precedes capacity.

`consume` reserves an authenticated TGS request. `consume_and_increment` reserves
a resource request and increments its counter in one transaction. A failed
transaction changes neither. `increment_without_replay_tracking` uses the same
counter transaction while bypassing duplicate tracking; it still requires healthy
initialized state. Counters count committed demo operations, not HTTP attempts or
responses. An accepted operation whose response is lost is not recovered by this
API; a retry of the same identity is rejected.

The KDC material loader validates its TGS store, keys and password verifier. The
resource loader validates its own store and service key without opening KDC-only
files. Loaders do not create state. Applications must also call the store for each
operation; successful startup validation alone is insufficient.

## Evidence limits

Tests use real temporary SQLite files, lock contention and spawned processes;
they cover ordinary process exit/reopen, not power interruption or storage-device
durability. This is a trusted single-host lab. File identity checks detect a live
handle's database being removed/replaced. There is no external trusted history to
detect a valid same-run snapshot substituted before a fresh process opens it, or
an attacker rewriting valid data in place. Do not claim rollback resistance against
a malicious local filesystem administrator. This setup supplies no HTTP endpoints,
Active Directory integration or complete Kerberos implementation.
