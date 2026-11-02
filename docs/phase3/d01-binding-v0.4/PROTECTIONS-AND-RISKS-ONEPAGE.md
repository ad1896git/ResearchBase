# v0.4 裁决后保留／减少／实际风险（一页）

**三项policy已由owner明确解决；当前等独评与root实际开发设施报告，不再重复索要方向。** D01 HIGH不变，root独评通过后直接冻结并按裁决处理57；作者不执行DB/角色/关闭PR。

| 项目 | 保留 | 减少与实际风险 |
|---|---|---|
| DB | cluster系统ID、DB名/OID/ownerOID、PG18主版本五项；Alembic/endpoint/role绑定 | 不绑minor；未声明维护升级可能无自动diff。PG/config资源校准仍实际记录，升级/角色变更走同一owner-confirmed append-only rebind。 |
| helper | OID、零参非variadic非setbool签名、定义SHA、owner、明确安全flags/固定search_path/support0、完整normalizedACL | 不再序列化35字段。定义hash仍可能发现许多其他改动，但不单列所有catalog估算/元数据；rawACL的NULL/排序等同权限差异不属未来security比较。0083历史byte-for-byte ACL义务不放松。 |
| 权限 | 全grantee/grantor/EXECUTE/grantable，PUBLIC0+owner完整保留，意外grant拒绝；ordinarywriter禁owner/提升权限/DDL | 不保存完整rolegraph；直接谓词不等于记录所有无影响membership变化。协作DBA维护前撤销/rebind，PUBLIC权限实际audit；不静默REVOKE全局权限。 |
| 格式与防绕开 | 标准JSON闭合字段/UTF8/重复键/非有限值/上限+SHA；唯一enginecreator、每事务实际连接/preflight | JSONhash不是人类批准。lint不是恶意同UID隔离或真实factory/lease证明；新源重构尚未实现，不能冒PASS。 |
| 开发设施 | owner授权root在本机HomebrewPG18创建NEW专用测试DB/受限role，前后报告 | 只是coding/test权限；若本地HBAtrust，必须如实标记，不能当protectedreference认证或A2、genuineconsumer、生产设施。 |

**永久不变**：受保护operator/安装与全代码闭包；CAS/root/namespace/inode；连续lease、真实commit/revoke/cleanup；currententitlement、原receipt/UNKNOWN/full reservation；资源/价格/预算/expiry；CLI/API默认无genuine注册；reference不升级production；原0083保持literalfalse、无历史迁移/表/ACL重写。

**下一步**：独评本候选→root直接freeze；D02按精确source/interface范围和实际dev报告进入bounded实现、D03继续设计。实际reference migration/apply、安装/注册、真实D1科学写入和生产仍各自原门禁。本包向量只证明codec，不证明actualDB/CAS/role安全；无作者SQL或设施操作。
