"""Integration tests for the E11/E12 bounded Kerberoasting-inspired runner (B05)."""

import csv
import json
from pathlib import Path
import subprocess
import sys


def test_kerberoasting_cli_runs_e11_and_e12_and_sanitizes_outputs(tmp_path):
    output_dir = tmp_path / "b05-run"
    command = [
        sys.executable,
        "experiments/kerberoasting/runner.py",
        "--output-dir",
        str(output_dir),
        "--iterations",
        "1000",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stderr

    results_path = output_dir / "results.jsonl"
    summary_path = output_dir / "summary.csv"
    env_path = output_dir / "environment.json"
    assert results_path.is_file()
    assert summary_path.is_file()
    assert env_path.is_file()

    records = [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines()]
    assert [r["case_id"] for r in records] == ["E11", "E12"]
    e11, e12 = records
    assert e11["password_class"] == "weak_in_list"
    assert e11["recovered"] is True
    assert e11["outcome"] == "recovered"
    assert e12["password_class"] == "random_absent"
    assert e12["recovered"] is False
    assert e12["outcome"] == "not_recovered_within_list_budget"
    assert e11["iterations"] == e12["iterations"] == 1000
    assert e11["wordlist_size"] == e12["wordlist_size"] == 5
    assert e12["attempts"] == 5

    # Ensure no plaintext passwords or raw ciphertext leak into summary outputs.
    for raw_text in (results_path.read_text(), summary_path.read_text(), env_path.read_text()):
        assert "labservice" not in raw_text
        assert "ciphertext" not in raw_text

    rows = list(csv.DictReader(summary_path.open(encoding="utf-8", newline="")))
    assert len(rows) == 2
    assert rows[0]["case_id"] == "E11" and rows[0]["recovered"] == "true"
    assert rows[1]["case_id"] == "E12" and rows[1]["recovered"] == "false"

    env = json.loads(env_path.read_text(encoding="utf-8"))
    assert env["kdf_algorithm"] == "pbkdf2_hmac_sha256"
    assert env["iterations"] == 1000
    assert env["network_calls_during_verification"] == 0
