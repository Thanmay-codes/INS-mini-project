"""Real library crypto through the released public API and independent vectors."""

import json
from pathlib import Path

import pytest


VECTORS = json.loads((Path(__file__).parents[2] / "data/fixtures/contract/vectors-v1.json").read_text())


@pytest.mark.parametrize("kind, response, field, key_name", [
    ("tgt", "login_response", "tgt", "tgs"),
    ("service", "service_response", "service_ticket", "service"),
])
def test_real_ticket_helpers_decrypt_independent_vectors_and_round_trip(kind, response, field, key_name):
    from kerberos_lab.common.crypto import decode_b64, open_ticket, seal_ticket
    from kerberos_lab.common.models import Ticket

    key = decode_b64(VECTORS["keys"][key_name], expected_length=32)
    expected = Ticket.from_dict(VECTORS["ticket_plaintexts"][kind])
    assert open_ticket(VECTORS[response][field], key, expected_kind=kind) == expected
    first = seal_ticket(expected, key)
    second = seal_ticket(expected, key)
    assert open_ticket(first, key, expected_kind=kind) == expected
    assert first["nonce"] != second["nonce"]


def test_ticket_tampering_wrong_keys_and_role_relabeling_never_decrypt():
    from kerberos_lab.common.crypto import decode_b64, encode_b64, open_ticket
    from kerberos_lab.common.errors import InvalidAuthentication, MalformedRequest

    envelope = VECTORS["service_response"]["service_ticket"]
    key = decode_b64(VECTORS["keys"]["service"])
    ciphertext = bytearray(decode_b64(envelope["ciphertext"]))
    ciphertext[0] ^= 1
    for altered, other_key, kind in (
        ({**envelope, "ciphertext": encode_b64(bytes(ciphertext))}, key, "service"),
        (envelope, bytes(32), "service"), (envelope, key, "tgt"),
        ({**envelope, "kind": "tgt"}, key, "tgt"),
    ):
        with pytest.raises(InvalidAuthentication):
            open_ticket(altered, other_key, expected_kind=kind)
    for patch in ({"version": True}, {"extra": 1}, {"nonce": "AAAA"},
                  {"ciphertext": "A" * 11000}, {"ciphertext": "AAAA"}):
        with pytest.raises(MalformedRequest):
            open_ticket({**envelope, **patch}, key, expected_kind="service")


@pytest.mark.parametrize("encoded", ["AA==\n", "AB==", "é", True, None, "===="])
def test_noncanonical_base64_is_rejected(encoded):
    from kerberos_lab.common.crypto import decode_b64
    from kerberos_lab.common.errors import MalformedRequest

    with pytest.raises(MalformedRequest):
        decode_b64(encoded)


@pytest.mark.parametrize("purpose, request_name, response_name, ticket_kind, envelope_name", [
    ("tgs", "service_request", "login_response", "tgt", "tgt"),
    ("resource", "resource_request", "service_response", "service", "service_ticket"),
])
def test_signing_and_verification_match_independent_domain_separated_vectors(
        purpose, request_name, response_name, ticket_kind, envelope_name):
    from kerberos_lab.common.crypto import sign_authenticator, verify_authenticator
    from kerberos_lab.common.models import ClientSession, Ticket

    request = VECTORS[request_name]
    session = ClientSession.from_dict(VECTORS[response_name]["client_session"])
    auth = sign_authenticator(session, request[envelope_name], request["body"],
                              purpose=purpose, timestamp=VECTORS["now"],
                              request_nonce=request["authenticator"]["request_nonce"])
    assert auth == request["authenticator"]
    assert verify_authenticator(auth, Ticket.from_dict(VECTORS["ticket_plaintexts"][ticket_kind]),
                                request[envelope_name], request["body"], purpose=purpose,
                                now=VECTORS["now"], skew=30) == auth


CASES = json.loads((Path(__file__).parents[2] / "data/fixtures/contract/cases-v1.json").read_text())["cases"]


@pytest.mark.parametrize("case", [case for case in CASES if case["name"] not in {
    "unknown_request_field", "unsupported_version"}], ids=lambda case: case["name"])
def test_declared_authentication_and_time_cases_exercise_actual_helpers(case):
    from kerberos_lab.common.crypto import decode_b64, open_ticket, verify_authenticator
    from kerberos_lab.common.errors import LabError

    request = case["request"]
    try:
        ticket = open_ticket(request["service_ticket"], decode_b64(VECTORS["keys"]["service"]),
                             expected_kind="service")
        result = verify_authenticator(request["authenticator"], ticket,
                                      request["service_ticket"], request["body"],
                                      purpose="resource", now=case["now"], skew=30)
    except LabError as error:
        assert error.http_status == case["expected_http"]
        if "expected_reason" in case:
            assert error.reason == case["expected_reason"]
    else:
        assert case["expected_http"] == 200
        assert result["request_nonce"] == request["authenticator"]["request_nonce"]


@pytest.mark.parametrize("patch", [
    {"client_id": "mallory"}, {"service_id": "tgs"}, {"ticket_id": "f" * 32},
    {"method": "GET"}, {"path": "/other"}, {"request_nonce": "f" * 32},
    {"body_sha256": "0" * 64}, {"ticket_sha256": "0" * 64},
])
def test_authenticated_request_fields_cannot_be_rewritten(patch):
    from kerberos_lab.common.crypto import verify_authenticator
    from kerberos_lab.common.errors import InvalidAuthentication
    from kerberos_lab.common.models import Ticket

    request = VECTORS["resource_request"]
    with pytest.raises(InvalidAuthentication):
        verify_authenticator({**request["authenticator"], **patch},
                             Ticket.from_dict(VECTORS["ticket_plaintexts"]["service"]),
                             request["service_ticket"], request["body"],
                             purpose="resource", now=VECTORS["now"], skew=30)


def test_body_envelope_and_purpose_are_bound_and_mac_failure_precedes_time():
    from kerberos_lab.common.crypto import verify_authenticator, sign_authenticator, seal_ticket, decode_b64
    from kerberos_lab.common.errors import InvalidAuthentication, MalformedRequest
    from kerberos_lab.common.models import ClientSession, Ticket

    req = VECTORS["service_request"]
    ticket = Ticket.from_dict(VECTORS["ticket_plaintexts"]["tgt"])
    with pytest.raises(InvalidAuthentication):
        verify_authenticator(req["authenticator"], ticket, req["tgt"], {"service_id": "other"},
                             purpose="tgs", now=VECTORS["now"], skew=30)
    other_envelope = seal_ticket(ticket, decode_b64(VECTORS["keys"]["tgs"]))
    with pytest.raises(InvalidAuthentication):
        verify_authenticator(req["authenticator"], ticket, other_envelope, req["body"],
                             purpose="tgs", now=VECTORS["now"], skew=30)
    with pytest.raises(InvalidAuthentication):
        verify_authenticator(req["authenticator"], ticket, req["tgt"], {"operation": "increment"},
                             purpose="resource", now=VECTORS["now"], skew=30)
    altered = {**req["authenticator"], "mac": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="}
    with pytest.raises(InvalidAuthentication) as caught:
        verify_authenticator(altered, ticket, req["tgt"], req["body"],
                             purpose="tgs", now=VECTORS["now"] + 1000, skew=30)
    assert caught.value.reason == "bad_integrity"
    with pytest.raises(MalformedRequest):
        verify_authenticator({**req["authenticator"], "extra": 1}, ticket, req["tgt"], req["body"],
                             purpose="tgs", now=VECTORS["now"], skew=30)
    session = ClientSession.from_dict(VECTORS["login_response"]["client_session"])
    # Authorization of an unsupported but authenticated TGS target belongs to B01.
    signed = sign_authenticator(session, req["tgt"], {"service_id": "other"},
                                purpose="tgs", timestamp=VECTORS["now"])
    assert verify_authenticator(signed, ticket, req["tgt"], {"service_id": "other"},
                                purpose="tgs", now=VECTORS["now"], skew=30) == signed


def test_new_client_requests_get_fresh_nonces_while_exact_replay_stays_valid_without_a_store():
    from kerberos_lab.common.crypto import sign_authenticator, verify_authenticator, new_key, new_identifier
    from kerberos_lab.common.models import ClientSession, Ticket

    req = VECTORS["resource_request"]
    session = ClientSession.from_dict(VECTORS["service_response"]["client_session"])
    first = sign_authenticator(session, req["service_ticket"], req["body"],
                               purpose="resource", timestamp=VECTORS["now"])
    second = sign_authenticator(session, req["service_ticket"], req["body"],
                                purpose="resource", timestamp=VECTORS["now"])
    assert first["request_nonce"] != second["request_nonce"]
    ticket = Ticket.from_dict(VECTORS["ticket_plaintexts"]["service"])
    for _ in range(2):
        assert verify_authenticator(first, ticket, req["service_ticket"], req["body"],
                                    purpose="resource", now=VECTORS["now"], skew=30) == first
    assert len(new_key()) == 32
    assert len(bytes.fromhex(new_identifier())) == 16
