"""Released configuration precedence, validation and injected time."""

from pathlib import Path

import pytest


def test_example_configuration_loads_and_explicit_options_take_precedence(tmp_path):
    from kerberos_lab.common.settings import load_settings, make_clock

    example = Path(__file__).parents[2] / "configs/replay.example.toml"
    default = load_settings(example, run_dir=tmp_path, role="kdc")
    assert (default.host, default.port, default.ticket_lifetime_seconds,
            default.allowed_clock_skew_seconds, default.replay_capacity) == (
                "127.0.0.1", 5000, 300, 30, 10000)
    settings = load_settings(example, run_dir=tmp_path, role="resource", port=5012,
                             defense_mode="authenticator_no_cache", frozen_time_seconds=1000,
                             clock_offset_seconds=-15)
    assert (settings.port, settings.defense_mode) == (5012, "authenticator_no_cache")
    assert make_clock(settings).now() == 985


@pytest.mark.parametrize("contents", [
    "[unknown]\nx=1", "[protocol]\nextra=1", "[protocol]\nschema_version=true",
    "[protocol]\nticket_lifetime_seconds=0", "[protocol]\nallowed_clock_skew_seconds=-1",
    "[resource]\nretain_replay_records_for_full_run=false", "[resource]\ndefense_mode='unknown'",
    "[experiments]\nperformance_trials=true", "[experiments]\nconcurrency_workers=[2,0]",
    "[experiments]\nresource_clock_offsets_seconds=[1.5]", "[experiments]\nextra=1",
    "protocol=1", "[broken", "[protocol]\nreplay_capacity=true",
    "[protocol]\nsqlite_busy_timeout_ms=0",
])
def test_invalid_configuration_fails_before_runtime(tmp_path, contents):
    from kerberos_lab.common.errors import MalformedRequest
    from kerberos_lab.common.settings import load_settings

    config = tmp_path / "bad.toml"
    config.write_text(contents)
    with pytest.raises(MalformedRequest):
        load_settings(config, run_dir=tmp_path, role="resource")


def test_direct_settings_and_overrides_cannot_bypass_validation(tmp_path):
    from dataclasses import replace
    from kerberos_lab.common.errors import MalformedRequest
    from kerberos_lab.common.settings import load_settings

    settings = load_settings(None, run_dir=tmp_path, role="resource")
    for patch in ({"host": "0.0.0.0"}, {"port": True}, {"port": 0}, {"port": 65536},
                  {"role": "other"}, {"clock_offset_seconds": True},
                  {"frozen_time_seconds": -1}, {"ticket_lifetime_seconds": True},
                  {"run_dir": "not-a-path"}):
        with pytest.raises(MalformedRequest):
            replace(settings, **patch)
    with pytest.raises(MalformedRequest):
        load_settings(tmp_path / "missing.toml", run_dir=tmp_path, role="resource")
