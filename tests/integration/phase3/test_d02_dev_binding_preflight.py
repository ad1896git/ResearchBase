"""Explicit local DEV_ONLY facility; no fallback to CI/admin integration URLs."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from tests.unit.phase3.test_bearing_installation_process import _root, installation

from researchbase.foundation.bearing_installation import _artifact_digest, _parse_manifest

RECEIPT_SHA = "aa200178de3fc88379a33c4e524ce8694c99b5082ea5be15d0082235bb23f7aa"
ROOT = Path(__file__).resolve().parents[3]

CHILD = r"""import sys
from pathlib import Path
from typing import Any, cast
base=Path(__file__).parent.parent
lib=base/'runtime'/'lib'/('python%d.%d'%sys.version_info[:2])
sys.path[:]=[str(base/'source'),str(lib),str(lib/'lib-dynload'),str(lib/'site-packages')]
import json,os
from researchbase.foundation import bearing_installation as bi
records=base/'records'
prepared=bi.prepare_installation(approval_path=records/'approval.json',manifest_path=records/'manifest.json',namespace='test')
from researchbase.agent_runtime.domain.bearing_evaluation import evaluate
proof=bi.verify_installation(prepared=prepared,fixed_callable=evaluate)
from researchbase.persistence import database as db
from researchbase.foundation.bearing_binding_contracts import BindingError
from sqlalchemy import text
scenario=sys.argv[1]
path=records/'binding.json'
v=json.loads(path.read_bytes())
if scenario=='wrong-owner':v['database']['owner_oid']+=1
if scenario=='wrong-db-oid':v['database']['oid']+=1
if scenario=='wrong-session-role':v['roles']['session']['oid']+=1
if scenario=='wrong-helper-owner':
    old_owner=v['helper']['owner_oid'];v['helper']['owner_oid']+=1
    for grant in v['helper']['effective_acl']:
        for field in ('grantee_oid','grantor_oid'):
            if grant[field]==old_owner:grant[field]=v['helper']['owner_oid']
if scenario=='wrong-extra-acl':
    import copy
    extra=copy.deepcopy(v['helper']['effective_acl'][-1]);extra['grantee_oid']=4294967294
    v['helper']['effective_acl'].append(extra)
    v['helper']['effective_acl'].sort(key=lambda r:(r['grantee_oid'],r['grantor_oid'],
        r['privilege'],r['is_grantable']))
if scenario=='wrong-current-role':v['roles']['current']['oid']+=1
if scenario=='wrong-definition':v['helper']['definition_sha256']='0'*64
if scenario=='wrong-system':v['database']['system_identifier']='123456'
if scenario=='wrong-head':v['alembic_revision']='0082_no_match'
if scenario=='wrong-helper':v['helper']['oid']+=1
if scenario=='wrong-acl':v['helper']['effective_acl'][-1]['is_grantable']=True
if scenario=='wrong-cas':v['cas']['inode']+=1
if scenario=='wrong-lease':v['lease']['inode']+=1
if scenario.startswith('wrong-'):path.write_text(json.dumps(v));path.chmod(0o600)
if scenario=='ambient':os.environ['PGHOSTADDR']='127.0.0.1'
def fault(*args,**kwargs):raise RuntimeError('injected development fault')
if scenario=='fault-create':db.create_engine=fault
if scenario=='fault-connect':
    from sqlalchemy import event
    real_engine=db.create_engine;requested_connections=[]
    def engine_with_connect_fault(*args,**kwargs):
        e=real_engine(*args,**kwargs)
        def fail_after_physical_connect(connection):
            requested_connections.append((connection,connection.connection.driver_connection));fault()
        event.listen(e,'engine_connect',fail_after_physical_connect);return e
    db.create_engine=engine_with_connect_fault
if scenario=='fault-observe':db.observe_database=fault
if scenario=='fault-compare':db.compare_database=fault
if scenario=='fault-issue':
    class FailIssue(dict):
        def __setitem__(self,*args):fault()
    db._observations=FailIssue()
if scenario=='fault-end':
    from sqlalchemy import event
    real_engine=db.create_engine
    def engine_with_fault(*args,**kwargs):
        e=real_engine(*args,**kwargs);event.listen(e,'commit',fault);return e
    db.create_engine=engine_with_fault
if scenario=='fault-recheck':
    original_recheck=db._recheck
    calls=[0]
    def check_with_fault(*args):
        calls[0]+=1
        if calls[0]==2:fault()
        return original_recheck(*args)
    db._recheck=check_with_fault
try:
    factory=db.create_binding_preflight_factory(binding_record_path=path,installation=proof,fixed_callable=evaluate)
except BindingError as exc:
    assert scenario.startswith(('wrong-','fault-')) or scenario=='ambient',repr(exc.__cause__)
    if scenario=='fault-connect':
        assert 'cleanup unknown' in str(exc) and len(requested_connections)==1
        assert not db._bound_roots
        from researchbase.foundation.local_bearing_registration import acquire_lease,LeaseError
        try:acquire_lease(Path(v['lease']['path']))
        except LeaseError:pass
        else:raise AssertionError('unknown connection creation released old lease')
        # Fixture-only natural process disposal; no product recovery or release receipt.
        connection,driver=requested_connections[0];connection.close();assert driver.closed
        print(json.dumps({'scenario':scenario,'result':'PASS_DEV_ONLY_UNKNOWN_QUARANTINE',
            'physical_connection_was_requested':True,'lease_was_retained':True,
            'factory_not_issued':True,'authority':False}))
        sys.exit(0)
    causes=[]; current=exc
    while current is not None:
        causes.append(str(current));current=current.__cause__
    expected=('CAS identity changed' if scenario=='wrong-cas' else
        'local binding changed' if scenario=='wrong-lease' else
        'ambient PostgreSQL configuration denied' if scenario=='ambient' else
        'injected development fault' if scenario.startswith('fault-') else
        'database binding mismatch')
    assert any(expected in message for message in causes),causes
    from researchbase.foundation.local_bearing_registration import acquire_lease
    with acquire_lease(Path(v['lease']['path'])) as released:
        assert released.check()
    assert all(state.closed and state.driver.closed and not state.cleanup_unknown
        for state in db._bound_roots.values())
    print(json.dumps({'scenario':scenario,'result':'DENIED','all_owned_resources_closed':True,
        'expected_cause':expected,'authority':False}))
    sys.exit(0)
assert not scenario.startswith('wrong-') and scenario!='ambient'
if scenario=='overlap':
    try:
        with factory.read_session():
            with factory.read_session():raise AssertionError('overlap admitted')
    except BindingError:pass
    else:raise AssertionError('overlap not quarantined')
    try:factory.preflight()
    except BindingError:pass
    else:raise AssertionError('overlap root reactivated')
    state=db._bound_roots[factory]
    assert state.closed and state.invalid and state.driver.closed and not state.lease.check()
    print(json.dumps({'scenario':scenario,'result':'PASS_DEV_ONLY','overlap_denied':True,'authority':False}))
    sys.exit(0)
a=factory.preflight();a.assert_factory(a.factory_identity)
conn=a.connection_identity;obs=a.observation_id
with factory.read_session() as session:
    row=session.execute(text("SELECT pg_catalog.pg_backend_pid(),"
    "pg_catalog.current_setting('transaction_read_only'),public.pr316d1_enabled()" )).one()
    assert row[1:] == ('on',False)
    if scenario=='positive-bounds':
        bounds=session.execute(text("SELECT pg_catalog.current_setting('statement_timeout'),"
            "pg_catalog.current_setting('lock_timeout'),"
            "pg_catalog.current_setting('transaction_isolation'),"
            "pg_catalog.current_setting('default_transaction_read_only')")).one()
        assert tuple(bounds)==('10s','3s','repeatable read','on'),tuple(bounds)
    from dataclasses import asdict
    observed=asdict(db.observe_database(session.connection()))
    before=session.execute(text("SELECT (SELECT count(*) FROM public.alembic_version),"
        "pg_catalog.current_database(),SESSION_USER")).one()
    assert before[1:] == (v['database']['name'],v['roles']['session']['name'])
    try:a.assert_factory(a.factory_identity)
    except BindingError:pass
    else:raise AssertionError('active session accepted')
b=factory.preflight();b.assert_factory(b.factory_identity)
assert b.connection_identity is conn and b.observation_id is not obs
try:a.assert_factory(b.factory_identity)
except BindingError:pass
else:raise AssertionError('old observation accepted')
with factory.read_session() as session:
    after=session.execute(text("SELECT (SELECT count(*) FROM public.alembic_version),"
        "pg_catalog.current_database(),SESSION_USER")).one()
    pid=session.execute(text("SELECT pg_catalog.pg_backend_pid()" )).scalar_one()
    assert before==after and pid==row[0]
b=factory.preflight();b.assert_factory(b.factory_identity)
factory_token=b.factory_identity
if scenario in ('binding-expiry','installation-expiry','cas-inode-replace','lease-path-replace'):
    state=db._bound_roots[factory]
    original_connection=state.connection;original_driver=state.driver
    restoration=None;clock_target=None;original_clock=None
    if scenario in ('binding-expiry','installation-expiry'):
        from datetime import timedelta
        clock_target=db if scenario=='binding-expiry' else bi
        original_clock=clock_target.datetime
        class ExpiredClock(original_clock):
            @classmethod
            def now(cls,tz=None):return original_clock.now(tz)+timedelta(days=2)
        clock_target.datetime=ExpiredClock
    elif scenario=='cas-inode-replace':
        original_path=Path(v['cas']['path']);saved=original_path.with_name('cas.saved')
        original_path.rename(saved);original_path.mkdir(mode=0o700)
        assert original_path.stat().st_ino != v['cas']['inode']
        def restoration():original_path.rmdir();saved.rename(original_path)
    else:
        original_path=Path(v['lease']['path']);saved=original_path.with_name('lease.saved')
        original_path.rename(saved);original_path.touch(mode=0o600)
        assert original_path.stat().st_ino != v['lease']['inode']
        def restoration():original_path.unlink();saved.rename(original_path)
    try:
        if clock_target is not None:b.assert_factory(factory_token)
        else:factory.preflight()
    except BindingError:pass
    else:raise AssertionError('post-success continuity fault accepted')
    finally:
        if clock_target is not None:clock_target.datetime=original_clock
        if restoration is not None:restoration()
    assert state.connection is original_connection and state.driver is original_driver
    try:factory.preflight()
    except BindingError:pass
    else:raise AssertionError('restored resource/clock reactivated invalid root')
    if scenario=='lease-path-replace':
        from researchbase.foundation.local_bearing_registration import LeaseError,acquire_lease
        assert state.closed and state.invalid and state.cleanup_unknown and state.driver.closed
        try:state.lease.close_checked()
        except LeaseError:pass
        else:raise AssertionError('lost lease continuity minted close proof')
        try:factory.close()
        except BindingError:pass
        else:raise AssertionError('unknown root silently resumed cleanup')
        # Fixture-only new lease is not a new binding factory or old-root recovery.
        with acquire_lease(original_path) as other:
            assert other.identity_token is not state.lease.identity_token
            assert other.check()
    else:
        factory.close()
        assert state.closed and state.invalid and state.driver.closed and not state.cleanup_unknown
    print(json.dumps({'scenario':scenario,'result':'PASS_DEV_ONLY_CONTINUITY_DENIAL',
        'successful_real_factory_before_fault':True,'same_original_connection':True,
        'restoration_reactivation_denied':True,'clock_fault_injection':clock_target is not None,
        'cleanup_unknown':state.cleanup_unknown,'authority':False}))
    sys.exit(0)
if scenario in ('replace-wrapper','replace-callable'):
    if scenario=='replace-wrapper':
        from contextlib import contextmanager
        original=db.BoundBindingFactory.read_session
        @contextmanager
        def different_wrapper(self):yield None
        db.BoundBindingFactory.read_session=different_wrapper
        def restore():db.BoundBindingFactory.read_session=original
    else:
        original=evaluate.__code__;evaluate.__code__=(lambda:None).__code__
        def restore():evaluate.__code__=original
    try:b.assert_factory(factory_token)
    except BindingError:pass
    else:raise AssertionError('substituted wrapper/code accepted')
    restore()
    try:b.assert_factory(factory_token)
    except BindingError:pass
    else:raise AssertionError('quarantined root reactivated after restoration')
if scenario=='thread':
    import threading
    token=b.factory_identity
    outcomes=[]
    def check():
        try:b.assert_factory(token)
        except BindingError:outcomes.append('DENIED')
    t=threading.Thread(target=check);t.start();t.join();assert outcomes==['DENIED']
if scenario=='fork':
    pid=os.fork()
    if pid==0:
        try:factory.preflight()
        except BindingError:os._exit(0)
        os._exit(1)
    assert os.waitpid(pid,0)[1]==0
if scenario in ('fault-close','fault-session-rollback'):
    state=db._bound_roots[factory]
    original_close=state.connection.close
    if scenario=='fault-close':state.connection.close=fault
    try:
        if scenario=='fault-close':factory.close()
        else:
            with factory.read_session() as session:
                session.rollback=fault
    except BindingError:pass
    else:raise AssertionError('unknown cleanup accepted')
    assert state.closed and state.invalid and state.cleanup_unknown and state.lease.check()
    from researchbase.foundation.local_bearing_registration import acquire_lease, LeaseError
    try:acquire_lease(Path(v['lease']['path']))
    except LeaseError:pass
    else:raise AssertionError('unknown former root lease was reusable')
    try:factory.close()
    except BindingError:pass
    else:raise AssertionError('unknown cleanup silently retried')
    # Test-only final disposal after retaining the real unknown/quarantine assertion.
    # This is not product reactivation or a synthetic REVOKED/rollback receipt.
    state.connection.close=original_close;original_close();state.engine.dispose()
    state.lease.close_checked().assert_released_for(state.lease.identity_token)
    state.installation.close()
    try:factory.preflight()
    except BindingError:pass
    else:raise AssertionError('quarantined root reactivated')
    print(json.dumps({'scenario':scenario,'result':'PASS_DEV_ONLY_UNKNOWN_QUARANTINE',
        'lease_was_retained':True,'authority':False}))
    sys.exit(0)
if scenario=='pin-invalidate':
    from sqlalchemy import event
    state=db._bound_roots[factory]
    new_connections=[]
    event.listen(state.engine,'connect',lambda *args:new_connections.append(True))
    state.connection.invalidate()
    try:factory.preflight()
    except BindingError:pass
    else:raise AssertionError('replacement connection accepted')
    assert not new_connections and state.driver.closed
if scenario=='replace-record':
    raw=path.read_bytes();path.unlink();path.write_bytes(raw);path.chmod(0o600)
    try:factory.preflight()
    except BindingError:pass
    else:raise AssertionError('replacement accepted')
else:
    factory.close();factory.close()
try:b.assert_factory(factory_token)
except BindingError:pass
else:raise AssertionError('closed root accepted')
print(json.dumps({'scenario':scenario,'result':'PASS_DEV_ONLY','same_backend_pid':row[0],
 'observed':observed,'observed_timeouts':list(bounds) if scenario=='positive-bounds' else None,
 'read_only':'on','helper_enabled':False,'before_after_equal':list(before)==list(after),'authority':False}))
"""


@pytest.fixture(scope="module")
def dev_installation():
    supplied = os.getenv("D02_DEV_FACILITY_RECEIPT")
    if not supplied:
        pytest.skip("local DEV_ONLY D02 receipt explicitly required; no admin/CI fallback")
    receipt_path = Path(supplied)
    raw = receipt_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == RECEIPT_SHA
    facts = json.loads(raw)
    assert facts["authentication"] == "EXISTING_LOCAL_TRUST_UNCHANGED_DEV_ONLY"
    writer_path = receipt_path.parent / "writer-facts.json"
    writer = json.loads(writer_path.read_bytes())
    assert hashlib.sha256(writer_path.read_bytes()).hexdigest() == (
        "57864877bd2c19733b0a4d9f8d6f7377c9bf2023b0511d0ec3a4451b7fcb8eb5"
    )
    # RESULT's before/after SHA refers old-material snapshots, not writer-facts.
    assert writer["database"]["oid"] == facts["database"]["oid"]
    generator = cast(Any, installation).__wrapped__()
    base, interpreter = next(generator)
    try:
        source = base / "source"
        shutil.copytree(
            ROOT / "src/researchbase",
            source / "researchbase",
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        lib = base / "runtime" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}"
        shutil.copytree(
            Path(sys.prefix) / "lib" / lib.name / "site-packages",
            lib / "site-packages",
            dirs_exist_ok=True,
            symlinks=False,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        (source / "bootstrap.py").write_text(CHILD)
        for current, dirs, files in os.walk(base):
            Path(current).chmod(0o700)
            for name in dirs:
                (Path(current) / name).chmod(0o700)
            for name in files:
                (Path(current) / name).chmod(
                    0o700 if Path(current) / name == interpreter else 0o600
                )
        records = base / "records"
        m = json.loads((records / "manifest.json").read_bytes())
        m["roots"] = [
            _root("source", "package", source),
            _root("runtime", "runtime", base / "runtime" / "lib"),
        ]
        m["artifact_sha256"] = _artifact_digest(_parse_manifest(json.dumps(m).encode()))
        manifest = records / "manifest.json"
        manifest.write_text(json.dumps(m))
        manifest.chmod(0o600)
        a = json.loads((records / "approval.json").read_bytes())
        a["artifact_sha256"] = m["artifact_sha256"]
        a["manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
        (records / "approval.json").write_text(json.dumps(a))
        (records / "approval.json").chmod(0o600)
        vectors = json.loads((ROOT / "docs/phase3/d01-binding-v0.4/vectors.json").read_text())[
            "vectors"
        ]
        v = json.loads(
            bytes.fromhex(
                next(x["input_hex"] for x in vectors if x["expected"] == "ACCEPT_CODEC_ONLY")
            )
        )
        v["approved_at"] = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
        v["expires_at"] = a["expires_at"]
        v["deployment"].update(
            id=a["deployment_id"],
            host=a["host"],
            uid=a["uid"],
            namespace=a["namespace"],
            installation_manifest_sha256=a["manifest_sha256"],
            artifact_sha256=a["artifact_sha256"],
            callable_module=a["callable_module"],
            callable_qualname=a["callable_qualname"],
            callable_code_sha256=m["callable_code_sha256"],
        )
        v["database"] = {k: facts["database"][k] for k in ("name", "oid", "owner_oid")}
        v["database"].update(system_identifier=facts["cluster_system_identifier"], pg_major=18)
        v["alembic_revision"] = facts["head"]
        role = {"name": facts["writer_role"]["rolname"], "oid": facts["writer_role"]["oid"]}
        v["roles"]["session"] = role
        v["roles"]["current"] = role
        h = writer["helper"]
        v["helper"].update(
            oid=h["oid"],
            owner_oid=h["owner_oid"],
            definition_sha256=h["definition_sha256"],
            effective_acl=[
                {
                    "grantee_oid": r["grantee"],
                    "grantor_oid": r["grantor"],
                    "privilege": r["privilege"],
                    "is_grantable": r["grantable"],
                }
                for r in h["effective_acl"]
            ],
        )
        v["connection"].update(socket_directory=facts["socket"], port=facts["port"])
        cas = base / "cas"
        cas.mkdir(mode=0o700)
        lease = records / "lease"
        lease.touch(mode=0o600)
        for key, path, mode in [("cas", cas, 0o700), ("lease", lease, 0o600)]:
            st = path.stat()
            v[key].update(
                path=str(path), device=st.st_dev, inode=st.st_ino, uid=st.st_uid, mode=mode
            )
        v["cas"]["namespace"] = a["namespace"]
        print(
            "D02 FINAL FROZEN INSTALLATION",
            json.dumps(
                {
                    "manifest_sha256": a["manifest_sha256"],
                    "artifact_sha256": a["artifact_sha256"],
                    "owned_source_sha256": {
                        relative: hashlib.sha256((source / relative).read_bytes()).hexdigest()
                        for relative in (
                            "researchbase/foundation/bearing_binding_contracts.py",
                            "researchbase/foundation/bearing_binding.py",
                            "researchbase/foundation/bearing_installation.py",
                            "researchbase/foundation/local_bearing_registration.py",
                            "researchbase/persistence/bearing_preflight.py",
                            "researchbase/persistence/database.py",
                            "researchbase/persistence/uow.py",
                            "researchbase/hg1_runtime.py",
                        )
                    },
                    "source_files": len(m["roots"][0]["files"]),
                    "runtime_files": len(m["roots"][1]["files"]),
                    "driver_profile": (
                        "SQLAlchemy pure Python + psycopg python; original origin checks unchanged"
                    ),
                },
                sort_keys=True,
            ),
        )
        yield base, interpreter, json.dumps(v).encode()
    finally:
        generator.close()


@pytest.mark.parametrize(
    "scenario",
    [
        "positive",
        "positive-bounds",
        "wrong-db-oid",
        "wrong-session-role",
        "wrong-helper-owner",
        "wrong-extra-acl",
        "fault-connect",
        "binding-expiry",
        "installation-expiry",
        "cas-inode-replace",
        "lease-path-replace",
        "overlap",
        "wrong-owner",
        "wrong-current-role",
        "wrong-definition",
        "wrong-system",
        "wrong-head",
        "wrong-helper",
        "wrong-acl",
        "wrong-cas",
        "wrong-lease",
        "ambient",
        "thread",
        "fork",
        "replace-record",
        "pin-invalidate",
        "replace-wrapper",
        "replace-callable",
        "fault-create",
        "fault-observe",
        "fault-compare",
        "fault-issue",
        "fault-end",
        "fault-recheck",
        "fault-close",
        "fault-session-rollback",
    ],
)
def test_actual_writer_preflight(dev_installation, scenario):
    base, interpreter, record = dev_installation
    path = base / "records/binding.json"
    path.write_bytes(record)
    path.chmod(0o600)
    run = subprocess.run(
        [str(interpreter), "-I", "-S", "-B", str(base / "source/bootstrap.py"), scenario],
        env={
            "TMPDIR": str(base),
            "DISABLE_SQLALCHEMY_CEXT_RUNTIME": "1",
            "PSYCOPG_IMPL": "python",
            "PATH": "/opt/homebrew/opt/postgresql@18/bin:/usr/bin:/bin",
        },
        capture_output=True,
        text=True,
        timeout=120,
    )
    print(run.stdout, run.stderr)
    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(run.stdout.strip().splitlines()[-1])
    assert result["authority"] is False
    assert result["result"] == (
        "PASS_DEV_ONLY_CONTINUITY_DENIAL"
        if scenario
        in ("binding-expiry", "installation-expiry", "cas-inode-replace", "lease-path-replace")
        else "PASS_DEV_ONLY_UNKNOWN_QUARANTINE"
        if scenario in ("fault-close", "fault-session-rollback", "fault-connect")
        else "DENIED"
        if scenario.startswith(("wrong-", "fault-")) or scenario == "ambient"
        else "PASS_DEV_ONLY"
    )
