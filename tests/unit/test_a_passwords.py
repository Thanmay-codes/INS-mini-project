"""Real password helpers checked against the fixed public KDF vectors."""

import json
from pathlib import Path

import pytest


VECTORS = json.loads((Path(__file__).parents[2] / "data/fixtures/contract/vectors-v1.json").read_text())


def test_password_helpers_accept_the_known_password_without_normalizing_it():
    from kerberos_lab.common.crypto import make_password_verifier, verify_password

    password = VECTORS["login_request"]["password"]
    assert verify_password(password, VECTORS["password_verifier"]) is True
    assert verify_password(" " + password, VECTORS["password_verifier"]) is False
    fresh = make_password_verifier(password)
    assert verify_password(password, fresh) is True
    assert fresh["salt"] != VECTORS["password_verifier"]["salt"]


@pytest.mark.parametrize("patch", [{"version": True}, {"algorithm": "other"},
    {"n": 8}, {"n": True}, {"r": 1}, {"p": 2}, {"salt": "AAAA"},
    {"digest": "BAD"}, {"extra": 1}])
def test_corrupt_or_unapproved_verifier_parameters_are_not_a_password_mismatch(patch):
    from kerberos_lab.common.crypto import verify_password
    from kerberos_lab.common.errors import MalformedRequest

    with pytest.raises(MalformedRequest):
        verify_password("public-fixture-only", {**VECTORS["password_verifier"], **patch})


@pytest.mark.parametrize("password", ["", True, b"bytes", "x" * 1025, "é" * 513, "\ud800"])
def test_password_input_is_bounded_in_utf8_bytes(password):
    from kerberos_lab.common.crypto import make_password_verifier, verify_password
    from kerberos_lab.common.errors import MalformedRequest

    with pytest.raises(MalformedRequest):
        make_password_verifier(password)
    with pytest.raises(MalformedRequest):
        verify_password(password, VECTORS["password_verifier"])


def test_service_password_key_matches_the_independent_pbkdf2_vector():
    from kerberos_lab.common.crypto import derive_service_key, decode_b64, encode_b64

    vector = VECTORS["service_kdf"]
    assert encode_b64(derive_service_key(vector["password"], salt=decode_b64(vector["salt"]))) == vector["derived_key"]


@pytest.mark.parametrize("iterations", [0, -1, True, 1.5, 1000001])
def test_service_derivation_rejects_out_of_budget_work_parameters(iterations):
    from kerberos_lab.common.crypto import derive_service_key
    from kerberos_lab.common.errors import MalformedRequest

    with pytest.raises(MalformedRequest):
        derive_service_key("password", salt=bytes(16), iterations=iterations)


@pytest.mark.parametrize("salt", [bytes(15), bytes(17), "not-bytes"])
def test_service_derivation_requires_an_exact_binary_salt(salt):
    from kerberos_lab.common.crypto import derive_service_key
    from kerberos_lab.common.errors import MalformedRequest

    with pytest.raises(MalformedRequest):
        derive_service_key("password", salt=salt)
