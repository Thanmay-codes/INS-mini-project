import json
from experiments.replay.runner import (
    Attempt,
    SCENARIOS,
    _alter_request,
    _percentile,
    _summary,
    _time_conditions,
    run,
)


def test_runner_declares_all_core_scenarios_and_preserves_time_edges():
    assert SCENARIOS == tuple(f"E{i:02d}" for i in range(1, 11))
    assert _time_conditions(100, 200, 69, 69) == (False, True, "ticket_validity")
    assert _time_conditions(100, 200, 70, 70) == (True, True, None)
    assert _time_conditions(100, 200, 70, 71) == (True, True, None)
    assert _time_conditions(100, 200, 100, 131) == (True, False, "authenticator_freshness")
    assert _time_conditions(100, 200, 300, 231) == (False, False, "ticket_validity")


def test_runner_emits_distinct_byte_mutations_without_touching_the_capture():
    original = {
        "version": 1,
        "service_ticket": {"kind": "service", "ciphertext": "AQID", "nonce": "AQID"},
        "authenticator": {"mac": "AQID", "service_id": "files"},
        "body": {"operation": "increment"},
    }
    raw = json.dumps(original, sort_keys=True, separators=(",", ":")).encode()
    for mutation in ("ticket", "authenticator", "body", "service"):
        changed = _alter_request(raw, mutation)
        assert changed != raw
        assert json.loads(changed) != original
    assert json.loads(raw) == original


def test_summary_preserves_requested_trial_denominator_and_failures():
    attempts = [
        Attempt("E01", 1, "valid", "authenticator_cache", 0, 1, 1,
                200, None, True, 1, 1.0, 4.0),
        Attempt("E01", 2, "valid", "authenticator_cache", 0, 1, 1,
                0, "transport_failure", False, None, 2.0, 4.0,
                expected_outcome=False),
    ]
    row = _summary(attempts, trials=3)[0]
    assert row["requested_trials"] == row["trial_denominator"] == 3
    assert row["observed_trials"] == 2
    assert row["failed_trials"] == 1
    assert row["protected_operations"] == 1
    assert _percentile([], 0.5) is None
    assert _percentile([1.0, 2.0, 3.0, 100.0], 0.95) == 100.0


def test_real_process_smoke_runs_e01_through_e10(tmp_path):
    output, attempts = run(
        scenarios=SCENARIOS,
        trials=1,
        output_dir=tmp_path / "evidence",
        private_root=tmp_path / "private",
    )
    assert {attempt.scenario for attempt in attempts} == set(SCENARIOS)
    assert all(attempt.expected_outcome for attempt in attempts)
    assert (output / "requests.jsonl").is_file()
    assert (output / "summary.csv").is_file()
    metadata = json.loads((output / "environment.json").read_text())
    assert metadata["expected_trial_denominator"] == 1
    assert metadata["scenario_order"] == list(SCENARIOS)
    assert metadata["scenario_seed"] is None

    e02 = [attempt for attempt in attempts if attempt.scenario == "E02"]
    assert [(item.mode, item.status) for item in e02] == [
        ("authenticator_no_cache", 200),
        ("authenticator_no_cache", 200),
        ("authenticator_cache", 200),
        ("authenticator_cache", 409),
    ]
    e05 = [attempt for attempt in attempts if attempt.scenario == "E05"]
    for workers in (2, 4, 8):
        concurrent = [item for item in e05 if item.worker_count == workers]
        assert sum(item.status == 200 for item in concurrent) == 1
        assert sum(item.status == 409 for item in concurrent) == workers - 1
