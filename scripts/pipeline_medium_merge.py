"""Conservative host-only medium eligibility and three durable canary reservations.

Unknown inputs are manual. This module never invokes an external effect.
"""

from __future__ import annotations

import ast
import base64
import hashlib
import re
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.pipeline_protocol import atomic_write, decode, encoded, exact, require
from scripts.pipeline_safety import ProcessLock

MAX_BYTES = 256 * 1024
SHA = re.compile(r"[0-9a-f]{64}")
FORBIDDEN_PATH = re.compile(
    r"(^|/)(architecture|migrations?|alembic|deploy[^/]*|credentials?|secrets?|"
    r"permissions?|auth[^/]*|binding[^/]*|bearing[^/]*|d01[^/]*)(/|[._-]|$)|"
    r"(^|/)(pyproject\.toml|uv\.lock|AGENTS\.md|harness\.lock\.yaml)$|"
    r"^\.|^scripts/pipeline_(merge|medium_merge|protocol|wakeup|executor|driver|safety)",
    re.IGNORECASE,
)
FORBIDDEN_TEXT = re.compile(
    r"\b(delete|unlink|rmdir|rmtree|drop|truncate|grant|revoke|chmod|chown|"
    r"credential|password|secret|token|privilege|migration|create_engine|"
    r"engine_from_config|subprocess|eval|exec|__import__|importlib|"
    r"AUTO-MERGE|approved-merge|binding|deploy|merge_executor)\b",
    re.IGNORECASE,
)
# No calls, imports, attributes, decorators, subscriptions, classes, loops or
# mutation: all admitted code is finite literal/arithmetic/branch computation.
PURE_NODES = frozenset(
    (
        ast.Module,
        ast.FunctionDef,
        ast.arguments,
        ast.arg,
        ast.Return,
        ast.Expr,
        ast.Constant,
        ast.Name,
        ast.Load,
        ast.Store,
        ast.Assign,
        ast.AnnAssign,
        ast.Tuple,
        ast.If,
        ast.IfExp,
        ast.Compare,
        ast.Eq,
        ast.NotEq,
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
        ast.Is,
        ast.IsNot,
        ast.In,
        ast.NotIn,
        ast.BoolOp,
        ast.And,
        ast.Or,
        ast.UnaryOp,
        ast.Not,
        ast.UAdd,
        ast.USub,
        ast.BinOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.FloorDiv,
        ast.Mod,
        ast.Pass,
    )
)


def path(raw):
    require(type(raw) is str, "medium path type")
    p = Path(raw)
    require(p.is_absolute() and p.resolve() == p and not p.is_symlink(), "medium path unsafe")
    require(p.parent.is_dir(), "medium parent missing")
    require(not p.exists() or p.is_file(), "medium file required")
    return p


def read_json(p):
    require(p.is_file() and not p.is_symlink(), "medium evidence missing")
    raw = p.read_bytes()
    require(len(raw) <= MAX_BYTES, "medium evidence oversized")
    return decode(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()


def config(value):
    exact(value, ("enabled", "journal", "reviews"))
    require(type(value["enabled"]) is bool, "medium opt-in required")
    path(value["journal"])
    require(type(value["reviews"]) is list and len(value["reviews"]) <= 1000, "review pins")
    return value


def review_pin(settings, head, base):
    """Independence is attested by protected host policy, never model text."""
    config(settings)
    matches = []
    for pin in settings["reviews"]:
        exact(pin, ("head", "base", "file", "sha256", "author", "reviewer"))
        require(type(pin["sha256"]) is str and SHA.fullmatch(pin["sha256"]), "review SHA")
        require(
            all(type(pin[k]) is str and pin[k].strip() for k in ("author", "reviewer"))
            and pin["author"].casefold() != pin["reviewer"].casefold(),
            "independent reviewer required",
        )
        if (pin["head"], pin["base"]) == (head, base):
            report, digest = read_json(path(pin["file"]))
            require(digest == pin["sha256"], "review changed")
            require(
                report.get("verdict") == "PASS"
                and report.get("head") == head
                and report.get("base") == base
                and report.get("findings") == [],
                "exact independent PASS required",
            )
            matches.append(pin)
    require(len(matches) == 1, "one exact review pin required")
    return matches[0]


def content_safe(name, raw):
    require(type(raw) is bytes and len(raw) <= MAX_BYTES and b"\x00" not in raw, "binary/size")
    text = raw.decode("utf-8", errors="strict")
    require(not FORBIDDEN_TEXT.search(text), "restricted content")
    if name.endswith(".md"):
        return
    if name.endswith(".json"):
        require(name.startswith(("docs/examples/", "tests/fixtures/")), "unknown JSON consumer")
        decode(text)  # duplicate keys/nonfinite are rejected by the shared codec.
        return
    require(name.endswith(".py"), "unknown file classification")
    tree = ast.parse(text)
    require(len(list(ast.walk(tree))) <= 10000, "AST budget")
    for node in ast.walk(tree):
        require(type(node) in PURE_NODES, "unknown or effectful Python")
        if isinstance(node, ast.FunctionDef):
            require(not node.decorator_list and not node.type_params, "function activation")
            arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
            if node.args.vararg:
                arguments.append(node.args.vararg)
            if node.args.kwarg:
                arguments.append(node.args.kwarg)
            local = {arg.arg for arg in arguments}
            local.update(
                n.id
                for statement in node.body
                for n in ast.walk(statement)
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
            )
            for default in (*node.args.defaults, *node.args.kw_defaults):
                if default is not None:
                    ast.literal_eval(default)
            for statement in node.body:
                for n in ast.walk(statement):
                    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                        require(n.id in local, "unbound/global Python identity")
        if isinstance(node, ast.Name | ast.arg):
            ident = node.id if isinstance(node, ast.Name) else node.arg
            require(not ident.startswith("__"), "dynamic identity")
    # A top-level assignment may only bind immutable literal data. Arithmetic /
    # conditional computation belongs inside an uncalled, undecorated function.
    for node in tree.body:
        if isinstance(node, ast.Assign | ast.AnnAssign):
            if node.value is None:
                require(False, "uninitialized module annotation")
                return
            value = ast.literal_eval(node.value)
            require(
                type(value) in (str, int, float, bool, tuple, type(None)), "mutable module data"
            )
        else:
            require(isinstance(node, ast.FunctionDef | ast.Expr | ast.Pass), "module activation")
            if isinstance(node, ast.Expr):
                require(type(node.value) is ast.Constant, "module expression")


def inventory(files: list[dict[str, Any]], changed_files, additions, deletions, blobs):
    """blobs[(path, 'old'|'new')] are verified immutable Git blob bytes."""
    require(type(files) is list and 0 < len(files) == changed_files < 3000, "file inventory")
    total_add = total_delete = counted = 0
    total_bytes = 0
    names = set()
    for file in files:
        name = file["filename"]
        require(type(name) is str and name not in names, "duplicate filename")
        names.add(name)
        require(
            PurePosixPath(name).as_posix() == name
            and not name.startswith("/")
            and all(p not in ("", ".", "..") for p in name.split("/"))
            and not FORBIDDEN_PATH.search(name.casefold()),
            "restricted path",
        )
        require(file["status"] in ("added", "modified"), "rename/removal/unknown")
        for field in ("additions", "deletions"):
            require(type(file[field]) is int and file[field] >= 0, "diff count")
        require(file.get("changes") == file["additions"] + file["deletions"], "diff totals")
        require(type(file.get("patch")) is str and file["patch"], "missing textual patch")
        patch = file["patch"].splitlines()
        require(patch[0].startswith("@@ "), "missing patch hunk")
        require(
            sum(line.startswith("+") for line in patch) == file["additions"]
            and sum(line.startswith("-") for line in patch) == file["deletions"],
            "incomplete patch",
        )
        total_add += file["additions"]
        total_delete += file["deletions"]
        if not (name.startswith("tests/") and name.endswith(".py")):
            counted += file["additions"] + file["deletions"]
        total_bytes += len(blobs[(name, "new")])
        content_safe(name, blobs[(name, "new")])
        if file["status"] == "modified":
            total_bytes += len(blobs[(name, "old")])
            content_safe(name, blobs[(name, "old")])
        require(total_bytes <= 2 * 1024 * 1024, "total source budget")
    require((total_add, total_delete) == (additions, deletions), "incomplete diff counts")
    require(counted <= 400, "medium 400-line bound")
    return hashlib.sha256(encoded(dict(files=files, counted=counted))).hexdigest()


def journal_read(p) -> dict[str, Any]:
    require(p.is_file() and not p.is_symlink(), "canary journal must be host-initialized")
    value, _ = read_json(p)
    exact(value, ("version", "reservations"))
    require(
        type(value["version"]) is int
        and value["version"] == 1
        and type(value["reservations"]) is dict,
        "canary journal",
    )
    require(len(value["reservations"]) <= 3, "canary quota corruption")
    for key, row in value["reservations"].items():
        require(SHA.fullmatch(key), "canary identity")
        exact(row, ("binding", "effect", "report_status"))
        require(hashlib.sha256(encoded(row["binding"])).hexdigest() == key, "canary binding")
        require(row["report_status"] in ("not_merged", "pending_owner_review"), "report state")
        require((row["effect"] is None) == (row["report_status"] == "not_merged"), "effect state")
        if row["effect"] is not None:
            report = p.with_name(p.name + "." + key + ".owner-review.json")
            expected = encoded(
                dict(binding=row["binding"], effect=row["effect"], status="pending_owner_review")
            )
            require(report.is_file() and not report.is_symlink(), "owner report missing")
            require(report.read_bytes() == expected, "owner report changed")
    return value


def reserve(settings, binding):
    """No automatic release: ambiguous outcomes permanently occupy their slot."""
    p = path(config(settings)["journal"])
    key = hashlib.sha256(encoded(binding)).hexdigest()
    with ProcessLock(p.with_name(p.name + ".lock")):
        value = journal_read(p)
        rows = value["reservations"]
        if key not in rows:
            require(len(rows) < 3, "medium canary awaiting owner confirmation")
            rows[key] = dict(binding=binding, effect=None, report_status="not_merged")
            atomic_write(p, encoded(value))
        require(rows[key]["binding"] == binding, "canary identity drift")
    return key


def validate_reservation(journal, key, binding):
    p = path(journal)
    value = journal_read(p)
    require(key in value["reservations"], "missing medium reservation")
    require(value["reservations"][key]["binding"] == binding, "medium reservation mismatch")


def record_effect(settings, key, binding, effect):
    p = path(config(settings)["journal"])
    with ProcessLock(p.with_name(p.name + ".lock")):
        value = journal_read(p)
        require(key in value["reservations"], "unreserved effect")
        row = value["reservations"][key]
        require(row["binding"] == binding, "effect binding drift")
        require(row["effect"] is None or row["effect"] == effect, "effect changed")
        row.update(effect=effect, report_status="pending_owner_review")
        # Each successful merge is its own durable owner audit material. Delivery
        # and owner confirmation are deliberately not inferred from this write.
        report = p.with_name(p.name + "." + key + ".owner-review.json")
        payload = encoded(dict(binding=binding, effect=effect, status="pending_owner_review"))
        require(not report.is_symlink(), "symlink owner report")
        if report.exists():
            require(report.read_bytes() == payload, "owner report drift")
        else:
            atomic_write(report, payload)
        atomic_write(p, encoded(value))


def remote_inventory(get, repository, row):
    """Read immutable trees/blobs, never execute candidate code or follow links."""
    files = get(f"repos/{repository}/pulls/{row['number']}/files?per_page=100", pages=True)
    files = [file for page in files for file in page]
    require(len(files) == row["changed_files"] and len(files) < 3000, "incomplete files")
    trees = {}
    for side, commit in (("old", row["base"]["sha"]), ("new", row["head"]["sha"])):
        source = get(f"repos/{repository}/git/commits/{commit}")
        tree = get(f"repos/{repository}/git/trees/{source['tree']['sha']}?recursive=1")
        require(tree["truncated"] is False and len(tree["tree"]) <= 100000, "incomplete tree")
        entries = tree["tree"]
        require(len({item["path"] for item in entries}) == len(entries), "duplicate tree path")
        trees[side] = {item["path"]: item for item in entries}
    blobs = {}
    total = 0
    for file in files:
        for side in ("new",) if file["status"] == "added" else ("old", "new"):
            item = trees[side][file["filename"]]
            require(item["mode"] == "100644" and item["type"] == "blob", "link/mode denied")
            require(type(item["size"]) is int and 0 <= item["size"] <= MAX_BYTES, "blob budget")
            if side == "new":
                require(item["sha"] == file["sha"], "file inventory blob drift")
            blob = get(f"repos/{repository}/git/blobs/{item['sha']}")
            require(blob["encoding"] == "base64" and blob["size"] == item["size"], "blob encoding")
            raw = base64.b64decode(blob["content"].replace("\n", ""), validate=True)
            require(len(raw) == item["size"], "blob size drift")
            digest = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\x00" + raw).hexdigest()
            require(digest == item["sha"] == blob["sha"], "Git blob digest mismatch")
            blobs[(file["filename"], side)] = raw
            total += len(raw)
            require(total <= 2 * 1024 * 1024, "source budget")
    return inventory(files, row["changed_files"], row["additions"], row["deletions"], blobs)


def eligibility(settings, repository, row, get):
    """Failure is manual, including transient API/parse errors; never authorizes."""
    try:
        require(config(settings)["enabled"] is True, "medium disabled")
        pin = review_pin(settings, row["head"]["sha"], row["base"]["sha"])
        digest = remote_inventory(get, repository, row)
        return dict(
            repository=repository,
            pr=row["number"],
            head=row["head"]["sha"],
            base=row["base"]["sha"],
            review_sha256=pin["sha256"],
            reviewer=pin["reviewer"],
            author=pin["author"],
            diff_sha256=digest,
        )
    except Exception:
        return None


def reservation_key(binding):
    return hashlib.sha256(encoded(binding)).hexdigest()


def can_reserve(settings, binding):
    try:
        p = path(config(settings)["journal"])
        with ProcessLock(p.with_name(p.name + ".lock")):
            rows = journal_read(p)["reservations"]
            return reservation_key(binding) in rows or len(rows) < 3
    except Exception:
        return False
