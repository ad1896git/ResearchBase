# v0.4 owner-resolved specification crosswalk

UPDATED PROPOSAL pending independent review. Base7540438; previous9a proposal and
its known HOLD decisions remain in Git history. They are superseded by the explicit
owner resolution below, not silently interpreted away. Full production D1 remains
PROPOSED; the bounded reference-policy and development-scope changes are distinct.

## Owner resolution

Verbatim owner decision, transcribed by root (including the explicit follow-up choice):

```text
D01 v0.4 裁决：
辅助函数：采用“函数定义哈希 + 所有者 + 安全标志 + OID + 有效 ACL”。批准将 D1 规格中的“全部属性”修订为“所有安全相关属性”，修订内容写入规格并注明来源。
数据库识别：保留数据库所有者匹配，共五个字段。
D02 设施：使用本机 Homebrew PG18，新建专用测试数据库和受限角色，仅用于开发测试。角色创建步骤我已审阅，___（我自己执行 / 授权你执行，执行前后各回报一次结果）。
按以上修改 v0.4，独立评审通过后直接冻结，准入 D02 实现和 D03 设计。关闭 #57，保留分支。

后续明确选择：
- 授权你执行；执行前后各汇报一次结果
```

Source SHA256 `ecea1afa09529fccbf432b0ec8ed7c39142acfa5ca92c14773104ac9b25c6a48`; operator original is
`.pipeline/logs/reviews/D01-v04-owner-resolution-20261102/OWNER-RESOLUTION.md`.
No secret/host value/credential is embedded. This is actual owner authority for the
narrow delta, not a new signing framework or inferred permission.

D1=`docs/phase3/design/PR3-16-d1-amendment-contract.md`; ADR0027 references its
closed security set. Historical line references below are at754 before this diff;
current changed policy is the dated2026-11-02 O09 paragraph.

| Principle / previous issue | Historical requirement and exact quoted location | Resolution / unchanged boundary |
|---|---|---|
| DB fingerprint | D1:472 “pg_database 的 oid/datdba”; :454 “精确身份记录” | RESOLVED_BY_OWNER: five values system_identifier/name/OID/ownerOID/PGmajor all match. PGminor not bound; actualPG/config remain O03 observations. Alembic, Unix endpoint/port, session/current identities are retained separately. |
| One owner-confirmed rebind | D1:440 protected scoped approval; :476 “授权仍来自受保护的真实操作员/部署权限” | One public command, internal observe→diff→actual ownerconfirm→append. No self-approved boolean/hash authority, no overwrite/activation. Minor/role maintenance with no fingerprint difference still needs explicit rebind event. |
| Direct role predicates | D1:474 “无DDL、superuser、CREATEROLE/CREATEDB/REPLICATION/BYPASSRLS及切换owner权限” | All retained, including direct/indirect MEMBER denial for DB/functionowners and reachable elevatedroles. No complete rolegraph encoding required. PUBLIC effective privileges require actualaudit, not NOINHERIT assumption. |
| Helper catalog scope | D1:456/464/472 previously “全部…属性”; :410–414 historical “retain both PUBLIC and explicit role ACLs byte-for-byte” | RESOLVED_BY_OWNER: future comparison is OID/fixedsignature/definitionSHA/owner/finite securityset/full normalized effectiveACL, including allgrantees/grantors/PUBLIC/owner/grantability. Historical0083 rawACL/noGRANT/noownerchange duties untouched. SameTX and onlyapprovedfalse→truebody replacement retained. |
| Unix only | D1:454 endpoint/port; :438 singlehost/localFS | Narrow supported transport, not TCPfallback. Actual socketdir/port is root-supplied evidence; localdev HBAtrust is not protected referenceauthentication. |
| Standard JSON | D1 protected operatorrecord; ADR no new canonical/signing JSONtruthsource | Sorted standardJSON+SHA, closedshape/UTF8/duplicates/nonfinite/bounds. Whitespace/keyorder aliases standard; no v0.3 custombyteprotocol or55-vector repetition. SHA cannot issue authority. |
| Sole engine module | D1:442 one fixedroot; :450 “Before a transaction”; :446 actualcommit/failurecleanup lease | Existing database.py is proposed solecreator; uow.py and migrations.env bypasses must be refactored later. Lint/tests add defense, never replace per-attempt actualconnection/preflight/continuouslease/commit-revoke evidence. No engine source edited now. |
| D02 stage/provision | D1:478 reference BEFORE_CODING provisioning requirements | RESOLVED_BY_OWNER: root may create NEW dedicated localHomebrewPG18 devDB/restrictedroles with before/after reports, enabling authorized boundedcoding/test path after review and actualdevfacts. This development exception does not satisfy reference auth/installation/migration/apply/production gates. No existingDB/role/globalauth changes. |

## Exact approved source delta and gate

D1 O09 replaces only the future all-catalog comparison with the finite securityset
and complete semantic ACL, pins DBowner as the fifth value and explicitly records
owner-selected local development scope. ADR adds only a dated reference/provenance
note. No migration file, historical ACL assertion, enabled=false source, lifecycle,
Application/repository layering, lease, sameTX/actualcommit or reference/production
exclusion is changed. See source-binding.json for exact input SHA; diff is the
audit surface, not author private context.

Previous HELPER/DB4/STAGE owner questions are resolved. Remaining statuses are
PENDING_INDEPENDENT_REVIEW and PENDING_ROOT_ACTUAL_DEV_REPORTS, not a request for
duplicate direction approval. Root directly freezes after PASS, admits D02 bounded
implementation/D03 design with actual prerequisites, then closes57 preservingbranch.
Author does not provision or close a PR. Independent PASS is not actualprovision,
protectedreference/A2, realconsumer/PGbinding or production acceptance.
