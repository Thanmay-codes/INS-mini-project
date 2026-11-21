"""Non-secret local configuration, with explicit runtime overrides."""

from dataclasses import dataclass, replace
from pathlib import Path
import tomllib

from .clock import Clock, FrozenClock, OffsetClock, SystemClock
from ._validation import MAX_INTEGER, integer
from .errors import MalformedRequest
from .models import DefenseMode, Role


@dataclass(frozen=True)
class Settings:
    run_dir: Path
    role: Role
    port: int
    host: str = "127.0.0.1"
    clock_offset_seconds: int = 0
    frozen_time_seconds: int | None = None
    defense_mode: DefenseMode = "authenticator_cache"
    ticket_lifetime_seconds: int = 300
    allowed_clock_skew_seconds: int = 30
    replay_capacity: int = 10000
    sqlite_busy_timeout_ms: int = 5000

    def __post_init__(self) -> None:
        if (not isinstance(self.run_dir, Path) or self.role not in ("kdc", "resource")
                or self.host != "127.0.0.1" or self.defense_mode not in (
                    "authenticator_cache", "authenticator_no_cache")):
            raise MalformedRequest("invalid_configuration")
        integer(self.port, minimum=1, maximum=65535)
        integer(self.clock_offset_seconds, minimum=-MAX_INTEGER)
        if self.frozen_time_seconds is not None:
            integer(self.frozen_time_seconds)
        integer(self.allowed_clock_skew_seconds)
        for value in (self.ticket_lifetime_seconds, self.replay_capacity, self.sqlite_busy_timeout_ms):
            integer(value, minimum=1)


def load_settings(config_path: Path | None, *, run_dir: Path, role: Role,
                  port: int | None = None, clock_offset_seconds: int = 0,
                  frozen_time_seconds: int | None = None,
                  defense_mode: DefenseMode | None = None) -> Settings:
    if config_path is None:
        config = {}
    else:
        if not isinstance(config_path, Path):
            raise MalformedRequest("invalid_configuration_path")
        try:
            with config_path.open("rb") as handle:
                config = tomllib.load(handle)
        except (OSError, ValueError, UnicodeError):
            raise MalformedRequest("invalid_configuration_file") from None
    allowed = {
        "protocol": {"schema_version", "ticket_lifetime_seconds", "allowed_clock_skew_seconds",
                     "replay_capacity", "sqlite_busy_timeout_ms"},
        "resource": {"defense_mode", "retain_replay_records_for_full_run"},
        "experiments": {"performance_trials", "concurrency_workers", "resource_clock_offsets_seconds"},
    }
    if set(config) - set(allowed):
        raise MalformedRequest("unknown_configuration_table")
    for name, values in config.items():
        if not isinstance(values, dict) or set(values) - allowed[name]:
            raise MalformedRequest("invalid_configuration_fields")
    protocol = config.get("protocol", {})
    resource = config.get("resource", {})
    if integer(protocol.get("schema_version", 1)) != 1:
        raise MalformedRequest("invalid_configuration_version")
    if resource.get("retain_replay_records_for_full_run", True) is not True:
        raise MalformedRequest("invalid_retention_policy")
    experiments = config.get("experiments", {})
    if "performance_trials" in experiments:
        integer(experiments["performance_trials"], minimum=1)
    for name, minimum in (("concurrency_workers", 1), ("resource_clock_offsets_seconds", -MAX_INTEGER)):
        if name in experiments:
            values = experiments[name]
            if not isinstance(values, list) or not values:
                raise MalformedRequest("invalid_experiment_list")
            for value in values:
                integer(value, minimum=minimum)
    loaded = Settings(
        run_dir=run_dir, role=role, port=5000 if role == "kdc" else 5001,
        defense_mode=resource.get("defense_mode", "authenticator_cache"),
        ticket_lifetime_seconds=protocol.get("ticket_lifetime_seconds", 300),
        allowed_clock_skew_seconds=protocol.get("allowed_clock_skew_seconds", 30),
        replay_capacity=protocol.get("replay_capacity", 10000),
        sqlite_busy_timeout_ms=protocol.get("sqlite_busy_timeout_ms", 5000),
    )
    return replace(loaded, port=loaded.port if port is None else port,
                   clock_offset_seconds=clock_offset_seconds, frozen_time_seconds=frozen_time_seconds,
                   defense_mode=loaded.defense_mode if defense_mode is None else defense_mode)


def make_clock(settings: Settings) -> Clock:
    base = SystemClock() if settings.frozen_time_seconds is None else FrozenClock(settings.frozen_time_seconds)
    return OffsetClock(base, settings.clock_offset_seconds)
