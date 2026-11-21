"""Public model/serialization behavior specified by the A01 contract."""

import json
from pathlib import Path

import pytest


VECTORS = json.loads((Path(__file__).parents[2] / "data/fixtures/contract/vectors-v1.json").read_text())


def test_ticket_round_trips_the_public_contract_vector():
    from kerberos_lab.common.models import Ticket

    value = VECTORS["ticket_plaintexts"]["service"]
    assert Ticket.from_dict(value).to_dict() == value


@pytest.mark.parametrize("patch", [
    {"version": True}, {"version": 2}, {"kind": "unknown"},
    {"ticket_id": "BAD"}, {"client_id": "Alice"}, {"service_id": "tgs"},
    {"issued_at": -1}, {"not_before": True}, {"expires_at": 1700000000},
    {"issued_at": 1700000001}, {"expires_at": 2**53},
    {"session_key": "not-base64"}, {"session_key": "AAAA"},
    {"unexpected": "field"},
])
def test_invalid_tickets_are_rejected_at_both_public_construction_seams(patch):
    from kerberos_lab.common.errors import MalformedRequest
    from kerberos_lab.common.models import Ticket

    value = {**VECTORS["ticket_plaintexts"]["service"], **patch}
    with pytest.raises(MalformedRequest):
        Ticket.from_dict(value)
    if "unexpected" not in patch:
        with pytest.raises(MalformedRequest):
            Ticket(**value)


@pytest.mark.parametrize("value", [None, [], {}, {"version": 1}])
def test_ticket_mapping_requires_the_complete_exact_schema(value):
    from kerberos_lab.common.errors import MalformedRequest
    from kerberos_lab.common.models import Ticket

    with pytest.raises(MalformedRequest):
        Ticket.from_dict(value)


def test_client_session_validates_the_separate_client_credentials():
    from kerberos_lab.common.errors import MalformedRequest
    from kerberos_lab.common.models import ClientSession

    value = VECTORS["service_response"]["client_session"]
    assert ClientSession.from_dict(value).to_dict() == value
    for patch in ({"expires_at": True}, {"session_key": "AAAA"},
                  {"ticket_id": "bad"}, {"service_id": "other"}):
        with pytest.raises(MalformedRequest):
            ClientSession(**{**value, **patch})
    with pytest.raises(MalformedRequest):
        ClientSession.from_dict({**value, "unexpected": 1})


def test_json_boundary_is_canonical_and_rejects_ambiguous_wire_inputs():
    from kerberos_lab.common.errors import MalformedRequest
    from kerberos_lab.common.models import canonical_bytes, parse_json_object

    assert canonical_bytes({"z": [True, None, -1], "a": "é"}) == b'{"a":"\\u00e9","z":[true,null,-1]}'
    assert parse_json_object(b'{ "version": 1 }') == {"version": 1}
    for raw in (b'{"x":1,"x":2}', b'[]', b'{"x":NaN}', b'{"x":1.0}',
                b'{"x":9007199254740992}', b'{"x":"\xff"}', b'{broken'):
        with pytest.raises(MalformedRequest):
            parse_json_object(raw)
    with pytest.raises(MalformedRequest):
        parse_json_object(b'{"x":1}', max_bytes=6)
    cycle = []
    cycle.append(cycle)
    for value in ({1: "key"}, {"x": 1.5}, {"x": object()}, {"x": "\ud800"}, cycle):
        with pytest.raises(MalformedRequest):
            canonical_bytes(value)
