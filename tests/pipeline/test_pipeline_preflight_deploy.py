"""Same-byte historical deploy payload, full real plist schema, isolated only."""

from __future__ import annotations

import json
import plistlib
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from scripts import pipeline_preflight as t
from scripts.pipeline_wakeup import render_plist
from tests.pipeline.test_pipeline_preflight import MAC, fixture, invoke, save

# Preserved test payload only. Never imports/runs the failed OUT operator in parent.
DEPLOYMENT_PAYLOAD = "\"\"\"One bounded timer runtime upgrade. No old loop restart, no force kill or ledger reset.\"\"\"\nfrom pathlib import Path\nimport datetime,hashlib,json,os,plistlib,re,shlex,subprocess,sys,tarfile,time\nOUT=Path(__file__).resolve().parent;sys.path.insert(0,str(OUT))\nfrom manifest import bindings,validate,sha\nfrom snapshot_inventory import archive as archive_inventory\nB,ROOT,RUNTIME,PLIST=bindings(OUT/'bindings.json');PYTHON=RUNTIME/'.venv/bin/python3'\nassert sys.executable==str(PYTHON) and (3,12)<=sys.version_info[:2]<(3,13),'exact project venv Python required'\nsys.path.insert(0,str(RUNTIME))\nfrom scripts.pipeline_protocol import atomic_write,encoded\nfrom scripts.pipeline_safety import ProcessLock\nM=json.loads((OUT/'deployment-manifest.json').read_text());validate(M,ROOT,RUNTIME,OUT,PLIST,create=True)\nDOMAIN=f'gui/{os.getuid()}';LABEL='com.researchbase.pipeline-wakeup';SERVICE=DOMAIN+'/'+LABEL;LEGACY=('com.researchbase.autopilot','com.researchbase.watchdog')\nSTAMP=B['stamp'];HEAD=B['head'];CFG=ROOT/'.pipeline/control'/STAMP;SNAP=ROOT/'.pipeline/snapshots'/STAMP\nPOINTERS=[ROOT/'.pipeline/control/CURRENT_TIMER_DEPLOYMENT.json',ROOT/'.pipeline/control/CURRENT_AUTHORIZED_QUEUE.json'];original_pointers={p:p.read_bytes() for p in POINTERS}\nPREVIOUS=json.loads(original_pointers[POINTERS[0]]);OLD_CFG=Path(PREVIOUS['config_dir']);OLD=json.loads((OLD_CFG/'config.json').read_text())\nFILES=['.pipeline/state.json','.pipeline/queue.json','.pipeline/bin/autopilot.py','.pipeline/bin/run_forever.sh','.pipeline/bin/watchdog.sh']\n\ndef record(name,**data):\n    v=dict(at=datetime.datetime.now(datetime.UTC).isoformat(),**data);(OUT/(name+'.json')).write_bytes(encoded(v));print(json.dumps(dict(step=name,**v)),flush=True)\n\ndef run(argv,codes=(0,),timeout=45):\n    if B['mode']=='rehearsal' and argv[0]=='launchctl':assert getattr(subprocess.run,'_rb_rehearsal_transport',False),'real launchctl denied in rehearsal'\n    p=subprocess.run(argv,capture_output=True,text=True,timeout=timeout)\n    with (OUT/'commands.jsonl').open('a') as f:f.write(json.dumps(dict(argv=argv,rc=p.returncode,stdout=p.stdout,stderr=p.stderr))+'\\n')\n    assert p.returncode in codes,(argv,p.returncode,p.stderr)\n    return p.stdout\n\ndef legacy_hashes():return {p:sha(ROOT/p) for p in FILES}|{name:sha(PLIST.parent/(name+'.plist')) for name in LEGACY}\n\ndef legacy_ok():\n    flags=run(['launchctl','print-disabled',DOMAIN])\n    for label in LEGACY:\n        assert f'\"{label}\" => disabled' in flags\n        run(['launchctl','print',DOMAIN+'/'+label],codes=(113,))\n    assert legacy_hashes()==legacy_before,'legacy drift'\n\nchanged=False;booted_out=False;new_active=False;old_lock=None;before_plist=PLIST.read_bytes();legacy_before=legacy_hashes()\ntry:\n    assert not CFG.exists() and not SNAP.exists()\n    if B['mode']=='live':\n        pre=json.loads((OUT/'preflight-acceptance.json').read_text());assert pre['success'] and pre['interpreter']==str(PYTHON) and pre['deployment_sha256']==sha(Path(__file__)) and pre['manifest_sha256']==sha(OUT/'deployment-manifest.json')\n        rev=json.loads((OUT/'deployment-review.json').read_text());assert rev['verdict']=='PASS' and rev['deployment_sha256']==sha(Path(__file__)) and rev['manifest_sha256']==sha(OUT/'deployment-manifest.json')\n        merged=json.loads(run(['gh','api','repos/ad1896git/ResearchBase/pulls/54']));assert merged['merged'] and merged['merge_commit_sha']==HEAD\n        assert json.loads(run(['gh','api','repos/ad1896git/ResearchBase/git/ref/heads/main']))['object']['sha']==HEAD\n    assert run(['git','-C',str(RUNTIME),'rev-parse','HEAD']).strip()==HEAD\n    assert not run(['git','-C',str(RUNTIME),'status','--porcelain']).strip()\n    assert run(['/opt/homebrew/bin/codex','--version']).strip()=='codex-cli 0.164.0'\n    legacy_ok();loaded=run(['launchctl','print',SERVICE]);assert str(OLD_CFG/'config.json') in loaded\n    processes=run(['ps','-axo','pid=,ppid=,pgid=,lstart=,command=']);(OUT/'processes-before.txt').write_text(processes)\n    for line in processes.splitlines():\n        try:parts=shlex.split(line)\n        except ValueError:continue\n        if '-c' in parts or '-lc' in parts:continue\n        assert not any(str(ROOT/p) in parts for p in FILES[2:]),'legacy executor still running'\n    # Disable new starts, drain current owner naturally, never signal executing workers.\n    run(['launchctl','disable',SERVICE]);changed=True\n    old_lock=ProcessLock(Path(OLD['root'])/'wakeup.lock');deadline=time.monotonic()+1800\n    while not old_lock.acquire():\n        assert time.monotonic()<deadline,'old timer did not drain in30min'\n        record('drain-heartbeat',phase='waiting_natural_owner_exit');time.sleep(5)\n    while re.search(r'^\\s*pid = \\d+',run(['launchctl','print',SERVICE]),re.M):\n        assert time.monotonic()<deadline,'old launcher did not exit';record('drain-heartbeat',phase='waiting_natural_launcher_exit');time.sleep(1)\n    validate(M,ROOT,RUNTIME,OUT,PLIST)\n    dispositions=[];oldqueue=json.loads(Path(OLD['queue']).read_text())\n    for entry in oldqueue['entries']:\n        state=json.loads((Path(entry['control'])/'state.json').read_text())\n        assert all(t['status'] in ('done','blocked','failed','awaiting_merge','budget_exhausted') for t in state['tasks'].values()),'in-flight old task'\n        dispositions.append(dict(id=entry['id'],statuses={n:t['status'] for n,t in state['tasks'].items()},history_retained=True))\n    run(['launchctl','bootout',DOMAIN,str(PLIST)]);booted_out=True\n    run(['launchctl','print',SERVICE],codes=(113,));legacy_ok()\n    SNAP.mkdir(mode=0o700)\n    (SNAP/'installed-before.plist').write_bytes(before_plist)\n    for p,raw in original_pointers.items():(SNAP/p.name).write_bytes(raw)\n    (SNAP/'registry-dispositions.json').write_bytes(encoded(dispositions));(SNAP/'legacy-sha256.json').write_bytes(encoded(legacy_before))\n    archive=SNAP/'engineering-control.tar'\n    with tarfile.open(archive,'x') as tar:\n        archive_inventory(ROOT,M['snapshot_inventory'],tar)\n    with archive.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()\n    (SNAP/'archive.sha256').write_text(digest+'  engineering-control.tar\\n')\n    with tarfile.open(archive) as tar:assert all(name in tar.getnames() for name in FILES)\n    record('snapshot',success=True,path=str(archive),sha256=digest)\n    CFG.mkdir(mode=0o700)\n    state=CFG/'state';state.mkdir(mode=0o700)\n    atomic_write(CFG/'queue.json',encoded(oldqueue))\n    policyroot=CFG/'throughput';worktrees=ROOT/'.pipeline/work'/STAMP;policyroot.mkdir(mode=0o700)\n    index=CFG/'index-initial.json';atomic_write(index,encoded(dict(version=1,contracts={},completed={},templates={},publications={})))\n    config={**OLD,'root':str(state),'queue':str(CFG/'queue.json'),'runtime':str(RUNTIME),'python':str(PYTHON),'source_head':HEAD,'version':2}\n    config['throughput']=dict(version=1,root=str(policyroot),worktrees=str(worktrees),source_checkout=str(RUNTIME),repository='ad1896git/ResearchBase',base_ref='main',authorization=dict(path=OLD['merge_policy']['authorization_file'],sha256=OLD['merge_policy']['authorization_sha256']),index=dict(path=str(index),sha256=sha(index)),implementation_slots=2,review_slots=1,pg_slots=1,pg_environment={})\n    # Existing merge identities, OFF switch, label policy, auth SHA and targets are unchanged.\n    assert config['merge_policy']==OLD['merge_policy']\n    atomic_write(CFG/'config.json',encoded(config));atomic_write(CFG/'history.json',encoded(dict(previous=PREVIOUS,dispositions=dispositions,merge_policy_unchanged=True,pg_profile='held until exact reviewed profile supplied')))\n    rendered=OUT/'rendered.plist';env=dict(os.environ,PYTHONPATH=str(RUNTIME))\n    result=subprocess.run([str(PYTHON),'-m','scripts.pipeline_wakeup','--config',str(CFG/'config.json'),'--render-plist',str(rendered)],cwd=RUNTIME,env=env,capture_output=True,text=True,timeout=30);assert result.returncode==0,result.stderr\n    run(['plutil','-lint',str(rendered)]);p=plistlib.loads(rendered.read_bytes());assert p['StartInterval']==300 and p['RunAtLoad'] and 'KeepAlive' not in p and p['ProgramArguments'][0]==str(PYTHON)\n    atomic_write(PLIST,rendered.read_bytes());PLIST.chmod(0o644);start=time.monotonic()\n    with ProcessLock(state/'wakeup.lock'):\n        run(['launchctl','enable',SERVICE]);run(['launchctl','bootstrap',DOMAIN,str(PLIST)]);new_active=True\n        log=state/'launchd.stdout.log';limit=time.monotonic()+40\n        while not log.exists() or not log.read_text().strip():\n            assert time.monotonic()<limit,'RunAtLoad absent';time.sleep(1)\n        assert [json.loads(s) for s in log.read_text().splitlines()]==[dict(status='busy')]\n        assert not (policyroot/'admitted-packets.json').exists()\n    record('lock-validation',success=True,actual_launchd_busy=True)\n    while True:\n        rows=[json.loads(s) for s in log.read_text().splitlines()]\n        if len(rows)>1:\n            result=rows[1];assert result['status']=='checked' and time.monotonic()-start>=250\n            assert not result['backlog'] and set(result['entries'])=={e['id'] for e in oldqueue['entries']}\n            assert all(s in ('done','held') for s in result['entries'].values()),'unexpected old generation advancement'\n            break\n        assert time.monotonic()<start+390,'scheduled start missing';record('heartbeat',phase='waiting_real_interval',elapsed=time.monotonic()-start);time.sleep(10)\n    loaded=run(['launchctl','print',SERVICE]);assert str(CFG/'config.json') in loaded;assert re.search(r'runs = [2-9][0-9]*',loaded) and 'last exit code = 0' in loaded\n    stderr=(state/'launchd.stderr.log').read_text()\n    # Missing contracts/owner gates are expected visible holds, not dispatch failures.\n    if stderr.strip():\n        notes=[json.loads(s) for s in stderr.splitlines()];assert all(v.get('status')=='held' for v in notes),notes\n    assert not (policyroot/'quarantine.json').exists();legacy_ok()\n    current=dict(stamp=STAMP,runtime=str(RUNTIME),snapshot=str(SNAP),evidence=str(OUT),config_dir=str(CFG),head=HEAD,merged_baseline=HEAD,previous=PREVIOUS,all_low_risk_enabled=PREVIOUS['all_low_risk_enabled'],medium_high_label_required=True,merge_effects_enabled=PREVIOUS['merge_effects_enabled'],throughput_enabled=True,rollout_validation='pending_real_CI_wait_concurrent_worker',rollback='Run exact pinned Python rollback.py; natural drain; prior timer only; preserve all ledgers and merge effects; legacy stays disabled.')\n    atomic_write(POINTERS[0],encoded(current));p=json.loads(original_pointers[POINTERS[1]]);p['timer_registry']=str(CFG/'queue.json');atomic_write(POINTERS[1],encoded(p))\n    record('acceptance',success=True,scheduled_start=True,elapsed=time.monotonic()-start,head=HEAD,config=str(CFG/'config.json'),snapshot=str(SNAP),full_rollout_validation='PENDING')\nexcept Exception as error:\n    record('failure',error=f'{type(error).__name__}: {error}',changed=changed,new_active=new_active)\n    try:\n        if changed:\n            if not booted_out:\n                run(['launchctl','enable',SERVICE]);assert str(OLD_CFG/'config.json') in run(['launchctl','print',SERVICE])\n            else:\n                run(['launchctl','disable',SERVICE])\n                if new_active:\n                    assert not re.search(r'^\\s*pid = \\d+',run(['launchctl','print',SERVICE]),re.M),'new owner active; preserve evidence; no forced stop'\n                    run(['launchctl','bootout',DOMAIN,str(PLIST)],codes=(0,113))\n                atomic_write(PLIST,before_plist);PLIST.chmod(0o644)\n                for p,raw in original_pointers.items():atomic_write(p,raw)\n                run(['launchctl','enable',SERVICE]);run(['launchctl','bootstrap',DOMAIN,str(PLIST)])\n            assert PLIST.read_bytes()==before_plist and all(p.read_bytes()==raw for p,raw in original_pointers.items())\n        legacy_ok();record('rollback',success=True,prior_timer_restored=changed,legacy_disabled=True,evidence_retained=True)\n    except Exception as rb:record('rollback',success=False,error=str(rb))\n    raise SystemExit(2)\nfinally:\n    if old_lock is not None:old_lock.close()\n"  # noqa: E501


def deployment_fixture(tmp_path) -> tuple[Path, Path, dict[str, Any]]:
    r, o, m = fixture(tmp_path)
    runtime = Path(__file__).resolve().parents[2]
    # Fixture approves canonical host directories explicitly; product keeps its
    # canonical-path rejection (Linux /bin may be a symlink to /usr/bin).
    executable_dirs = list(
        dict.fromkeys(str(Path(path).resolve()) for path in ("/usr/bin", "/bin"))
    )
    prior = o / "prior-runtime"
    (prior / ".venv/bin").mkdir(parents=True)
    (prior / ".venv/bin/python3").symlink_to(sys.executable)
    old = o / ".pipeline/control/old"
    (old / "state").mkdir(parents=True)
    (o / "LaunchAgents").mkdir()
    (o / "codex-home").mkdir()
    for name in (
        ".pipeline/state.json",
        ".pipeline/queue.json",
        ".pipeline/bin/autopilot.py",
        ".pipeline/bin/run_forever.sh",
        ".pipeline/bin/watchdog.sh",
    ):
        p = o / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}")
    (old / "queue.json").write_text(json.dumps(dict(version=1, entries=[])))
    cfg = dict(
        version=2,
        root=str(old / "state"),
        queue=str(old / "queue.json"),
        runtime=str(prior),
        python=str(prior / ".venv/bin/python3"),
        source_head="a" * 40,
        approvers=["fixture-owner"],
        codex_home=str(o / "codex-home"),
        executable_dirs=executable_dirs,
        merge_policy=dict(
            enabled=False,
            authorization_file=str(o / ".pipeline/control/auth.json"),
            authorization_sha256="f" * 64,
            stop_file=str(o / ".pipeline/control/AUTO-MERGE.OFF"),
            merge_log=str(o / ".pipeline/control/MERGE-LOG.md"),
        ),
    )
    (old / "config.json").write_text(json.dumps(cfg))
    pointer = dict(
        head="a" * 40,
        runtime=str(prior),
        config_dir=str(old),
        all_low_risk_enabled=True,
        merge_effects_enabled=True,
    )
    (o / ".pipeline/control/CURRENT_TIMER_DEPLOYMENT.json").write_text(json.dumps(pointer))
    (o / ".pipeline/control/CURRENT_AUTHORIZED_QUEUE.json").write_text(
        json.dumps(dict(timer_registry=str(old / "queue.json")))
    )
    oldplist = o / "LaunchAgents/com.researchbase.pipeline-wakeup.plist"
    oldplist.write_bytes(render_plist(cfg, old / "config.json"))
    for name in ("autopilot", "watchdog"):
        (o / "LaunchAgents" / ("com.researchbase." + name + ".plist")).write_bytes(
            plistlib.dumps(dict(Label="com.researchbase." + name))
        )
    writable = r / "payload/attempt-0"
    base = writable / "fixture"
    stamp = "testtarget"

    def mapped(v: Any) -> Any:
        if type(v) is str and v.startswith(str(o)) and not v.startswith(str(prior)):
            return str(base / Path(v).relative_to(o))
        if type(v) is list:
            return [mapped(x) for x in v]
        if type(v) is dict:
            return {k: mapped(x) for k, x in v.items()}
        return v

    oldvalue = plistlib.loads(oldplist.read_bytes())
    mappedold = mapped(oldvalue)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=runtime, text=True).strip()
    newcfg = {
        **mapped(cfg),
        "runtime": str(runtime),
        "python": sys.executable,
        "source_head": head,
        "root": str(base / ".pipeline/control" / stamp / "state"),
        "queue": str(base / ".pipeline/control" / stamp / "queue.json"),
    }
    newvalue = plistlib.loads(
        render_plist(newcfg, base / ".pipeline/control" / stamp / "config.json")
    )
    for row, value, original in zip(
        m["plists"], (mappedold, newvalue), (oldvalue, newvalue), strict=True
    ):
        Path(row["path"]).write_bytes(plistlib.dumps(value))
        Path(row["original_path"]).write_bytes(plistlib.dumps(original))
        row.update(
            sha256=t.sha(Path(row["path"])), original_sha256=t.sha(Path(row["original_path"]))
        )
        mapping = {}

        def pairs(a, b, mapping=mapping):
            if type(a) is str and a != b:
                mapping[a] = b
            elif type(a) is list:
                for x, y in zip(a, b, strict=True):
                    pairs(x, y)
            elif type(a) is dict:
                for k in a:
                    pairs(a[k], b[k])

        pairs(original, value)
        row["path_mapping"] = mapping
    Path(m["script"]).write_text(DEPLOYMENT_PAYLOAD)
    m["script_sha256"] = t.sha(Path(m["script"]))
    m["interpreter_inputs"].append(
        {
            **m["interpreter_inputs"][0],
            "role": "prior",
            "executable": str(prior / ".venv/bin/python3"),
        }
    )
    (prior / ".venv/pyvenv.cfg").write_text(
        "home = " + str(Path(sys.base_prefix).resolve() / "bin") + "\n"
    )
    m["interpreter_inputs"][1]["path_aliases"] = sorted(
        set(
            t.interpreter_aliases(prior / ".venv/bin/python3")
            + t.interpreter_aliases(Path(sys.base_prefix).resolve() / "bin")
        )
    )

    m["deployment"] = dict(
        version=1,
        head=head,
        required_feature54="7540438a4d4c1e58af8872dc8c6c18cb07fdb2f2",
        stamp=stamp,
        runtime=str(runtime),
        prior_runtime=str(prior),
        mappings=[
            dict(source=str(o / ".pipeline"), destination=".pipeline"),
            dict(source=str(o / "LaunchAgents"), destination="LaunchAgents"),
            dict(source=str(o / "codex-home"), destination="codex-home"),
        ],
        path_aliases={},
        rewrite_json=[
            ".pipeline/control/CURRENT_TIMER_DEPLOYMENT.json",
            ".pipeline/control/CURRENT_AUTHORIZED_QUEUE.json",
            ".pipeline/control/old/config.json",
            ".pipeline/control/old/queue.json",
        ],
        prior_plist="LaunchAgents/com.researchbase.pipeline-wakeup.plist",
        executable_dirs=executable_dirs,
        codex_version="codex-cli 0.164.0",
    )
    save(r, m)
    return r, o, m


def test_actual_plist_schema_and_typed_deployment_plan(tmp_path):
    r, o, m = deployment_fixture(tmp_path)
    manifest, _, _, proof = t.plan(r)
    assert (
        manifest["deployment"]["required_feature54"] == "7540438a4d4c1e58af8872dc8c6c18cb07fdb2f2"
    )
    v = plistlib.loads(Path(m["plists"][0]["path"]).read_bytes())
    assert (
        v["StartInterval"] == 300
        and v["RunAtLoad"]
        and set(v["EnvironmentVariables"]) == {"PATH", "CODEX_HOME", "PYTHONPATH"}
    )
    assert (
        proof["old"]["path_mapping"]
        and t.inventory([o])[str(o / "prior-runtime/.venv/bin/python3")]["kind"] == "symlink"
    )


def test_deployment_executable_directory_symlink_still_denied(tmp_path):
    r, o, m = deployment_fixture(tmp_path)
    directories = m["deployment"]["executable_dirs"]
    assert len(directories) == len(set(directories))
    assert all(str(Path(path).resolve()) == path for path in directories)
    alias = o / "unapproved-executable-alias"
    alias.symlink_to(directories[0], target_is_directory=True)
    m["deployment"]["executable_dirs"] = [str(alias)]
    save(r, m)
    with pytest.raises(t.SafetyError, match="noncanonical/symlink"):
        t.plan(r)


@MAC
def test_fixed_cli_full_deployment_and_rollback_same_bytes(tmp_path):
    r, o, m = deployment_fixture(tmp_path)
    before = t.inventory([o])
    rc = invoke(r)
    if rc:
        result = r / "evidence/attempt-0/result.json"
        pytest.fail(result.read_text() if result.exists() else "no confined result")
    assert t.inventory([o]) == before
    result = json.loads((r / "evidence/attempt-0/result.json").read_text())
    assert result["adapter"] == "deployment"
    for phase in ("normal", "rollback"):
        a = json.loads((r / "payload/attempt-0" / phase / "adapter-result.json").read_text())
        assert (
            a["same_payload_bytes"]
            and a["payload_sha256"] == m["script_sha256"]
            and a["launchctl"] == "SIMULATED_ONLY"
        )
        assert any(v[1] == "bootstrap" for v in a["calls"] if v[0] == "launchctl")
    assert result["status"] == "pass" and result["live_unchanged"]
    context = t.VerificationContext(
        root=str(r),
        attempt=0,
        result_sha256=t.sha(r / "evidence/attempt-0/result.json"),
        manifest_sha256=t.sha(r / "manifest.json"),
        payload_sha256=m["script_sha256"],
        release_head=m["deployment"]["head"],
        python=sys.executable,
        expected_bindings=(("bindings.json", t.sha(r / "bindings.json")),),
    )
    verified = t.verify_result(context)
    assert verified["status"] == "verified" and verified["current_online_state"] == "NOT_RESCANNED"
    argv = [
        sys.executable,
        "-B",
        "-m",
        "scripts.pipeline_preflight",
        "verify",
        "--root",
        str(r),
        "--attempt",
        "0",
        "--result-sha256",
        context.result_sha256,
        "--manifest-sha256",
        context.manifest_sha256,
        "--payload-sha256",
        context.payload_sha256,
        "--release-head",
        context.release_head,
        "--python",
        sys.executable,
    ]
    v = subprocess.run(
        argv, capture_output=True, text=True, cwd=Path(__file__).resolve().parents[2]
    )
    assert v.returncode == 0, v.stdout + v.stderr
    assert t.inventory([o]) == before


@pytest.mark.parametrize("mutation", ["head", "feature", "runtime", "mapping", "plist_env"])
def test_bad_deployment_model_refuses_before_first_payload_write(tmp_path, mutation):
    r, o, m = deployment_fixture(tmp_path)
    if mutation == "head":
        m["deployment"]["head"] = "unknown"
    elif mutation == "feature":
        m["deployment"]["required_feature54"] = "a" * 40
    elif mutation == "runtime":
        m["deployment"]["runtime"] = str(o)
    elif mutation == "mapping":
        m["deployment"]["mappings"][0]["destination"] = "../escape"
    else:
        row = m["plists"][0]
        p = Path(row["path"])
        v = plistlib.loads(p.read_bytes())
        v["EnvironmentVariables"]["CODEX_HOME"] = str(o)
        p.write_bytes(plistlib.dumps(v))
        row["sha256"] = t.sha(p)
    save(r, m)
    before = t.inventory([o])
    assert invoke(r) != 0
    assert t.inventory([o]) == before and not (r / "payload").exists()


CAPTURE_ENTRY = "\"\"\"Readonly capture inside the merged fixed tool OS-confined Root only; no lease.\"\"\"\nfrom pathlib import Path\nimport json,sys\nOUT=Path(__file__).resolve().parent\nsys.path.insert(0,str(OUT))\nimport manifest as M\n\ndef main():\n    B,ROOT,RUNTIME,PLIST=M.bindings(OUT/'bindings.json')\n    M.review_roles(B,OUT) # pending roles reject before control or lock access\n    writable=Path(B['preflight_root'])\n    assert writable.is_absolute() and writable.resolve()==writable and OUT.is_relative_to(writable),'Root-derived output required'\n    assert not ROOT.is_relative_to(writable) and not writable.is_relative_to(ROOT),'online/write Root overlap'\n    assert sys.executable==str(RUNTIME/'.venv/bin/python3'),'fixed interpreter required'\n    sys.path.insert(0,str(RUNTIME))\n    from scripts.pipeline_preflight import confined\n    confined(writable) # fixed tool kernel proof BEFORE first control read/output\n    dest=OUT/'deployment-manifest.json'\n    assert not dest.exists() and not dest.is_symlink(),'prior capture preserved'\n    manifest=M.build()\n    M.validate(manifest,ROOT,RUNTIME,OUT,PLIST,create=False)\n    with dest.open('x') as f:f.write(json.dumps(manifest,indent=2)+'\\n')\n    print(json.dumps(dict(status='readonly_captured_kernel_confined',files=len(manifest['files']),manifest=str(dest))))\nif __name__=='__main__':main()\n"  # noqa: E501


def capture_fixture(tmp_path):
    r, o, m = fixture(tmp_path)
    runtime = Path(__file__).resolve().parents[2]
    context = dict(
        release_head="a" * 40,
        tool_merge_head="b" * 40,
        validation_pr=56,
        validation_head="c" * 40,
        validation_base="d" * 40,
        validation_run=123,
        queue_sha256="e" * 64,
        index_sha256="f" * 64,
    )
    roles = {}
    for role in ("index-activation-review", "validation-admission-review"):
        path = r / (role + ".json")
        path.write_text(
            json.dumps(dict(version=1, role=role, verdict="PASS", findings=[], context=context))
        )
        roles[role] = dict(path=path.name, sha256=t.sha(path))
        m["bindings"].append(str(path))
    (r / "capture-manifest.py").write_text(CAPTURE_ENTRY)
    m["script"] = str(r / "capture-manifest.py")
    # Real entry/kernel/children/IO; only online control transport is synthetic.
    (r / "manifest.py").write_text(
        "from pathlib import Path\nimport json,hashlib\n"
        + "OUT=Path(__file__).resolve().parent\n"
        + f"ONLINE=Path({str(o)!r});RUNTIME=Path({str(runtime)!r})\n"
        + f"def bindings(path):return ({{'preflight_root':{str(r)!r}}},ONLINE,RUNTIME,ONLINE/'fixture.plist')\n"  # noqa: E501
        + "def review_roles(b,out):\n v=json.loads((out/'capture.json').read_text())\n assert len(v['roles'])==2\n"  # noqa: E501
        + "def build():\n return {'files':[{'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(ONLINE.iterdir()) if p.is_file()]}\n"  # noqa: E501
        + "def validate(m,*args,**kw):\n assert kw=={'create':False}\n for row in m['files']:assert hashlib.sha256((ONLINE/row['path']).read_bytes()).hexdigest()==row['sha256']\n"  # noqa: E501
    )
    for name in ("deploy.py", "snapshot_inventory.py", "rollback.py"):
        (r / name).write_text("# inert synthetic dependency\n")
    sources = {
        name: t.sha(r / name)
        for name in (
            "deploy.py",
            "manifest.py",
            "snapshot_inventory.py",
            "rollback.py",
            "capture-manifest.py",
        )
    }
    m["script_sha256"] = t.sha(r / "capture-manifest.py")
    (r / "capture.json").write_text(
        json.dumps(
            dict(
                version=1,
                script_sha256=m["script_sha256"],
                context=context,
                roles=roles,
                sources=sources,
            )
        )
    )
    m["bindings"].append(str(r / "capture.json"))
    save(r, m)
    return r, o, m


def capture_invoke(root):
    return subprocess.run(
        [sys.executable, "-B", "-m", "scripts.pipeline_preflight", "capture", "--root", str(root)],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
    )


@MAC
def test_native_capture_then_deployment_then_verify(tmp_path):
    second = tmp_path / "rehearsal"
    second.mkdir()
    dr, online, expected = deployment_fixture(second)
    first = tmp_path / "capture"
    first.mkdir()
    r, o, m = capture_fixture(first)
    # Synthetic source data contains the complete typed deployment plan. The
    # capture output, rather than the test's in-memory object, drives rehearsal.
    seed = o / "prepared-deployment.json"
    seed.write_text(json.dumps(expected))
    module = r / "manifest.py"
    source = module.read_text().replace(
        "return {'files':",
        "return {'prepared_deployment':json.loads((ONLINE/'prepared-deployment.json').read_text()),'files':",  # noqa: E501
    )
    module.write_text(source)
    auth = json.loads((r / "capture.json").read_text())
    auth["sources"]["manifest.py"] = t.sha(module)
    (r / "capture.json").write_text(json.dumps(auth))
    before = t.inventory([o])
    observed = capture_invoke(r)
    assert observed.returncode == 0, observed.stdout + observed.stderr
    result_path = r / "evidence/attempt-0/result.json"
    result = json.loads(result_path.read_text())
    assert result["adapter"] == "capture" and result["mode"] == "readonly_capture"
    assert [p["phase"] for p in result["phases"]] == ["capture"]
    assert result["phases"][0]["exit_code"] == 0 and result["before"] == result["after"]
    captured = r / "deployment-manifest.json"
    assert captured.is_file() and t.inventory([o]) == before
    dm = json.loads(captured.read_text())["prepared_deployment"]
    assert dm == expected
    commitment = dr / "capture-commitment.json"
    commitment.write_text(
        json.dumps(
            dict(captured_manifest_sha256=t.sha(captured), capture_result_sha256=t.sha(result_path))
        )
    )
    dm["bindings"].append(str(commitment))
    save(dr, dm)
    dbefore = t.inventory([online])
    assert invoke(dr) == 0
    context = t.VerificationContext(
        root=str(dr),
        attempt=0,
        result_sha256=t.sha(dr / "evidence/attempt-0/result.json"),
        manifest_sha256=t.sha(dr / "manifest.json"),
        payload_sha256=dm["script_sha256"],
        release_head=dm["deployment"]["head"],
        python=sys.executable,
        expected_bindings=(("capture-commitment.json", t.sha(commitment)),),
    )
    assert t.verify_result(context)["status"] == "verified"
    assert t.inventory([online]) == dbefore and t.inventory([o]) == before


@MAC
def test_native_capture_pending_roles_before_online_io(tmp_path):
    r, o, m = capture_fixture(tmp_path)
    auth = json.loads((r / "capture.json").read_text())
    auth["context"] = None
    (r / "capture.json").write_text(json.dumps(auth))
    m["online_inputs"].insert(0, str(o / "never-created"))
    save(r, m)
    observed = capture_invoke(r)
    assert observed.returncode == 2 and "unknown or missing fields" in observed.stdout
    assert not (r / "evidence").exists() and not (r / "deployment-manifest.json").exists()


@pytest.mark.parametrize(
    "mutation", ["unknown", "failed", "context", "digest", "source", "missing", "deployment"]
)
def test_capture_closed_roles_reject_before_online_read(tmp_path, mutation):
    r, o, m = capture_fixture(tmp_path)
    path = r / "capture.json"
    auth = json.loads(path.read_text())
    role = "validation-admission-review"
    if mutation == "unknown":
        auth["extra"] = True
    elif mutation == "failed":
        receipt = r / (role + ".json")
        value = json.loads(receipt.read_text())
        value["verdict"] = "FAIL"
        receipt.write_text(json.dumps(value))
        auth["roles"][role]["sha256"] = t.sha(receipt)
    elif mutation == "context":
        auth["context"]["validation_run"] += 1
    elif mutation == "digest":
        auth["roles"][role]["sha256"] = "0" * 64
    elif mutation == "source":
        (r / "rollback.py").write_text("# changed")
    elif mutation == "missing":
        (r / (role + ".json")).unlink()
    else:
        m["deployment"] = {}
    path.write_text(json.dumps(auth))
    with patch.object(t, "inventory", side_effect=AssertionError("unexpected online inventory")):
        with pytest.raises((t.SafetyError, FileNotFoundError)):
            t.capture_roles(r, m)
