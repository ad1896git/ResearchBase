"""Offline standard-JSON approval specimens only; never a binding/approval issuer."""

import datetime as dt
import hashlib
import json
import re
import unicodedata
from pathlib import Path

SCHEMA = {
    "kind": "text",
    "schema_version": "int",
    "approval_id": "text",
    "sequence": "int",
    "previous_approval_sha256": "previous",
    "approved_at": "text",
    "expires_at": "text",
    "confirmation": {"event": "text", "decision_sha256": "hash", "diff_sha256": "hash"},
    "deployment": {
        "id": "text",
        "host": "text",
        "uid": "u64",
        "namespace": "text",
        "root_id": "text",
        "installation_manifest_sha256": "hash",
        "artifact_sha256": "hash",
        "callable_module": "text",
        "callable_qualname": "text",
        "callable_code_sha256": "hash",
    },
    "database": {
        "system_identifier": "text",
        "name": "text",
        "oid": "oid",
        "owner_oid": "oid",
        "pg_major": "int",
    },
    "alembic_revision": "text",
    "roles": {
        "session": {"name": "text", "oid": "oid"},
        "current": {"name": "text", "oid": "oid"},
        "policy": "text",
    },
    "helper": {
        "name": "text",
        "oid": "oid",
        "definition_sha256": "hash",
        "owner_oid": "oid",
        "signature": {
            "argument_type_oids": [],
            "variadic_type_oid": "u32",
            "return_type_oid": "oid",
            "returns_set": "bool",
        },
        "security": {
            "kind": "text",
            "language": "text",
            "volatility": "text",
            "security_definer": "bool",
            "leakproof": "bool",
            "strict": "bool",
            "parallel": "text",
            "support_oid": "u32",
            "configuration": ["text"],
        },
        "effective_acl": [
            {
                "grantee_oid": "u32",
                "grantor_oid": "oid",
                "privilege": "text",
                "is_grantable": "bool",
            }
        ],
    },
    "connection": {"transport": "text", "socket_directory": "text", "port": "int"},
    "cas": {
        "path": "text",
        "namespace": "text",
        "device": "u64",
        "inode": "u64",
        "uid": "u64",
        "mode": "int",
    },
    "lease": {"path": "text", "device": "u64", "inode": "u64", "uid": "u64", "mode": "int"},
}


def need(ok, why):
    if not ok:
        raise ValueError(why)


def pairs(items):
    result = {}
    for key, value in items:
        need(key not in result, "DUPLICATE_KEY")
        result[key] = value
    return result


def reject(_):
    raise ValueError("NONINTEGER_OR_NONFINITE")


def integer(token):
    need(len(token.lstrip("-")) <= 20, "INTEGER_BOUND")
    return int(token)


def shape(value, schema):
    if type(schema) is dict:
        need(type(value) is dict and set(value) == set(schema), "CLOSED_FIELDS")
        for key, item in schema.items():
            shape(value[key], item)
    elif type(schema) is list:
        need(type(value) is list and len(value) <= 64, "ARRAY_BOUND")
        if not schema:
            need(not value, "EMPTY_ARGUMENTS")
        else:
            for item in value:
                shape(item, schema[0])
    elif schema == "previous":
        if value is not None:
            shape(value, "hash")
    elif schema == "bool":
        need(type(value) is bool, "BOOL")
    elif schema in {"int", "u64", "u32", "oid"}:
        need(type(value) is int, "INTEGER_TYPE")
        maximum = 2**32 - 1 if schema in {"oid", "u32"} else 2**64 - 1
        need((1 if schema == "oid" else 0) <= value <= maximum, "INTEGER_RANGE")
    else:
        need(type(value) is str and 0 < len(value.encode("utf-8")) <= 4096, "UTF8_TEXT")
        need(not any(unicodedata.category(c) in {"Cc", "Cs"} for c in value), "TEXT_CONTROL")
        if schema == "hash":
            need(re.fullmatch(r"[0-9a-f]{64}", value) is not None, "SHA256")


def depth_bound(text):
    quoted = escaped = False
    depth = 0
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "{[":
            depth += 1
            need(depth <= 8, "DEPTH_BOUND")
        elif char in "}]":
            depth -= 1
    # json.loads owns all syntax validation, not this resource-only scan.


def utc(value):
    need("T" in value and value.endswith(("Z", "+00:00")), "UTC")
    result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    need(result.utcoffset() == dt.timedelta(0), "UTC")
    return result


def decode(raw):
    try:
        need(type(raw) is bytes and len(raw) <= 32768, "RECORD_BOUND")
        text = raw.decode("utf-8", errors="strict")
        need(not text.startswith("\ufeff"), "BOM")
        depth_bound(text)
        value = json.loads(
            text,
            object_pairs_hook=pairs,
            parse_constant=reject,
            parse_float=reject,
            parse_int=integer,
        )
        shape(value, SCHEMA)
        need(
            value["kind"] == "ResearchBase.D01.BindingApproval" and value["schema_version"] == 4,
            "VERSION",
        )
        need(1 <= value["sequence"] <= 2147483647, "SEQUENCE")
        initial = value["sequence"] == 1
        need((value["previous_approval_sha256"] is None) == initial, "APPEND_CHAIN")
        event = value["confirmation"]["event"]
        need(
            event == "INITIAL"
            if initial
            else event in {"PG_UPGRADE", "MIGRATION", "ROLE_CHANGE", "DEPLOYMENT_CHANGE"},
            "EVENT",
        )
        need(utc(value["approved_at"]) < utc(value["expires_at"]), "EXPIRY_ORDER")
        d = value["database"]
        need(
            d["pg_major"] == 18
            and re.fullmatch(r"[1-9][0-9]{0,19}", d["system_identifier"]) is not None,
            "PG18_IDENTITY",
        )
        need(int(d["system_identifier"]) < 2**64, "SYSTEM_ID")
        for name in (
            d["name"],
            value["roles"]["session"]["name"],
            value["roles"]["current"]["name"],
        ):
            need(len(name.encode()) <= 63, "NAME_BOUND")
        for name in (
            value["approval_id"],
            value["alembic_revision"],
            value["deployment"]["id"],
            value["deployment"]["namespace"],
            value["deployment"]["root_id"],
        ):
            need(len(name.encode()) <= 128, "IDENTITY_BOUND")
        need(
            value["alembic_revision"].lower()
            not in {"latest", "current", "main", "master", "head"},
            "REVISION_ALIAS",
        )
        need(value["roles"]["policy"] == "restricted-writer-v4", "ROLE_POLICY")
        helper = value["helper"]
        need(helper["name"] == "public.pr316d1_enabled()", "HELPER_NAME")
        need(
            helper["signature"]
            == {
                "argument_type_oids": [],
                "variadic_type_oid": 0,
                "return_type_oid": 16,
                "returns_set": False,
            },
            "HELPER_SIGNATURE",
        )
        need(
            helper["security"]
            == {
                "kind": "f",
                "language": "sql",
                "volatility": "s",
                "security_definer": False,
                "leakproof": False,
                "strict": False,
                "parallel": "u",
                "support_oid": 0,
                "configuration": ["search_path=pg_catalog, public, pg_temp"],
            },
            "HELPER_SECURITY",
        )
        rows = helper["effective_acl"]
        keys = []
        for row in rows:
            need(row["privilege"] == "EXECUTE", "ACL_PRIVILEGE")
            need(row["grantee_oid"] != 0 or not row["is_grantable"], "PUBLIC_GRANTABLE")
            keys.append(
                (row["grantee_oid"], row["grantor_oid"], row["privilege"], row["is_grantable"])
            )
        need(keys == sorted(set(keys)), "ACL_NORMALIZED")
        need(any(row["grantee_oid"] == 0 for row in rows), "ACL_PUBLIC")
        need(any(row["grantee_oid"] == helper["owner_oid"] for row in rows), "ACL_OWNER")
        connection = value["connection"]
        need(connection["transport"] == "UNIX" and 1 <= connection["port"] <= 65535, "UNIX_ONLY")
        deployment = value["deployment"]
        need(
            deployment["callable_module"] == "researchbase.agent_runtime.domain.bearing_evaluation"
            and deployment["callable_qualname"] == "evaluate",
            "CALLABLE",
        )
        need(value["cas"]["namespace"] == deployment["namespace"], "NAMESPACE")
        for key, mode in (("cas", 448), ("lease", 384)):
            need(
                value[key]["mode"] == mode and value[key]["uid"] == deployment["uid"],
                "LOCAL_BINDING",
            )
        for path in (connection["socket_directory"], value["cas"]["path"], value["lease"]["path"]):
            need(path.startswith("/") and "//" not in path and not path.endswith("/"), "LOCAL_PATH")
            need(all(part not in {".", ".."} for part in path.split("/")), "LOCAL_PATH")
        return value
    except (UnicodeError, RecursionError, OverflowError) as exc:
        raise ValueError("BOUNDED_JSON_DENIED") from exc


def canonical(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def main():
    root = Path(__file__).resolve().parent
    data = json.loads((root / "vectors.json").read_text())
    for row in data["vectors"]:
        raw = bytes.fromhex(row["input_hex"])
        try:
            value = decode(raw)
        except ValueError:
            need(row["expected"] == "REJECT_CODEC", row["id"])
        else:
            need(row["expected"] == "ACCEPT_CODEC_ONLY", row["id"])
            need(hashlib.sha256(canonical(value)).hexdigest() == row["canonical_sha256"], row["id"])
    print(
        json.dumps(
            {
                "result": "OFFLINE_JSON_SPECIMENS_CONSISTENT_ONLY",
                "vectors": len(data["vectors"]),
                "PG": "NOT_RUN",
                "approval_or_binding_issued": False,
                "freeze": "NOT_A_GATE",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
