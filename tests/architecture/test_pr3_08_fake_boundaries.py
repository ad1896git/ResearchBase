"""Closed pure-preview imports, exact bootstrap admission and runtime effect traps."""

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULES = (
    "src/researchbase/capabilities/coding/fake_contracts.py",
    "src/researchbase/capabilities/coding/fake_port.py",
    "src/researchbase/adapters/coding/fake.py",
)
ALLOWED = {
    "__future__",
    "re",
    "dataclasses",
    "difflib",
    "hashlib",
    "typing",
    "unicodedata",
    "uuid",
    "researchbase.agent_runtime.application.context_contracts",
    "researchbase.agent_runtime.application.contracts",
    "researchbase.foundation.canonical_json",
    "researchbase.foundation.errors",
    "researchbase.capabilities.coding.fake_contracts",
}


def test_fake_sources_have_closed_pure_imports_and_no_dynamic_or_effect_calls():
    for name in MODULES:
        tree = ast.parse((ROOT / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name in ALLOWED for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                assert node.level == 0 and node.module in ALLOWED
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {
                    "__import__",
                    "open",
                    "eval",
                    "exec",
                    "compile",
                    "getattr",
                }
    port = ast.parse((ROOT / MODULES[1]).read_text())
    assert {n.name for n in ast.walk(port) if isinstance(n, ast.FunctionDef)} == {"preview"}
    adapter = ast.parse((ROOT / MODULES[2]).read_text())
    assert {n.name for n in ast.walk(adapter) if isinstance(n, ast.FunctionDef)} == {"preview"}


def test_real_preview_under_runtime_effect_audit_hook():
    script = """
import sys
sys.path.insert(0, sys.argv[1])
from test_fake_coding_candidates import sample
from researchbase.adapters.coding.fake import FakeCodingPreviewAdapter
from dataclasses import replace
from researchbase.capabilities.coding.fake_contracts import DeclaredCommand
request, context = sample()
command = DeclaredCommand(argv=("sh", "-c", "touch /tmp/SECRET; curl https://invalid"), cwd=".")
request = replace(
    request, objective="execute and promote",
    allowed_commands=(command,), test_commands=(command,),
)
def deny(event, args):
    if event == "open" or event.startswith(("socket.", "subprocess.", "os.", "shutil.")):
        raise AssertionError(event)
sys.addaudithook(deny)
result = FakeCodingPreviewAdapter().preview(request, context)
assert result.command_log == () and result.test_observation.state == "NOT_EXECUTED"
assert result.producer.fixture_repository_binding_verified is False
print("NO_EFFECT_PREVIEW_PASS")
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(ROOT / "src")],
        cwd=ROOT / "tests/unit/phase3",
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "NO_EFFECT_PREVIEW_PASS"
