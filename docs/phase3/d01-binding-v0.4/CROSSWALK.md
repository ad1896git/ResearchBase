# v0.4 seven-principle specification crosswalk

PROPOSED; exactbase7540438. This is an author crosswalk, not independent PASS.
D1=`docs/phase3/design/PR3-16-d1-amendment-contract.md`; ADR=`docs/architecture/adr/ADR-0027-pr3-16-d1-node-budget-amendment.md`.
Production D1 is PROPOSED (D1:3); the accepted limited reference policy and its
specific stage/preflight requirements must be distinguished from production GO.
No v0.3 preference is treated as authority.

| Owner principle | Authoritative text / exact location | Finding / candidate effect |
|---|---|---|
| 1 four DB values, PGmajor only | D1:472 “pg_control_system().system_identifier … pg_database 的 oid/datdba … session_user/current_user …”; :454 “精确身份记录，包括…端点与端口…迁移角色及函数 owner” | No requirement to bind PGminor was found; keep real PG/config in O03 measurements. **QUESTION DB4**: if “onlyfour” drops approved datdba/other fixed identity comparison, live owner-membership denial is not the same as matching original owner identity. Record permits DB-owner change without a bound-value difference if writer remains non-owner. Unix endpoint and session/current role identity retained separately, explicitly not silently deleted. |
| 2 append-only owner-confirmed rebind | D1:440 “operator…create a separate protected, scoped bootstrap authorization record”; :476 “授权仍来自受保护的真实操作员/部署权限”; :478 “BEFORE_CODING 须合同接受、基础参考基础设施身份与认证 provision 及接口审查” | Append/new ownerdecision is compatible, no mutation/self-approval. **QUESTION STAGE**: automatic D02 implementation admission cannot be reported as satisfying missing actual prerequisite facts/authentication/provision. Actual socket/admin/writer/DB are unassigned. Compatible conditional acceptance may retain those gates; bypass requires owner decision, not a record-format side effect. |
| 3 direct conservative role checks, no graph record | D1:474 “普通Application writer不是函数owner，无DDL、superuser、CREATEROLE/CREATEDB/REPLICATION/BYPASSRLS及切换owner权限” | No normative demand for serialized full role graph found. Keep all these unchanged predicates (also indirect/equality owner membership) using direct queries. NOINHERIT does not remove PUBLIC privileges. Benign membership changes can leave policy predicates unchanged: protected maintenance must explicitly revoke/rebind, not claim complete drift detection. |
| 4 definitionhash+owner/security/effectiveEXECUTE, not35fields | D1:456 “OID、零参数 boolean 签名、owner、ACL、语言、volatility、security、search_path 和其他属性…一致”; :464 “原 OID、签名、owner、ACL、search_path 和全部其他函数属性未变”; :472 “pg_proc OID/owner/ACL/全部属性”; :410–414 “retain both PUBLIC and explicit role ACLs byte-for-byte” | **CONFLICT HELPER if summary replaces fixed preflight/activation checks.** Definitionhash does not bind OID/raw ACL, nor prove every catalog attribute unchanged. Effective EXECUTE for the selected writer can stay true while another role receives a grant. Keep existing checks until owner resolves scope; do not “fix” by revoking helper PUBLIC. |
| 5 Unix only | D1:454 “端点与端口”; :472 fixed inet_server_addr()/port; :438 singlehost/localFS trustboundary | Compatible restriction, not obligation to keep TCP. Null inet observations do not establish local endpoint authorization; retain actual protected Unix socketdir/port and clusteridentity, no fallback/guessed defaults. Local compose TCP mapping is not a reference Unix grant. |
| 6 standard sorted JSON+SHA, fewer vectors | D1:440 protectedrecord, no required v0.3 binary format; ADR reference decision “无新运行时 canonical schema、表或签名 JSON 真相源” | Compatible operator-record format simplification; JSON/SHA remains data, not approver proof/scientifictruth. Closedshape, duplicate/nonfinite/UTF8/bounds remain necessary. v0.3 bytegrammar/55vectors are prior proposed artifacts, not mandatory new coverage. |
| 7 one engine module, startup preflight beforefactory+lint/tests | D1:442 “exactly one fixed DB/store/verifier binding”; :450 “Before a transaction…preflight”; :446 lease through actualcommit/failurecleanup; ADR:111 typedport/layering | Compatible additional construction discipline only if all runtime invariants remain. One startup check/lint is insufficient for later physicalconnection/reconnect/lifetime. Current database.py/uow.py/migrations.env multiple engine paths need a separately reviewed real refactor, not a new self-issued verification flag or unrelated import exemption. |

## Three owner decision topics; no silent compatibility selection

1. HELPER: choose (A) reduced summary only for record but retain original complete
   O09 fixed preflight/activation catalog evidence (still needs exact approved
   source/record linkage), or (B) explicitly amend that scope to the reduced set and
   accept identity/ACL drift risks. Neither alternative is owner-approved here.
2. DB4: confirm whether actual queried datdba and other fixed identity facts remain
   approved/matched outside the four serialized DB values, or deliberately remove
   their original-identity comparison while retaining conservative live denial.
   Do not conceal extra fields by renaming them into a second truth record.
3. STAGE: preserve actual BEFORE_CODING prerequisites and treat automatic D02
   source authorization as conditional on their satisfaction, or explicitly decide
   a bounded prerequisite change. Missing facilities are not supplied by independent
   design PASS. D03 design is not D02/production integration.

Until resolved: **HOLD_FREEZE_09_DECISION**; no D02 source, no approval-file writing,
no role/PG/migration action, no57close. D1 source governing text is unchanged.
