"""Offline proposed codec/vector specimen, never an installation or runtime verifier."""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import ipaddress
import json
import math
import re
import struct
import unicodedata
from pathlib import Path

PREFIX = b"researchbase.bearing.binding.v1\x00"
MAX_RECORD = 65536
MAX_JSON_DEPTH = 8
MAX_INTEGER_DIGITS = 20
PG_FIELDS = (
    "oid",
    "proname",
    "pronamespace",
    "proowner",
    "prolang",
    "procost",
    "prorows",
    "provariadic",
    "prosupport",
    "prokind",
    "prosecdef",
    "proleakproof",
    "proisstrict",
    "proretset",
    "provolatile",
    "proparallel",
    "pronargs",
    "pronargdefaults",
    "prorettype",
    "proargtypes",
    "proallargtypes",
    "proargmodes",
    "proargnames",
    "proargdefaults",
    "protrftypes",
    "prosrc",
    "probin",
    "prosqlbody",
    "proconfig",
    "proacl",
)


class Denied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise Denied(reason)


def array(v, size, tag):
    need(type(v) is list and len(v) == size, tag)


def uint(v, bits=64, positive=False):
    need(type(v) is int and int(positive) <= v < 2**bits, "INTEGER")


def oid(v, zero=False):
    uint(v, 32, not zero)


def text(v, cap=1024, *, empty=False, body=False):
    need(type(v) is str, "TEXT")
    need(unicodedata.normalize("NFC", v) == v, "NFC")
    need(not any(0xD800 <= ord(c) <= 0xDFFF or c == "\x00" for c in v), "TEXT")
    need(
        not any(unicodedata.category(c) == "Cc" and not (body and c in "\n\t\r") for c in v),
        "TEXT",
    )
    need(int(not empty) <= len(v.encode("utf8")) <= cap, "TEXT_LIMIT")


def digest(v):
    need(type(v) is str and re.fullmatch(r"[0-9a-f]{64}", v) is not None, "DIGEST")


def path(v):
    text(v, 4096)
    need(v.startswith("/") and v != "/" and not v.endswith("/"), "PATH")
    need(all(p not in ("", ".", "..") for p in v[1:].split("/")), "PATH")


def utc(v):
    need(type(v) is str and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z", v), "UTC")
    try:
        return dt.datetime.strptime(v, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=dt.UTC)
    except ValueError as exc:
        raise Denied("UTC") from exc


def bools(values):
    need(all(type(v) is bool for v in values), "BOOL")


def optional_array(v, cap, element):
    if v is None:
        return
    need(type(v) is list and len(v) <= cap, "ARRAY_LIMIT")
    for item in v:
        element(item)


def roles(v, dbowner, functionowner):
    array(v, 4, "ROLES")
    session, current, rows, edges = v
    oid(session)
    oid(current)
    need(type(rows) is list and 1 <= len(rows) <= 128, "ROLE_LIMIT")
    ids = []
    for row in rows:
        array(row, 9, "ROLE_ROW")
        oid(row[0])
        text(row[1], 63)
        bools(row[2:])
        ids.append(row[0])
    need(ids == sorted(set(ids)), "ROLE_ORDER")
    need({session, current, dbowner, functionowner} <= set(ids), "ROLE_MISSING")
    need(type(edges) is list and len(edges) <= 256, "EDGE_LIMIT")
    for edge in edges:
        array(edge, 6, "EDGE")
        for x in edge[:3]:
            oid(x)
        bools(edge[3:])
        need(edge[0] in ids and edge[1] in ids and edge[2] in ids, "ROLE_MISSING")
    need(edges == sorted(edges) and len({tuple(e) for e in edges}) == len(edges), "EDGE_ORDER")
    # Conservative consumer writer profile, not migration-role activation authority.
    reachable = {session, current}
    while True:
        expanded = reachable | {e[0] for e in edges if e[1] in reachable}
        if expanded == reachable:
            break
        reachable = expanded
    for row in rows:
        if row[0] in reachable:
            need(not any(row[i] for i in (2, 4, 5, 7, 8)), "WRITER_PRIVILEGE")
    # The graph deliberately rejects any membership route to owner, even options-false.
    need(not ({dbowner, functionowner} & reachable), "OWNER_REACHABLE")
    need(not any(e[3] for e in edges if e[1] in reachable), "WRITER_ADMIN")


def acl(v, owner):
    array(v, 3, "ACL")
    kind, raw, effective = v
    need(kind in ("NULL", "ARRAY"), "ACL_KIND")
    if kind == "NULL":
        need(raw is None, "ACL_NULL")
    else:
        need(type(raw) is list and len(raw) <= 32, "ACL_LIMIT")
        for x in raw:
            text(x, 2048)
    need(type(effective) is list and len(effective) <= 64, "ACL_LIMIT")
    for grant in effective:
        array(grant, 4, "ACL_GRANT")
        oid(grant[0])
        oid(grant[1], zero=True)
        need(grant[2] == "EXECUTE", "ACL_PRIVILEGE")
        bools(grant[3:])
    need(
        effective == sorted(effective) and len({tuple(x) for x in effective}) == len(effective),
        "ACL_ORDER",
    )
    if kind == "NULL":
        need(
            effective == [[owner, 0, "EXECUTE", False], [owner, owner, "EXECUTE", False]],
            "ACL_DEFAULT",
        )
    if kind == "ARRAY" and raw == []:
        need(effective == [], "ACL_EMPTY")


def catalog(v):
    array(v, 35, "CATALOG_SHAPE")
    for i in (0, 2, 3, 4, 18):
        oid(v[i])
    for i in (7, 8):
        oid(v[i], zero=True)
    need(v[1] == "pr316d1_enabled", "FUNCTION_NAME")
    for i in (5, 6):
        need(type(v[i]) is str and re.fullmatch(r"[0-9a-f]{8}", v[i]), "FLOAT4_BITS")
        value = struct.unpack("!f", bytes.fromhex(v[i]))[0]
        need(math.isfinite(value) and value >= 0 and not (int(v[i], 16) >> 31), "FLOAT4_FINITE")
    need(v[9] == "f" and v[14] == "s" and v[15] in ("s", "r", "u"), "FUNCTION_FLAGS")
    bools(v[10:14])
    need(v[10] is False and v[13] is False, "FUNCTION_FLAGS")
    need(
        v[16] == 0 and type(v[16]) is int and v[17] == 0 and type(v[17]) is int and v[18] == 16,
        "SIGNATURE",
    )
    need(v[19] == [], "SIGNATURE")
    optional_array(v[20], 128, oid)
    optional_array(v[21], 128, lambda x: need(x in ("i", "o", "b", "v", "t"), "ARG_MODE"))
    optional_array(v[22], 128, lambda x: text(x, 1024, empty=True))
    for i in (23, 26, 27):
        if v[i] is not None:
            text(v[i], 8192, empty=True, body=True)
    optional_array(v[24], 128, oid)
    text(v[25], 8192, body=True)
    optional_array(v[28], 16, lambda x: text(x, 2048))
    acl(v[29], v[3])
    need(
        v[30] == "public" and v[31] == "sql" and v[32] == "" and v[33] == "boolean",
        "FUNCTION_IDENTITY",
    )
    text(v[34], 16384, body=True)


def validate(v, at):
    array(v, 18, "RECORD_SHAPE")
    need(type(v[0]) is int and v[0] == 1, "VERSION")
    for i in (1, 2, 3, 4, 9, 10, 12):
        text(v[i])
    uint(v[5])
    expiry = utc(v[6])
    need(at < expiry, "EXPIRED")
    for i in (7, 8, 11):
        digest(v[i])
    need(
        v[9:11] == ["researchbase.agent_runtime.domain.bearing_evaluation", "evaluate"], "CALLABLE"
    )
    need(v[13] == "SINGLE_HOST_LOCAL_FS", "TOPOLOGY")
    db = v[14]
    array(db, 11, "DATABASE")
    need(type(db[0]) is str and re.fullmatch(r"[1-9][0-9]{0,19}", db[0]), "SYSTEM_ID")
    need(int(db[0]) < 2**64, "SYSTEM_ID")
    uint(db[1], 32)
    need(180000 <= db[1] < 190000, "PG_VERSION")
    if db[2] == "UNIX":
        need(db[3:5] == [None, None], "ENDPOINT_NULL")
    elif db[2] == "LOOPBACK_TCP":
        need(type(db[3]) is str and "%" not in db[3], "ADDRESS")
        try:
            address = ipaddress.ip_address(db[3])
        except ValueError as exc:
            raise Denied("ADDRESS") from exc
        need(address.is_loopback and not getattr(address, "ipv4_mapped", None), "ADDRESS")
        need(str(address) == db[3], "ADDRESS_CANONICAL")
        uint(db[4], 16, True)
    else:
        raise Denied("TRANSPORT")
    text(db[5], 63)
    oid(db[6])
    oid(db[7])
    text(db[8], 128)
    digest(db[10])
    catalog(v[15])
    roles(db[9], db[7], v[15][3])
    array(v[16], 6, "CAS")
    path(v[16][0])
    text(v[16][1])
    for x in v[16][2:5]:
        uint(x)
    need(type(v[16][5]) is int and v[16][5] == 0o700, "CAS_MODE")
    array(v[17], 5, "LEASE")
    path(v[17][0])
    for x in v[17][1:4]:
        uint(x)
    need(type(v[17][4]) is int and v[17][4] == 0o600, "LEASE_MODE")
    need(v[16][4] == v[17][3] == v[5], "UID_BINDING")


def encode(v):
    return PREFIX + json.dumps(
        v, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf8")


def json_structure_bound(body):
    """Count only unquoted delimiters; no recursive parse or schema trust."""
    depth = 0
    quoted = False
    escaped = False
    for byte in body:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 0x5C:
                escaped = True
            elif byte == 0x22:
                quoted = False
        elif byte == 0x22:
            quoted = True
        elif byte in (0x5B, 0x7B):
            depth += 1
            need(depth <= MAX_JSON_DEPTH, "JSON_DEPTH")
        elif byte in (0x5D, 0x7D):
            depth -= 1
            need(depth >= 0, "JSON_STRUCTURE")
    # json.loads remains responsible for syntax/closing delimiter correctness.


def json_integer(token):
    digits = token.removeprefix("-")
    need(len(digits) <= MAX_INTEGER_DIGITS, "JSON_INTEGER_LIMIT")
    return int(token)


def decode(raw, *, expected=None, at=None):
    need(type(raw) is bytes and len(raw) <= MAX_RECORD, "RECORD_LIMIT")
    need(raw.startswith(PREFIX), "DOMAIN")
    json_structure_bound(raw[len(PREFIX) :])
    try:
        v = json.loads(
            raw[len(PREFIX) :].decode("utf8"),
            parse_constant=lambda _: (_ for _ in ()).throw(Denied("JSON_CONSTANT")),
            parse_int=json_integer,
        )
    except Denied:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise Denied("JSON") from exc
    validate(v, at or dt.datetime(2029, 1, 1, tzinfo=dt.UTC))
    need(encode(v) == raw, "NONCANONICAL_BYTES")
    if expected is not None:
        need(raw == expected, "APPROVED_BINDING_MISMATCH")
    return v


def sample():
    # Every ID/path/hash here is synthetic. This fixture authorizes no deployment.
    owner, writer = 20002, 20001
    rows = [
        [writer, "fixture_writer", False, True, False, False, True, False, False],
        [owner, "fixture_owner", False, True, False, False, False, False, False],
    ]
    function = [
        90001,
        "pr316d1_enabled",
        2200,
        owner,
        14,
        "42c80000",
        "00000000",
        0,
        0,
        "f",
        False,
        False,
        False,
        False,
        "s",
        "u",
        0,
        0,
        16,
        [],
        None,
        None,
        None,
        None,
        None,
        "SELECT false",
        None,
        None,
        ["search_path=pg_catalog, public, pg_temp"],
        ["NULL", None, [[owner, 0, "EXECUTE", False], [owner, owner, "EXECUTE", False]]],
        "public",
        "sql",
        "",
        "boolean",
        "CREATE OR REPLACE FUNCTION public.pr316d1_enabled()\n RETURNS boolean\n LANGUAGE sql\n STABLE\n SET search_path TO 'pg_catalog', 'public', 'pg_temp'\nAS $function$SELECT false$function$\n",
    ]
    return [
        1,
        "fixture-deployment",
        "synthetic-Café",
        "fixture-ns",
        "fixture-host.invalid",
        1000,
        "2030-01-01T00:00:00.000000Z",
        "a" * 64,
        "b" * 64,
        "researchbase.agent_runtime.domain.bearing_evaluation",
        "evaluate",
        "c" * 64,
        "fixture-root",
        "SINGLE_HOST_LOCAL_FS",
        [
            "1000000000000000001",
            180000,
            "UNIX",
            None,
            None,
            "fixture_db",
            30001,
            owner,
            "fixture_revision",
            [writer, writer, rows, []],
            "d" * 64,
        ],
        function,
        ["/fixture/cas", "fixture-ns", 1, 2, 1000, 448],
        ["/fixture/lease", 1, 3, 1000, 384],
    ]


def main():
    here = Path(__file__).resolve().parent
    base = sample()
    baseline = encode(base)
    vectors = []

    def emit(name, raw, accepted, *, expected=None, at=None):
        reason = None
        try:
            decode(raw, expected=expected, at=at)
        except Denied as exc:
            reason = str(exc)
        need((reason is None) == accepted, f"SPECIMEN_RESULT:{name}:{reason}")
        path = here / "literal-bytes" / f"{name}.bin"
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(raw)
        vectors.append(
            dict(
                id=name,
                expected="ACCEPT_CODEC_ONLY" if accepted else "REJECT",
                rejection=reason,
                byte_length=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(),
                bytes_file=str(path.relative_to(here)),
                literal_utf8=raw.decode("utf8", errors="backslashreplace"),
                bytes_hex=raw.hex(),
                expected_binding_sha256=hashlib.sha256(expected).hexdigest()
                if expected is not None
                else None,
                at_utc=at.isoformat() if at else "2029-01-01T00:00:00+00:00",
            )
        )

    emit("positive-unix-null", baseline, True)
    v = copy.deepcopy(base)
    v[14][2:5] = ["LOOPBACK_TCP", "127.0.0.1", 5432]
    emit("positive-ipv4", encode(v), True)
    v[14][3] = "::1"
    emit("positive-ipv6", encode(v), True)
    v = copy.deepcopy(base)
    v[15][29] = ["ARRAY", [], []]
    emit("positive-acl-empty", encode(v), True)
    for name, change in [
        ("bool-uid", lambda v: v.__setitem__(5, True)),
        ("float-uid", lambda v: v.__setitem__(5, 1000.0)),
        ("utc-offset", lambda v: v.__setitem__(6, "2030-01-01T00:00:00.000000+00:00")),
        ("oid-overflow", lambda v: v[14].__setitem__(6, 2**32)),
        (
            "role-limit",
            lambda v: v[14][9].__setitem__(
                2,
                [
                    [20001 + i, "fixture_role", False, True, False, False, False, False, False]
                    for i in range(129)
                ],
            ),
        ),
        (
            "edge-limit",
            lambda v: v[14][9].__setitem__(3, [[20002, 20001, 20002, False, False, False]] * 257),
        ),
        ("edge-missing-option", lambda v: v[14][9][3].append([20002, 20001, 20002, False, False])),
        ("acl-privilege", lambda v: v[15][29][2][0].__setitem__(2, "CREATE")),
        (
            "acl-raw-limit",
            lambda v: v[15].__setitem__(29, ["ARRAY", ["fixture=unknown/fixture"] * 33, []]),
        ),
        ("config-limit", lambda v: v[15].__setitem__(28, ["fixture=unknown"] * 17)),
        ("nfd-text", lambda v: v.__setitem__(2, "synthetic-Cafe\u0301")),
        ("unix-port-nonnull", lambda v: v[14].__setitem__(4, 5432)),
        (
            "ip-noncanonical",
            lambda v: v[14].__setitem__(slice(2, 5), ["LOOPBACK_TCP", "0:0:0:0:0:0:0:1", 5432]),
        ),
        (
            "ip-remote",
            lambda v: v[14].__setitem__(slice(2, 5), ["LOOPBACK_TCP", "192.0.2.1", 5432]),
        ),
        (
            "ip-mapped",
            lambda v: v[14].__setitem__(slice(2, 5), ["LOOPBACK_TCP", "::ffff:127.0.0.1", 5432]),
        ),
        ("missing-position", lambda v: v.pop()),
        ("extra-position", lambda v: v.append("extra")),
        ("wrong-callable", lambda v: v.__setitem__(10, "evaluate_bytes")),
        ("catalog-extra-field", lambda v: v[15].append("extra")),
        ("float4-nan", lambda v: v[15].__setitem__(5, "7fc00000")),
        ("acl-null-empty-confusion", lambda v: v[15][29].__setitem__(1, [])),
        ("unsafe-path", lambda v: v[16].__setitem__(0, "/fixture/../cas")),
        ("oversized-body", lambda v: v[15].__setitem__(25, "x" * 8193)),
        (
            "set-owner-reachable",
            lambda v: v[14][9][3].append([20002, 20001, 20002, False, False, True]),
        ),
        (
            "inherit-owner-reachable",
            lambda v: v[14][9][3].append([20002, 20001, 20002, False, True, False]),
        ),
    ]:
        v = copy.deepcopy(base)
        change(v)
        emit("negative-" + name, encode(v), False)
    membership = copy.deepcopy(base)
    membership[14][9][2].append(
        [20004, "fixture_member_role", False, True, False, False, False, False, False]
    )
    membership[14][9][3].append([20004, 20001, 20002, False, False, False])
    membership_bytes = encode(membership)
    emit("positive-restricted-membership", membership_bytes, True)
    for flag, label in [(4, "inherit"), (5, "set")]:
        changed = copy.deepcopy(membership)
        changed[14][9][3][0][flag] = True
        emit(
            "negative-expected-membership-" + label,
            encode(changed),
            False,
            expected=membership_bytes,
        )
    transitive = copy.deepcopy(membership)
    transitive[14][9][3].insert(0, [20002, 20004, 20002, False, False, True])
    emit("negative-transitive-owner", encode(transitive), False)
    emit("negative-expiry-equality", baseline, False, at=dt.datetime(2030, 1, 1, tzinfo=dt.UTC))
    emit("negative-extra-whitespace", PREFIX + b" " + baseline[len(PREFIX) :], False)
    emit("negative-unicode-escape-alias", baseline.replace("é".encode(), b"\\u00e9"), False)
    emit("negative-trailing-data", baseline + b"[]", False)
    emit("negative-bom", b"\xef\xbb\xbf" + baseline, False)
    emit("negative-invalid-utf8", PREFIX + b"[" + b"\xff" + b"]", False)
    emit("negative-record-limit", PREFIX + b" " * 65537, False)
    v = copy.deepcopy(base)
    v[15][29] = ["ARRAY", [], []]
    emit("negative-expected-acl-null", encode(v), False, expected=baseline)
    v = copy.deepcopy(base)
    v[14][9][2][0][3] = False
    emit("negative-expected-role-option", encode(v), False, expected=baseline)
    for label, value in [("DEL", "\u007f"), ("C1", "\u0085")]:
        for field in ("host", "path", "body"):
            changed = copy.deepcopy(base)
            if field == "host":
                changed[4] = "fixture" + value + "host"
            elif field == "path":
                changed[16][0] = "/fixture/" + value + "cas"
            else:
                changed[15][25] = "SELECT" + value + "false"
            emit("negative-control-" + field + "-" + label, encode(changed), False)
    emit("negative-depth15000-array", PREFIX + b"[" * 15000 + b"0" + b"]" * 15000, False)
    emit("negative-depth9-object", PREFIX + b'{"x":' * 9 + b"0" + b"}" * 9, False)
    emit("negative-depth9-array", PREFIX + b"[" * 9 + b"0" + b"]" * 9, False)
    emit("negative-depth8-wrong-record", PREFIX + b"[" * 8 + b"0" + b"]" * 8, False)
    emit("negative-integer5000-digits", PREFIX + b"[" + b"9" * 5000 + b"]", False)
    quoted = copy.deepcopy(base)
    quoted[15][25] = 'SELECT false /* [ { ] } " \\" \\\\ [ { */'
    emit("positive-quoted-brackets-escapes", encode(quoted), True)
    body = copy.deepcopy(base)
    body[15][25] = "SELECT\tfalse\n/* body CR follows */\r"
    emit("positive-body-HT-LF-CR", encode(body), True)
    result = dict(
        status="PROPOSED_OFFLINE_CODEC_SPECIMENS_NOT_AUTHORITY",
        synthetic=True,
        prefix_hex=PREFIX.hex(),
        pg_proc_fields=list(PG_FIELDS),
        vectors=vectors,
    )
    (here / "vectors.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        f"{len(vectors)} vectors verified; accepted={sum(v['expected'] == 'ACCEPT_CODEC_ONLY' for v in vectors)}"
    )


if __name__ == "__main__":
    main()
