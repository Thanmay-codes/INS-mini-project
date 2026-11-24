from experiments.analysis.analyze import (
    key_metrics,
    nearest_rank,
    performance_summary,
    scenario_summary,
    time_categories,
)


def _attempt(scenario, trial, phase, status, *, mode="authenticator_cache",
             index=1, offset=0, ticket_ok=None, auth_ok=None, reason=None,
             latency=1.0, counter=None, expected=True):
    return {
        "scenario": scenario, "trial": trial, "phase": phase, "mode": mode,
        "request_index": index, "worker_count": 1, "offset_seconds": offset,
        "status": status, "accepted": status == 200,
        "error_code": ({409: "replay_detected", 401: "invalid_authentication"}.get(status)),
        "expected_outcome": expected, "ticket_time_valid": ticket_ok,
        "authenticator_time_valid": auth_ok, "expected_time_reason": reason,
        "latency_ms": latency, "startup_ms": latency + 10,
        "counter": counter,
    }


def test_nearest_rank_percentiles_have_explicit_small_sample_behavior():
    assert nearest_rank([40, 10, 30, 20], 0.50) == 20
    assert nearest_rank([40, 10, 30, 20], 0.95) == 40
    assert nearest_rank([12], 0.50) == nearest_rank([12], 0.95) == 12
    assert nearest_rank([], 0.95) is None


def test_duplicate_and_legitimate_metrics_keep_expected_denominators():
    attempts = [
        _attempt("E02", 1, "exact_duplicate", 200, mode="authenticator_no_cache", index=1),
        _attempt("E02", 1, "exact_duplicate", 200, mode="authenticator_no_cache", index=2),
        _attempt("E02", 2, "exact_duplicate", 200, mode="authenticator_no_cache", index=1),
        _attempt("E02", 2, "exact_duplicate", 200, mode="authenticator_no_cache", index=2),
        _attempt("E02", 1, "exact_duplicate", 200, index=1),
        _attempt("E02", 1, "exact_duplicate", 409, index=2),
        _attempt("E02", 2, "exact_duplicate", 200, index=1),
        _attempt("E01", 1, "valid_request", 200, counter=1),
        _attempt("E01", 2, "valid_request", 200, counter=1),
        _attempt("E03", 1, "fresh_authenticator", 200, index=1, counter=1),
        _attempt("E03", 1, "fresh_authenticator", 200, index=2, counter=2),
        _attempt("E03", 2, "fresh_authenticator", 401, index=1),
    ]
    metrics = key_metrics("synthetic-check", {"trials_per_scenario": 2}, attempts)
    by_key = {(row["defense_mode"], row["metric"]): row for row in metrics}
    duplicate_no_cache = by_key[("authenticator_no_cache", "duplicate_acceptance")]
    assert (duplicate_no_cache["numerator"], duplicate_no_cache["expected_denominator"],
            duplicate_no_cache["fraction_expected_denominator"]) == (2, 2, 1.0)
    duplicate_cache = by_key[("authenticator_cache", "duplicate_acceptance")]
    assert (duplicate_cache["numerator"], duplicate_cache["expected_denominator"],
            duplicate_cache["observed_denominator"], duplicate_cache["missing_observations"]) == (0, 2, 1, 1)
    legitimate = by_key[("authenticator_cache", "legitimate_rejection")]
    assert (legitimate["numerator"], legitimate["expected_denominator"],
            legitimate["observed_denominator"], legitimate["missing_observations"]) == (1, 6, 5, 1)
    assert legitimate["fraction_observed_denominator"] == 0.2
    assert not any(row["metric"] == "restart_replay_rejection" for row in metrics)


def test_summary_counts_restart_time_categories_and_latency_deterministically():
    attempts = [
        _attempt("E05", 1, "concurrent_2", 200, counter=1),
        _attempt("E05", 1, "concurrent_2", 409, index=2),
        _attempt("E06", 1, "before_restart", 200, counter=1),
        _attempt("E06", 1, "after_restart_exact_replay", 409, index=2),
        _attempt("E07", 1, "clock_offset", 401, offset=60, ticket_ok=True,
                 auth_ok=False, reason="authenticator_freshness"),
        _attempt("E07", 2, "clock_offset", 401, offset=60, ticket_ok=True,
                 auth_ok=False, reason="authenticator_freshness"),
    ]
    meta = {"trials_per_scenario": 2}
    rows = scenario_summary("synthetic-check", meta, attempts)
    restart = next(row for row in rows if row["scenario"] == "E06"
                   and row["phase"] == "after_restart_exact_replay")
    assert restart["expected_attempt_denominator"] == 2
    assert restart["observed_attempts"] == 1
    assert restart["missing_attempts"] == 1
    times = time_categories("synthetic-check", meta, attempts)
    assert times == [{
        "source_run": "synthetic-check", "scenario": "E07", "phase": "clock_offset",
        "offset_seconds": 60,
        "requested_trials": 2, "observed_trials": 2, "missing_trials": 0,
        "observed_attempts": 2, "accepted": 0,
        "invalid_authentication_responses": 2,
        "ticket_time_valid_count": 2, "ticket_time_invalid_count": 0,
        "authenticator_time_valid_count": 0, "authenticator_time_invalid_count": 2,
        "ticket_validity_rejection_count": 0,
        "authenticator_freshness_rejection_count": 2,
        "no_time_rejection_expected_count": 0, "other_time_reason_count": 0,
    }]


def test_performance_summary_uses_measured_trial_and_attempt_denominators():
    attempts = [
        _attempt("E02", trial, "exact_duplicate", status, index=index,
                 latency=latency, expected=expected)
        for trial, (status, latency, expected) in enumerate(
            [(200, 5.0, True), (409, 15.0, True), (0, 100.0, False)], 1
        )
        for index in (1, 2)
    ]
    rows = performance_summary("synthetic-check", {"trials_per_scenario": 4}, attempts)
    row = rows[0]
    assert row["requested_trials"] == 4
    assert row["observed_trials"] == 3
    assert row["missing_trials"] == 1
    assert row["expected_attempt_denominator"] == 8
    assert row["observed_attempts"] == 6
    assert row["missing_attempts"] == 2
    assert row["failed_trials"] == 1
    assert row["latency_p50_ms"] == 15
    assert row["latency_p95_ms"] == 100
    assert row["trial_median_latency_p50_ms"] == 15
    assert row["trial_median_latency_p95_ms"] == 100


def test_missing_planned_conditions_remain_visible():
    metadata = {
        "trials_per_scenario": 30,
        "scenarios": ["E01", "E02", "E03", "E06", "E07"],
        "modes": ["authenticator_no_cache", "authenticator_cache"],
        "clock": {"E07_offsets_seconds": [-60, -15, 0, 15, 60]},
    }
    attempts = [_attempt("E01", 1, "valid_request", 200)]
    perf = performance_summary("synthetic-check", metadata, attempts)
    missing_e02 = [row for row in perf if row["scenario"] == "E02"]
    assert len(missing_e02) == 2
    assert all(row["requested_trials"] == 30 and row["observed_trials"] == 0
               and row["missing_trials"] == 30 and row["missing_attempts"] == 60
               for row in missing_e02)
    metrics = key_metrics("synthetic-check", metadata, attempts)
    missing_restart = next(row for row in metrics if row["metric"] == "restart_replay_rejection")
    assert (missing_restart["expected_denominator"], missing_restart["observed_denominator"],
            missing_restart["missing_observations"]) == (30, 0, 30)
    categories = time_categories("synthetic-check", metadata, attempts)
    e07 = [row for row in categories if row["scenario"] == "E07"]
    assert len(e07) == 5
    assert all(row["requested_trials"] == 30 and row["observed_trials"] == 0
               and row["missing_trials"] == 30 and row["observed_attempts"] == 0
               for row in e07)


def test_observed_e08_boundary_is_not_duplicated_as_missing():
    metadata = {"trials_per_scenario": 1, "scenarios": ["E08"], "clock": {}}
    attempts = [_attempt("E08", 1, "at_not_before_leeway", 200, offset=-30,
                         ticket_ok=True, auth_ok=True)]
    rows = time_categories("synthetic-check", metadata, attempts)
    observed = [row for row in rows if row["phase"] == "at_not_before_leeway"]
    assert len(observed) == 1
    assert observed[0]["observed_attempts"] == 1
    assert observed[0]["no_time_rejection_expected_count"] == 1


def _e04_attempts(trials, *, omit=()):
    mutations = ("ticket", "authenticator", "body", "service")
    return [
        _attempt("E04", trial, f"mutated_{mutation}", 401 if mutation != "body" else 400,
                 mode="authenticator_cache", index=index)
        for trial in range(1, trials + 1)
        for index, mutation in enumerate(mutations, 1)
        if (trial, mutation) not in omit
    ]


def test_e04_each_phase_has_one_attempt_per_requested_trial():
    phases = ("mutated_ticket", "mutated_authenticator", "mutated_body", "mutated_service")
    for trial_count in (1, 3):
        rows = scenario_summary(
            "synthetic-e04-complete",
            {"trials_per_scenario": trial_count, "scenarios": ["E04"]},
            _e04_attempts(trial_count),
        )
        e04 = [row for row in rows if row["scenario"] == "E04"]
        assert {row["phase"] for row in e04} == set(phases)
        assert all(row["expected_attempt_denominator"] == trial_count
                   and row["observed_attempts"] == trial_count
                   and row["missing_attempts"] == 0
                   and row["missing_trials"] == 0 for row in e04)


def test_e04_reports_partial_and_entirely_missing_phase_observations():
    metadata = {"trials_per_scenario": 3, "scenarios": ["E04"]}
    attempts = _e04_attempts(
        3, omit=((2, "ticket"), (1, "body"), (2, "body"), (3, "body"),
                 (1, "service"), (2, "service"), (3, "service")),
    )
    rows = scenario_summary("synthetic-e04-incomplete", metadata, attempts)
    by_phase = {row["phase"]: row for row in rows if row["scenario"] == "E04"}
    assert (by_phase["mutated_ticket"]["expected_attempt_denominator"],
            by_phase["mutated_ticket"]["observed_attempts"],
            by_phase["mutated_ticket"]["missing_attempts"]) == (3, 2, 1)
    assert (by_phase["mutated_body"]["expected_attempt_denominator"],
            by_phase["mutated_body"]["observed_attempts"],
            by_phase["mutated_body"]["missing_attempts"]) == (3, 0, 3)
    assert (by_phase["mutated_service"]["observed_trials"],
            by_phase["mutated_service"]["missing_trials"]) == (0, 3)


def test_e02_and_e03_keep_two_attempts_per_trial_in_shared_phase():
    trials = 3
    attempts = [
        _attempt("E02", trial, "exact_duplicate", status, index=index)
        for trial in range(1, trials + 1)
        for index, status in ((1, 200), (2, 409))
    ] + [
        _attempt("E03", trial, "fresh_authenticator", 200, index=index)
        for trial in range(1, trials + 1)
        for index in (1, 2)
    ]
    rows = scenario_summary("synthetic-e02-e03", {"trials_per_scenario": trials}, attempts)
    for scenario in ("E02", "E03"):
        row = next(item for item in rows if item["scenario"] == scenario)
        assert row["expected_attempt_denominator"] == trials * 2
        assert row["observed_attempts"] == trials * 2
        assert row["missing_attempts"] == 0
