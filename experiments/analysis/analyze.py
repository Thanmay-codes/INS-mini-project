"""Deterministically summarize B03 JSONL/CSV runs and write candidate outputs."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import html
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_ATTEMPTS_PER_TRIAL = {
    "E01": 1, "E02": 2, "E03": 2, "E04": 1, "E06": 1,
    "E07": 1, "E08": 1, "E09": 1, "E10": 1,
}
E04_PHASES = ("mutated_ticket", "mutated_authenticator", "mutated_body", "mutated_service")


class AnalysisError(ValueError):
    """Input evidence is incomplete or does not match the released schema."""


def nearest_rank(values: list[float], percentile: float) -> float | None:
    """Return the nearest-rank percentile: sorted[ceil(p*n)-1], p in (0,1]."""
    if not values:
        return None
    if not 0 < percentile <= 1:
        raise ValueError("percentile must be greater than 0 and at most 1")
    ordered = sorted(float(value) for value in values)
    rank = math.ceil(percentile * len(ordered))
    return round(ordered[rank - 1], 4)


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _mode(record: dict[str, Any]) -> str:
    return record.get("mode") or "not_applicable"


def _int(value: Any, *, default: int = 0) -> int:
    return value if type(value) is int else default


def _condition(record: dict[str, Any]) -> tuple[str, str, str, int, int]:
    return (
        str(record.get("scenario", "unknown")), _mode(record),
        str(record.get("phase", "unknown")), _int(record.get("worker_count")),
        _int(record.get("offset_seconds")),
    )


def scenario_summary(source: str, metadata: dict[str, Any],
                     attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group raw attempts by the full condition, preserving requested denominators."""
    denominator = _int(metadata.get("trials_per_scenario"))
    groups: dict[tuple[str, str, str, int, int], list[dict[str, Any]]] = {}
    for record in attempts:
        groups.setdefault(_condition(record), []).append(record)
    if "E04" in metadata.get("scenarios", []):
        for phase in E04_PHASES:
            groups.setdefault(("E04", "authenticator_cache", phase, 1, 0), [])
    rows: list[dict[str, Any]] = []
    for (scenario, mode, phase, workers, offset), records in sorted(groups.items()):
        expected_each = workers if scenario == "E05" else EXPECTED_ATTEMPTS_PER_TRIAL.get(scenario, 1)
        expected_attempts = denominator * expected_each
        observed_trials = {record.get("trial") for record in records if type(record.get("trial")) is int}
        failed_trials = {
            record.get("trial") for record in records
            if type(record.get("trial")) is int and record.get("expected_outcome") is False
        }
        accepted = [record for record in records if record.get("status") == 200 and record.get("accepted") is True]
        responses = [record for record in records if _int(record.get("status")) > 0]
        rejects = [record for record in records if 400 <= _int(record.get("status")) <= 599]
        latencies = [float(record["latency_ms"]) for record in records
                     if isinstance(record.get("latency_ms"), (int, float))
                     and math.isfinite(float(record["latency_ms"]))]
        startup_by_process: dict[tuple[Any, ...], float] = {}
        for record in records:
            if not (isinstance(record.get("startup_ms"), (int, float))
                    and math.isfinite(float(record["startup_ms"]))):
                continue
            process_key = (record.get("trial"), phase, offset, workers,
                           record.get("request_index") if scenario == "E05" else None)
            startup_by_process.setdefault(process_key, float(record["startup_ms"]))
        startup = list(startup_by_process.values())
        counters = [_int(record.get("counter")) for record in accepted
                    if type(record.get("counter")) is int]
        rows.append({
            "source_run": source, "scenario": scenario, "defense_mode": mode,
            "phase": phase, "worker_count": workers, "offset_seconds": offset,
            "requested_trials": denominator,
            "observed_trials": len(observed_trials),
            "missing_trials": max(0, denominator - len(observed_trials)),
            "failed_trials": len(failed_trials),
            "expected_attempt_denominator": expected_attempts,
            "observed_attempts": len(records),
            "missing_attempts": max(0, expected_attempts - len(records)),
            "completed_responses": len(responses), "accepted": len(accepted),
            "rejected_http_responses": len(rejects),
            "transport_failures": sum(_int(record.get("status")) == 0 for record in records),
            "protected_operations": len(accepted),
            "counter_max": max(counters) if counters else None,
            "acceptance_fraction_of_responses": round(len(accepted) / len(responses), 6) if responses else None,
            "latency_p50_ms": nearest_rank(latencies, 0.50),
            "latency_p95_ms": nearest_rank(latencies, 0.95),
            "startup_p50_ms": nearest_rank(startup, 0.50),
            "startup_p95_ms": nearest_rank(startup, 0.95),
        })
    return rows


def key_metrics(source: str, metadata: dict[str, Any],
                attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Calculate primary replay, legitimate-request and restart outcomes."""
    trials = _int(metadata.get("trials_per_scenario"))
    rows: list[dict[str, Any]] = []
    planned = set(metadata.get("scenarios", []))
    declared_modes = metadata.get("modes", [])
    duplicate_modes = sorted(set(declared_modes) if "E02" in planned else
                             {_mode(record) for record in attempts if record.get("scenario") == "E02"})
    for mode in duplicate_modes:
        duplicates = [record for record in attempts if record.get("scenario") == "E02"
                      and record.get("phase") == "exact_duplicate" and _mode(record) == mode
                      and _int(record.get("request_index")) > 1]
        duplicate_responses = [record for record in duplicates if _int(record.get("status")) > 0]
        duplicate_denominator = trials
        duplicate_accepted = sum(record.get("status") == 200 for record in duplicates)
        rows.append({
            "source_run": source, "metric": "duplicate_acceptance", "defense_mode": mode,
            "numerator": duplicate_accepted, "expected_denominator": duplicate_denominator,
            "attempted_duplicates": len(duplicates),
            "observed_denominator": len(duplicate_responses),
            "missing_observations": max(0, duplicate_denominator - len(duplicate_responses)),
            "fraction_expected_denominator": round(duplicate_accepted / duplicate_denominator, 6) if duplicate_denominator else None,
            "fraction_observed_denominator": round(duplicate_accepted / len(duplicate_responses), 6) if duplicate_responses else None,
            "protected_operations": sum(record.get("status") == 200 for record in duplicates),
        })

    legitimate_modes = sorted(set(declared_modes) if planned.intersection({"E01", "E03"}) else
                              {_mode(record) for record in attempts if record.get("scenario") in ("E01", "E03")})
    for mode in legitimate_modes:
        legitimate = [record for record in attempts if record.get("scenario") in ("E01", "E03")
                      and _mode(record) == mode]
        included_scenarios = planned.intersection({"E01", "E03"}) or {record["scenario"] for record in legitimate}
        expected_legitimate = trials * sum(1 if scenario == "E01" else 2
                                           for scenario in included_scenarios)
        completed = [record for record in legitimate if _int(record.get("status")) > 0]
        false_rejections = sum(400 <= _int(record.get("status")) <= 599 for record in legitimate)
        rows.append({
            "source_run": source, "metric": "legitimate_rejection", "defense_mode": mode,
            "numerator": false_rejections, "expected_denominator": expected_legitimate,
            "observed_denominator": len(completed),
            "missing_observations": max(0, expected_legitimate - len(completed)),
            "fraction_expected_denominator": round(false_rejections / expected_legitimate, 6) if expected_legitimate else None,
            "fraction_observed_denominator": round(false_rejections / len(completed), 6) if completed else None,
            "protected_operations": sum(record.get("status") == 200 for record in legitimate),
        })

    restart_modes = sorted({"authenticator_cache"} if "E06" in planned else set())
    restart_modes = sorted(set(restart_modes).union(
        {_mode(record) for record in attempts if record.get("scenario") == "E06"
         and record.get("phase") == "after_restart_exact_replay"}))
    for mode in restart_modes:
        restart = [record for record in attempts if record.get("scenario") == "E06"
                   and record.get("phase") == "after_restart_exact_replay" and _mode(record) == mode]
        restart_responses = [record for record in restart if _int(record.get("status")) > 0]
        restart_rejected = sum(record.get("status") == 409 for record in restart)
        rows.append({
            "source_run": source, "metric": "restart_replay_rejection", "defense_mode": mode,
            "numerator": restart_rejected, "expected_denominator": trials,
            "attempted_replays": len(restart),
            "observed_denominator": len(restart_responses),
            "missing_observations": max(0, trials - len(restart_responses)),
            "fraction_expected_denominator": round(restart_rejected / trials, 6) if trials else None,
            "fraction_observed_denominator": round(restart_rejected / len(restart_responses), 6) if restart_responses else None,
            "protected_operations": sum(record.get("status") == 200 for record in restart),
        })
    return rows


def time_categories(source: str, metadata: dict[str, Any],
                    attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trials = _int(metadata.get("trials_per_scenario"))
    selected = [record for record in attempts if record.get("scenario") in ("E07", "E08")]
    groups: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for record in selected:
        key = (str(record.get("scenario")), str(record.get("phase")),
               _int(record.get("offset_seconds")))
        groups.setdefault(key, []).append(record)
    rows = []
    for (scenario, phase, offset), records in sorted(groups.items()):
        reasons = [record.get("expected_time_reason") for record in records]
        rows.append({
            "source_run": source, "scenario": scenario, "phase": phase,
            "offset_seconds": offset,
            "requested_trials": trials,
            "observed_trials": len({record.get("trial") for record in records}),
            "missing_trials": max(0, trials - len({record.get("trial") for record in records})),
            "observed_attempts": len(records),
            "accepted": sum(record.get("status") == 200 for record in records),
            "invalid_authentication_responses": sum(record.get("error_code") == "invalid_authentication" for record in records),
            "ticket_time_valid_count": sum(record.get("ticket_time_valid") is True for record in records),
            "ticket_time_invalid_count": sum(record.get("ticket_time_valid") is False for record in records),
            "authenticator_time_valid_count": sum(record.get("authenticator_time_valid") is True for record in records),
            "authenticator_time_invalid_count": sum(record.get("authenticator_time_valid") is False for record in records),
            "ticket_validity_rejection_count": sum(reason == "ticket_validity" for reason in reasons),
            "authenticator_freshness_rejection_count": sum(reason == "authenticator_freshness" for reason in reasons),
            "no_time_rejection_expected_count": sum(reason in (None, "none") for reason in reasons),
            "other_time_reason_count": sum(reason not in (None, "none", "ticket_validity", "authenticator_freshness") for reason in reasons),
        })
    planned = set(metadata.get("scenarios", []))
    observed_keys = {(row["scenario"], row["phase"], row["offset_seconds"]) for row in rows}
    expected_time_conditions: list[tuple[str, str, int | None]] = []
    clock = metadata.get("clock", {})
    if "E07" in planned:
        expected_time_conditions.extend(("E07", "clock_offset", int(offset))
                                        for offset in clock.get("E07_offsets_seconds", []))
    if "E08" in planned:
        expected_time_conditions.extend(("E08", phase, None) for phase in (
            "before_not_before", "at_not_before_leeway", "inside_not_before",
            "inside_expiry", "at_expiry_leeway", "after_expiry"))
    for scenario, phase, offset in expected_time_conditions:
        observed_condition = ((scenario, phase, offset) in observed_keys if scenario == "E07"
                              else any(key_scenario == scenario and key_phase == phase
                                       for key_scenario, key_phase, _key_offset in observed_keys))
        if not observed_condition:
            rows.append({
                "source_run": source, "scenario": scenario, "phase": phase,
                "offset_seconds": offset,
                "requested_trials": trials, "observed_trials": 0,
                "missing_trials": trials, "observed_attempts": 0,
                "accepted": 0, "invalid_authentication_responses": 0,
                "ticket_time_valid_count": 0, "ticket_time_invalid_count": 0,
                "authenticator_time_valid_count": 0, "authenticator_time_invalid_count": 0,
                "ticket_validity_rejection_count": 0,
                "authenticator_freshness_rejection_count": 0,
                "no_time_rejection_expected_count": 0, "other_time_reason_count": 0,
            })
    return rows


def performance_summary(source: str, metadata: dict[str, Any],
                        attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = [record for record in attempts if record.get("scenario") in ("E01", "E02", "E03")]
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in selected:
        groups.setdefault((str(record.get("scenario")), _mode(record)), []).append(record)
    trial_denominator = _int(metadata.get("trials_per_scenario"))
    expected_counts = {"E01": 1, "E02": 2, "E03": 2}
    declared_modes = metadata.get("modes", [])
    for scenario in set(metadata.get("scenarios", [])).intersection(expected_counts):
        for mode in declared_modes:
            groups.setdefault((scenario, mode), [])
    rows = []
    for (scenario, mode), records in sorted(groups.items()):
        latency = [float(record["latency_ms"]) for record in records
                   if isinstance(record.get("latency_ms"), (int, float))
                   and math.isfinite(float(record["latency_ms"]))]
        startup_by_trial: dict[Any, float] = {}
        for record in records:
            if (isinstance(record.get("startup_ms"), (int, float))
                    and math.isfinite(float(record["startup_ms"]))):
                startup_by_trial.setdefault(record.get("trial"), float(record["startup_ms"]))
        startup = list(startup_by_trial.values())
        by_trial: dict[Any, list[float]] = {}
        for record in records:
            latency_value = record.get("latency_ms")
            if (type(record.get("trial")) is int
                    and isinstance(latency_value, (int, float))
                    and math.isfinite(float(latency_value))):
                by_trial.setdefault(record["trial"], []).append(float(latency_value))
        trial_medians = [median for trial in sorted(by_trial)
                         if (median := _median(by_trial[trial])) is not None]
        expected = trial_denominator * expected_counts[scenario]
        observed_trials = len({record.get("trial") for record in records})
        failed = len({record.get("trial") for record in records if record.get("expected_outcome") is False})
        rows.append({
            "source_run": source, "scenario": scenario, "defense_mode": mode,
            "requested_trials": trial_denominator, "observed_trials": observed_trials,
            "missing_trials": max(0, trial_denominator - observed_trials), "failed_trials": failed,
            "expected_attempt_denominator": expected, "observed_attempts": len(records),
            "missing_attempts": max(0, expected - len(records)),
            "accepted": sum(record.get("status") == 200 for record in records),
            "rejected_http_responses": sum(400 <= _int(record.get("status")) <= 599 for record in records),
            "transport_failures": sum(_int(record.get("status")) == 0 for record in records),
            "protected_operations": sum(record.get("status") == 200 for record in records),
            "latency_p50_ms": nearest_rank(latency, 0.50),
            "latency_p95_ms": nearest_rank(latency, 0.95),
            "trial_median_latency_p50_ms": nearest_rank(trial_medians, 0.50),
            "trial_median_latency_p95_ms": nearest_rank(trial_medians, 0.95),
            "startup_p50_ms": nearest_rank(startup, 0.50),
            "startup_p95_ms": nearest_rank(startup, 0.95),
        })
    return rows


def _read_run(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    path = path.resolve(strict=True)
    required = (path / "requests.jsonl", path / "summary.csv", path / "environment.json")
    if not all(item.is_file() for item in required):
        raise AnalysisError(f"{path} must contain requests.jsonl, summary.csv, and environment.json")
    metadata = json.loads(required[2].read_text(encoding="utf-8"))
    attempts = [json.loads(line) for line in required[0].read_text(encoding="utf-8").splitlines() if line.strip()]
    raw_summary = list(csv.DictReader(required[1].open("r", encoding="utf-8", newline="")))
    if _int(metadata.get("attempt_count"), default=-1) != len(attempts):
        raise AnalysisError(f"{path}: metadata attempt count does not match JSONL")
    failed = sum(record.get("expected_outcome") is False for record in attempts)
    if _int(metadata.get("failed_trial_attempts"), default=-1) != failed:
        raise AnalysisError(f"{path}: metadata failed count does not match JSONL")
    indexed: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in attempts:
        if not isinstance(record, dict) or not isinstance(record.get("scenario"), str):
            raise AnalysisError(f"{path}: invalid JSONL record")
        indexed.setdefault((record["scenario"], _mode(record)), []).append(record)
    for row in raw_summary:
        key = (row.get("scenario", ""), row.get("defense_mode", ""))
        values = indexed.get(key, [])
        try:
            observed_trials = {value.get("trial") for value in values if type(value.get("trial")) is int}
            failed_trials = {value.get("trial") for value in values
                             if type(value.get("trial")) is int and value.get("expected_outcome") is False}
            rejected = sum(_int(value.get("status")) not in (0, 200) for value in values)
            counts_match = (int(row["observed_attempts"]) == len(values)
                            and int(row["observed_trials"]) == len(observed_trials)
                            and int(row["accepted"]) == sum(value.get("status") == 200 for value in values)
                            and int(row["rejected"]) == rejected
                            and int(row["failed_trials"]) == len(failed_trials))
        except (KeyError, ValueError):
            counts_match = False
        if not counts_match:
            raise AnalysisError(f"{path}: summary CSV does not reconcile with JSONL for {key}")
    if {(row.get("scenario", ""), row.get("defense_mode", "")) for row in raw_summary} != set(indexed):
        raise AnalysisError(f"{path}: summary CSV is missing or adds scenario/mode groups")
    digest = {item.name: hashlib.sha256(item.read_bytes()).hexdigest() for item in required}
    return metadata, attempts, raw_summary, digest


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _svg(performance: list[dict[str, Any]]) -> str:
    performance = [row for row in performance
                   if _int(row.get("requested_trials")) >= 30
                   and _int(row.get("observed_trials")) == _int(row.get("requested_trials"))
                   and _int(row.get("failed_trials")) == 0
                   and _int(row.get("missing_attempts")) == 0]
    width, height = 1060, 500
    left, top, plot_width, plot_height = 90, 70, 900, 320
    max_value = max((float(row.get("latency_p95_ms") or 0) for row in performance), default=1.0)
    scale = plot_height / max(max_value * 1.15, 1.0)
    bar_width = 22
    group_width = plot_width / max(1, len(performance))
    pieces = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
              '<rect width="100%" height="100%" fill="white"/>',
              '<text x="530" y="32" text-anchor="middle" font-family="sans-serif" font-size="20">Candidate: E01-E03 request latency</text>',
              '<text x="18" y="235" transform="rotate(-90 18 235)" font-family="sans-serif" font-size="13">Latency (ms)</text>',
              f'<line x1="{left}" y1="{top+plot_height}" x2="{left+plot_width}" y2="{top+plot_height}" stroke="#333"/>']
    if not performance:
        pieces.append('<text x="540" y="225" text-anchor="middle" font-family="sans-serif" font-size="15">No complete 30-trial conditions in these inputs</text>')
    colors = {"p50": "#4778a8", "p95": "#e07a3f"}
    for index, row in enumerate(performance):
        center = left + group_width * (index + 0.5)
        for j, key in enumerate(("latency_p50_ms", "latency_p95_ms")):
            value = float(row.get(key) or 0)
            bar_height = value * scale
            x = center + (j - 0.5) * (bar_width + 3)
            y = top + plot_height - bar_height
            pieces.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width}" height="{bar_height:.1f}" fill="{colors["p50" if j == 0 else "p95"]}"/>')
        label = f'{row["scenario"]} {row["defense_mode"].replace("authenticator_", "")}'
        pieces.append(f'<text x="{center:.1f}" y="{top+plot_height+24}" text-anchor="middle" font-family="sans-serif" font-size="11">{html.escape(label)}</text>')
    pieces.extend([
        '<rect x="760" y="53" width="12" height="12" fill="#4778a8"/><text x="778" y="64" font-family="sans-serif" font-size="12">p50</text>',
        '<rect x="825" y="53" width="12" height="12" fill="#e07a3f"/><text x="843" y="64" font-family="sans-serif" font-size="12">p95</text>',
        '<text x="530" y="470" text-anchor="middle" font-family="sans-serif" font-size="12">Complete 30-trial groups only; incomplete groups remain in CSV. Candidate, not approved evidence.</text>',
        '</svg>',
    ])
    return "\n".join(pieces) + "\n"


def analyze(inputs: list[Path], output_dir: Path) -> Path:
    if not inputs:
        raise AnalysisError("at least one B03 result directory is required")
    output_dir = output_dir.resolve()
    figures_root = (ROOT / "results" / "figures").resolve()
    if not output_dir.is_relative_to(figures_root):
        raise AnalysisError("candidate output must be inside the ignored results/figures directory")
    if output_dir.exists():
        raise FileExistsError(f"output already exists: {output_dir}")
    sources = []
    scenario_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    time_rows: list[dict[str, Any]] = []
    performance_rows: list[dict[str, Any]] = []
    for input_path in inputs:
        metadata, attempts, _raw_summary, digests = _read_run(input_path)
        source_name = input_path.name
        sources.append({"source_run": source_name, "path": str(input_path.resolve()),
                        "runner_git_head": metadata.get("git_head"),
                        "scenario_order": metadata.get("scenario_order", metadata.get("scenarios")),
                        "trials_per_scenario": metadata.get("trials_per_scenario"),
                        "attempt_count": len(attempts),
                        "failed_attempts": sum(record.get("expected_outcome") is False for record in attempts),
                        "sha256": digests})
        scenario_rows.extend(scenario_summary(source_name, metadata, attempts))
        metric_rows.extend(key_metrics(source_name, metadata, attempts))
        time_rows.extend(time_categories(source_name, metadata, attempts))
        performance_rows.extend(performance_summary(source_name, metadata, attempts))
    output_dir.mkdir(parents=True)
    _write_csv(output_dir / "scenario_summary.csv", scenario_rows)
    _write_csv(output_dir / "primary_metrics.csv", metric_rows)
    _write_csv(output_dir / "time_categories.csv", time_rows)
    _write_csv(output_dir / "performance_summary.csv", performance_rows)
    (output_dir / "candidate_performance.svg").write_text(_svg(performance_rows), encoding="utf-8")
    run_metadata = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_code_git_head": _git_head(),
        "analysis_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "percentile_method": "nearest rank: sorted_values[ceil(p*n)-1], with p=0.50 or 0.95; no interpolation",
        "failed_and_missing_trials": "retained in requested, observed, missing, and failed columns; never silently dropped",
        "duplicate_acceptance": "E02 exact_duplicate with request_index > 1; numerator is HTTP 200, denominator is requested trials",
        "legitimate_rejection": "E01 and E03; HTTP 4xx/5xx are rejections, status 0 is a transport failure, denominators reported as both requested and completed responses",
        "time_reason_limit": "expected_time_reason is a runner-derived first check category, not a server diagnostic",
        "sources": sources,
        "outputs": ["scenario_summary.csv", "primary_metrics.csv", "time_categories.csv", "performance_summary.csv", "candidate_performance.svg"],
        "publication_state": "candidate only; not reviewed or published",
    }
    (output_dir / "analysis_metadata.json").write_text(json.dumps(run_metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_dir


def _git_head() -> str | None:
    import subprocess
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                text=True, timeout=3, check=True)
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="+", type=Path, help="B03 results/raw run directories")
    parser.add_argument("--output-dir", required=True, type=Path,
                        help="new ignored candidate output directory beneath results/figures")
    args = parser.parse_args(argv)
    try:
        output = analyze(args.runs, args.output_dir)
    except (AnalysisError, FileNotFoundError, FileExistsError, json.JSONDecodeError, OSError) as error:
        parser.error(str(error))
    print(json.dumps({"output_dir": str(output), "source_runs": len(args.runs)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
