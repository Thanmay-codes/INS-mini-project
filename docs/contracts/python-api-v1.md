# Python API and runtime contract v1

Status: shared A02/A03 APIs implemented and released in G1; B01/A04 app factories are merged. A05 integrates the launcher and awaits merge/G2 verification. Read [protocol-v1.md](protocol-v1.md) for validation/encoding/time behavior. Python 3.11+; use installed Flask/cryptography and the standard library. No extra dependency is required by this contract.

## Common types and errors

`kerberos_lab.common.models` exports aliases `TicketKind = Literal["tgt", "service"]`, `Role = Literal["kdc", "resource"]`, `Purpose = Literal["tgs", "resource"]`, `DefenseMode = Literal["authenticator_no_cache", "authenticator_cache"]`, and frozen dataclasses below. Mapping constructors validate exact fields and types; serializers use the frozen wire names.

```python
@dataclass(frozen=True)
class Ticket:
    version: int
    kind: TicketKind
    ticket_id: str
    client_id: str
    service_id: str
    issued_at: int
    not_before: int
    expires_at: int
    session_key: str  # canonical base64; decode only in crypto helper
    @classmethod
    def from_dict(cls, value: object) -> Ticket: ...
    def to_dict(self) -> dict[str, object]: ...

@dataclass(frozen=True)
class ClientSession:
    client_id: str
    service_id: str
    ticket_id: str
    session_key: str
    expires_at: int
    @classmethod
    def from_dict(cls, value: object) -> ClientSession: ...
    def to_dict(self) -> dict[str, object]: ...

def canonical_bytes(value: object) -> bytes: ...
def parse_json_object(raw: bytes, *, max_bytes: int = 65536) -> dict[str, object]: ...
def validate_ticket_time(ticket: Ticket, *, now: int, skew: int) -> None: ...
def validate_authenticator_time(timestamp: int, *, now: int, skew: int) -> None: ...
```

Dataclasses validate on direct construction too. `canonical_bytes` accepts JSON-compatible null/bool/string/int/list/dict values, rejecting floats, excessive integers and non-string object keys; wire validators apply their more restrictive schemas. `parse_json_object` rejects duplicates/non-object roots and applies the specified limit. Validate authenticator/envelope structures inside the shared crypto helpers instead of duplicating parsers across apps.

`common.errors` exports `LabError(Exception)` with `code: str`, `http_status: int`, `reason: str`; constructor `LabError(reason: str = "")`. Subclasses and fixed mappings: `MalformedRequest` (400/malformed_request), `InvalidCredentials` (401/invalid_credentials), `InvalidAuthentication` (401/invalid_authentication), `WrongService` (403/wrong_service), `ReplayDetected` (409/replay_detected), `ReplayStateUnavailable` (503/replay_state_unavailable). `reason` is controlled diagnostic text/code, never a response body or secret. `to_error_response(error: LabError) -> tuple[dict[str, object], int]` returns the exact public error envelope/status. Normalize expected library parsing/crypto/store failures; programmer errors must not become successful authentication.

## Clock and settings

`common.clock`:

```python
class Clock(Protocol):
    def now(self) -> int: ...
class SystemClock:  # floor(time.time()), valid nonnegative integer seconds
    def now(self) -> int: ...
class FrozenClock:
    def __init__(self, timestamp: int) -> None: ...
    def now(self) -> int: ...
    def set(self, timestamp: int) -> None: ...
    def advance(self, seconds: int) -> None: ...  # negative allowed if result valid
class OffsetClock:
    def __init__(self, base: Clock, offset_seconds: int) -> None: ...
    def now(self) -> int: ...
```

Reject boolean/invalid time inputs; offsets may be negative, resulting times may not. No sleeps or host-time changes. Measure latency separately with `time.perf_counter_ns()`.

`common.settings.Settings` is a frozen dataclass with `run_dir: Path`, `role: Role`, `host: str`, `port: int`, `clock_offset_seconds: int`, `frozen_time_seconds: int | None`, `defense_mode: DefenseMode`, `ticket_lifetime_seconds: int`, `allowed_clock_skew_seconds: int`, `replay_capacity: int`, `sqlite_busy_timeout_ms: int`. Host is strictly loopback `127.0.0.1`; defaults are 5000 for KDC and 5001 for resource, offset 0, live clock, defended mode, and protocol defaults. Lifetime/capacity/timeout must be positive; skew nonnegative; ports 1–65535. Initial single-service/user IDs are fixed by v1, not configurable extra audiences.

```python
def load_settings(config_path: Path | None, *, run_dir: Path, role: Role,
                  port: int | None = None, clock_offset_seconds: int = 0,
                  frozen_time_seconds: int | None = None,
                  defense_mode: DefenseMode | None = None) -> Settings: ...
def make_clock(settings: Settings) -> Clock: ...
```

TOML accepts the existing `protocol`, `resource`, `experiments` tables. Protocol keys: schema_version (=1), ticket_lifetime_seconds, allowed_clock_skew_seconds, optional replay_capacity/sqlite_busy_timeout_ms. Resource keys: defense_mode, retain_replay_records_for_full_run (=true). Experiments keys: performance_trials, concurrency_workers, resource_clock_offsets_seconds with validated positive counts/ports-independent worker counts and integer offsets. Defaults fill omitted settings; reject unknown tables/keys. Experiment options are validated by settings loading but consumed by B's runner, which may read the validated config independently. CLI overrides take precedence; KDC ignores the *effect* of resource defense mode and always checks replay. Invalid files/settings raise MalformedRequest with a configuration reason; app startup renders a non-secret stderr message and exits nonzero.

## Crypto helpers

`common.crypto` signatures:

```python
def encode_b64(value: bytes) -> str: ...
def decode_b64(value: str, *, expected_length: int | None = None) -> bytes: ...
def new_key() -> bytes: ...  # 32 cryptographically random bytes
def new_identifier() -> str: ...  # 16 random bytes as lowercase hex
def seal_ticket(ticket: Ticket, key: bytes) -> dict[str, object]: ...
def open_ticket(envelope: object, key: bytes, *, expected_kind: TicketKind) -> Ticket: ...
def sign_authenticator(session: ClientSession, envelope: dict[str, object],
                       body: dict[str, object], *, purpose: Purpose,
                       timestamp: int, request_nonce: str | None = None
                       ) -> dict[str, object]: ...
def verify_authenticator(authenticator: object, ticket: Ticket,
                         envelope: dict[str, object], body: dict[str, object], *,
                         purpose: Purpose, now: int, skew: int
                         ) -> dict[str, object]: ...
def make_password_verifier(password: str) -> dict[str, object]: ...
def verify_password(password: str, verifier: object) -> bool: ...
def derive_service_key(password: str, *, salt: bytes,
                       iterations: int = 100000) -> bytes: ...
```

The purpose determines method/path/service binding. Signing verifies the session/envelope/body shapes and permitted purpose; verification authenticates identity/context/digests/MAC and checks ticket/authenticator time using the caller's one captured `now`. Return the validated full authenticator mapping, including the consumed request nonce. The caller separately authorizes a supported TGS body service ID or resource operation. TGS body accepts a syntactically valid service ID so unsupported authenticated targets can receive 403; resource body requires exactly operation=increment. MAC failure and identity/context/role/time failures raise InvalidAuthentication, structural errors MalformedRequest. Decryption authentication failure is InvalidAuthentication; malformed envelope fields are MalformedRequest. A session key is decoded to bytes only after validation.

Password verifier exact fields: version=1, algorithm="scrypt", n=16384, r=8, p=1, salt=16 random bytes/base64, digest=32 bytes/base64. Enforce these parameters before performing untrusted KDF work. Incorrect valid password returns false; corrupt verifier raises MalformedRequest so a KDC startup can fail clearly. Use library Scrypt and verification API. Optional service derivation uses PBKDF2-HMAC-SHA256, salt exactly 16 bytes, 100,000 iterations by default; accept explicit integers in [1, 1,000,000] for controlled experiments. Record parameters; default parameter changes require a contract revision. These parameters are lab choices, not AD encryption profiles or password-hardening recommendations.

## Persistent replay API (A03)

`common.replay_cache`:

```python
def initialize_store(path: Path, *, run_id: str, namespace: Purpose) -> None: ...
class ReplayStore:
    @classmethod
    def open_existing(cls, path: Path, *, expected_run_id: str,
                      namespace: Purpose, capacity: int = 10000,
                      busy_timeout_ms: int = 5000) -> ReplayStore: ...
    def consume(self, *, service_id: str, ticket_id: str,
                request_nonce: str, accepted_at: int) -> None: ...
    def consume_and_increment(self, *, service_id: str, ticket_id: str,
                              request_nonce: str, accepted_at: int) -> int: ...
    def increment_without_replay_tracking(self, *, service_id: str) -> int: ...
    def counter(self, *, service_id: str) -> int: ...
```

No public connection object or persistent connection per instance: each operation opens `mode=rw`, validates metadata and closes its connection. Schema version 1 contains `metadata` (one run_id/schema_version/namespace record), `consumed` (namespace, service_id, ticket_id, request_nonce, accepted_at; composite primary key on first four), and `counters` (service_id primary key, nonnegative integer value). Initialization exclusively creates a new file and never replaces an existing store. Run IDs follow 32-hex identifier rules. Open checks metadata/schema plus SQLite quick_check. Every later operation checks metadata; missing/deleted/replaced/corrupt state is unavailable, never implicitly initialized.

Write operations use `BEGIN IMMEDIATE`, busy timeout and `synchronous=FULL` with rollback-journal mode DELETE for this single-host lab. Consumption checks existing identity before capacity, then inserts, optionally increments the counter, and commits. Capacity counts all retained consumed records in that store. No-cache counter increments do not add consumed records. Unique constraint conflict is ReplayDetected only for the matching identity; all storage/timeout/schema errors are ReplayStateUnavailable. The no-cache mode still needs the initialized operation-counter store. TGS consumes before issuing a response; lost response/retry uses a fresh request nonce rather than pretending result recovery exists.

## Private material and initialization

`common.material` exports frozen `LabMaterial` with `run_id: str`, `client_id: str`, `service_id: str`, `service_key: bytes`, `tgs_key: bytes | None`, `password_verifier: dict[str, object] | None`, `kdc_store_path: Path | None`, `resource_store_path: Path`.

```python
def initialize_run(run_dir: Path, *, password: str, run_id: str | None = None) -> None: ...
def load_material(run_dir: Path, *, role: Role) -> LabMaterial: ...
```

Run directory must be new/nonexistent; create with restricted permissions where supported and never overwrite existing contents. Layout: `manifest.json` with version=1, run_id, client_id="alice", service_id="files"; `tgs.key` and `service.key` binary 32-byte files; `user.json` with version=1, username="alice", verifier; `kdc.sqlite` namespace=tgs; `resource.sqlite` namespace=resource. Manifest has no secrets or user-supplied file paths. Only load fixed filenames, validate lengths/metadata and require initialized stores. Resource loader returns tgs_key/password_verifier/kdc_store_path as None and does not open those files. The same local host is trusted; this data structure is not OS-level isolation from all shared files. Callers must use ignored `data/private/<new-run>/` for normal experiments. Setup fixture verification may use temporary directories.

`scripts/init_demo.py` CLI: `--run-dir PATH` required; obtain password with getpass, or `--password-stdin` reads one UTF-8 line (remove only line terminator). No password argv/default credential/secret stdout. Print run ID and file locations only. Reset means deliberately choose a new run directory; v1 supplies no destructive reset flag.

## App factories and local process controls

`kdc.app.create_app(settings: Settings, *, clock: Clock | None = None) -> Flask` and `resource_server.app.create_app(...)` require settings and load validated material/state at startup. Injected Clock overrides make_clock(settings) in tests. Factories were implemented in B01/A04; A01 originally specified their interface. No supplied settings means Python TypeError; invalid material/state fails startup before serving.

Each app main supports required `--run-dir PATH`, optional `--config PATH`, `--port INT`, `--clock-offset-seconds INT`, `--frozen-time-seconds INT`; resource additionally `--defense-mode MODE`. KDC rejects that last option. Loopback host fixed, debug/reloader off. Factory clock injection supplies test changes; live process changes require an explicit new process setting/restart. A05 launcher (release tracked in the gate ledger): `--run-dir`, optional `--config`, `--kdc-port`/`--resource-port`, role-specific offset and frozen-time flags, resource defense mode; starts child modules and stops both on interruption/error. The launcher forwards options using argv arrays, never shell interpolation. B03 may start resource modules on distinct ports sharing the same run directory/store and service key; no HTTP time-control endpoints.

B owns client APIs/CLI, but its health invocation remains `python -m kerberos_lab.client` in the initial scaffold; B02 must preserve/document an equivalent health command before replacing that default. Client transport/capture APIs are documented by B02 using these wire objects and the shared signing helper.
