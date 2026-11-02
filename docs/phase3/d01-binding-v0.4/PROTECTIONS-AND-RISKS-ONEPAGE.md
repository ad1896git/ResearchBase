# v0.4 保留／放弃／实际风险（一页，PROPOSED）

**状态：HOLD，不自动冻结。** v0.3/#57草稿及分支保留。D01 HIGH与原依赖不变。

| 项目 | 保留保护 | 减少什么／实际风险 |
|---|---|---|
| DB／版本 | cluster system_identifier、DB名/OID、PG18主版本、Alembic；实际身份不等于授权 | 不绑minor，未声明维护升级可能无法自动察觉；性能/PG配置校准仍要真实记录。datdba原身份若移除，与D1固定核对不等价，待确认。 |
| role | 直接/间接owner拒绝，super/bypass/createrole及原CREATEDB/REPLICATION/DDL/ownerSET禁令 | 不保存完整图；不影响这些谓词的成员/选项变更可能无diff。DBA必须维护前撤销、显式rebind；不能声称已监控全部权限漂移。 |
| helper | pg_get_functiondef原UTF8哈希、owner、安全flags、选定roles有效EXECUTE；不自动改任何ACL | 不能证明原OID、raw ACL/所有其他属性不变；额外给其他role的权限可能不改变writer的EXECUTE。与D1:456/464/472及410要求有实质取舍。PUBLIC EXECUTE原样保留，不是误配。 |
| JSON | 标准排序JSON+SHA，版本/闭合字段/UTF8/重复键/非有限值/资源上限；批准记录只追加 | SHA不证明owner身份；JSON等价表示同hash，Unicode不同值仍不同。授权仍来自受保护operator和真正owner确认，不能加approved=true。 |
| 连接／防绕过 | Unix-only、固定组合根；sole engine creator；每transaction原preflight、sameconnection、连续lease、真实commit/revoke/cleanup与原receipt | lint只能约束受审代码，不是恶意同UID进程隔离或真实连接证明。现多入口尚未重构；实际socket/角色/设施未提供。 |

**继续保留**：default deny、普通CLI/API无genuine注册、无调用方自选authority；完整安装/代码闭包、CAS/namespace/inode；资源/预算/expiry；UNKNOWN/full reservation、不换原身份/不退款；reference不升级为production；真实PG/独评/阶段门禁。

**09:00只需决定三件事**：helper缩小的是record还是原完整核验；DB四字段是否删除原owner/其他身份匹配；D02自动准入是否仍须满足D1:478实际基础设施/认证provision。任一未决都不freeze、不写role/新批准、不close57。D03设计可准备不等于集成验收；本包所有真实设施/数据库行为NOT RUN。
