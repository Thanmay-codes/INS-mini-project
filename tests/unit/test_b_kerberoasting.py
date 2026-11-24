"""Unit tests for the bounded synthetic password-guessing extension (B05)."""

from copy import deepcopy
from pathlib import Path
import socket

import pytest

from kerberos_lab.common.errors import MalformedRequest

from experiments.kerberoasting.runner import (
    acquire_synthetic_service_ticket,
    load_candidate_wordlist,
    verify_ticket_offline,
)


def test_e11_weak_password_recovered_from_bundled_wordlist():
    wordlist = load_candidate_wordlist(Path("data/wordlists/demo.txt"))
    artifact = acquire_synthetic_service_ticket(
        service_password="labservice",
        iterations=1_000,
    )
    result = verify_ticket_offline(artifact, wordlist)
    assert result["recovered"] is True
    assert result["outcome"] == "recovered"
    assert result["attempts"] == wordlist.index("labservice") + 1
    assert result["matched_candidate_index"] == wordlist.index("labservice") + 1
    assert result["elapsed_ms"] >= 0.0


def test_e12_random_password_not_recovered_within_list_budget():
    wordlist = load_candidate_wordlist(Path("data/wordlists/demo.txt"))
    artifact = acquire_synthetic_service_ticket(
        service_password="Zx9!not-in-demo-list-987654321",
        iterations=1_000,
    )
    result = verify_ticket_offline(artifact, wordlist)
    assert result["recovered"] is False
    assert result["outcome"] == "not_recovered_within_list_budget"
    assert result["attempts"] == len(wordlist)
    assert result["matched_candidate_index"] is None


def test_candidate_budget_stops_before_later_match():
    wordlist = load_candidate_wordlist(Path("data/wordlists/demo.txt"))
    artifact = acquire_synthetic_service_ticket(
        service_password="labservice",
        iterations=1_000,
    )
    result = verify_ticket_offline(artifact, wordlist, max_attempts=2)
    assert result["recovered"] is False
    assert result["outcome"] == "not_recovered_within_budget"
    assert result["attempts"] == 2
    assert result["matched_candidate_index"] is None


@pytest.mark.parametrize(
    "mutator",
    [
        lambda a: a.pop("kdf"),
        lambda a: a["kdf"].__setitem__("algorithm", "rc4"),
        lambda a: a["kdf"].__setitem__("salt", "not-base64!"),
        lambda a: a["kdf"].__setitem__("iterations", 0),
        lambda a: a["service_ticket"].__setitem__("kind", "tgt"),
        lambda a: a["service_ticket"].__setitem__("ciphertext", "AAAA"),
    ],
)
def test_malformed_artifact_is_distinguished_from_wrong_guess(mutator):
    artifact = acquire_synthetic_service_ticket(
        service_password="labservice",
        iterations=1_000,
    )
    broken = deepcopy(artifact)
    mutator(broken)
    with pytest.raises(MalformedRequest):
        verify_ticket_offline(broken, ["welcome", "labservice"])


def test_offline_verifier_makes_no_network_calls(monkeypatch):
    def forbid_network(*_args, **_kwargs):
        raise AssertionError("offline verifier must not open network sockets")

    monkeypatch.setattr(socket, "create_connection", forbid_network)
    monkeypatch.setattr(socket.socket, "connect", forbid_network)

    artifact = acquire_synthetic_service_ticket(
        service_password="labservice",
        iterations=1_000,
    )
    result = verify_ticket_offline(artifact, ["welcome", "labservice"])
    assert result["recovered"] is True
    assert result["attempts"] == 2
