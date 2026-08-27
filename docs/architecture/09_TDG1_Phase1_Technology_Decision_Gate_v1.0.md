# ResearchBase TDG-1 — Phase 1 Technology Decision Gate

> **版本**：v1.0  
> **状态**：APPROVED TECHNOLOGY BASELINE / IMPLEMENTATION GATE  
> **日期**：2026-08-26  
> **适用范围**：Phase 1 PR-00 ～ PR-18  
> **上位规范**：
> - `ResearchBase_全系统设计文档_架构补全版_v1.2`
> - `ResearchBase_Final_Architecture_Correction_Addendum_v1.0`
> - `ResearchBase_Global_Schema_and_Contract_Registry_v1.0`
> - `ResearchBase_Phase1_Development_Specification_v1.1`
> - `ResearchBase_Cross_Phase_Contracts_and_Compatibility_v1.0`

---

# 0. Gate 结论

TDG-1 正式冻结以下 Phase 1 reference technology profile：

```text
Language              Python 3.12
Package/Env            uv + pyproject.toml
Database               PostgreSQL 18.x
ORM                    SQLAlchemy 2.0.x
Migration              Alembic
DB Driver              psycopg 3
Validation / DTO       Pydantic 2.x
HTTP API               FastAPI 0.141.x
CLI                    Typer 0.27.x
Testing                pytest
Lint / Format          Ruff
Type Check             Pyright
Artifact Store         content-addressed filesystem (Phase 1 reference)
Artifact Store Port    backend-neutral
Local Deployment       Docker Compose
Application Shape      modular monolith
API Style              synchronous application services first
```

Phase 1 不允许各开发人员自行替换这些核心技术。

---

# 1. Decision TDG1-01 — Python

## 决议

```text
Python 3.12.x
```

## 原因

Phase 1 的目标是建立可信 Domain/Persistence Core，而不是验证最新 Python runtime。

Python 3.12：

- typing/runtime 生态成熟；
- SQLAlchemy/Pydantic/FastAPI 支持稳定；
- 科研/HPC 环境兼容性通常优于刚发布的新解释器；
- 减少 Python 3.14/3.15 新 typing/runtime 行为对中级开发者造成额外噪声。

## 兼容策略

```text
Phase 1 CI REQUIRED: Python 3.12
Later CI MAY add newer Python
Production baseline remains 3.12 until ADR
```

不使用 Python 版本特有的新语义作为 Domain 设计前提。

---

# 2. Decision TDG1-02 — Package / Environment Management

## 决议

```text
uv
+
pyproject.toml
+
committed lockfile
```

项目不得同时维护：

```text
requirements.txt
poetry.lock
Pipfile
conda environment as canonical dependency definition
```

作为第二套 Source of Truth。

HPC/Conda 环境若未来需要：

```text
derive/export from project lock
```

而不是反向定义应用依赖。

---

# 3. Decision TDG1-03 — PostgreSQL

## 决议

```text
PostgreSQL 18.x
Reference development patch at design freeze: 18.6
```

不使用 PostgreSQL 19 Beta。

## 版本策略

Docker/CI SHALL pin major：

```text
postgres:18
```

生产部署 SHOULD pin具体 patch/container digest。

允许同一 major 内升级 security/bugfix patch：

```text
18.6 → later 18.x
```

无需 Architecture ADR，但需要：

```text
CI
migration tests
release note review
backup/restore smoke
```

切换 major：

```text
18 → 19
```

需要 TDG/ADR review。

## 为什么不继续锁 PostgreSQL 16

Phase 1 原规范写的是 `PostgreSQL 16+`，不是要求 16。

当前新项目没有 legacy compatibility burden，因此直接选择当前正式 major 18，避免在项目早期引入很快需要升级的基础数据库版本。

---

# 4. Decision TDG1-04 — ORM / SQL

## 决议

```text
SQLAlchemy 2.0.x
Reference design patch: 2.0.52
```

不采用 SQLAlchemy 2.1 Beta。

## ORM 使用规则

```text
SQLAlchemy ORM
= persistence implementation detail

Domain
≠ ORM model
```

写路径：

```text
Application Service
→ Repository Port
→ SQLAlchemy Repository
→ PostgreSQL
```

复杂 provenance/read-model Query MAY 使用：

```text
SQLAlchemy Core
explicit SQL
```

不要求所有 Query 都通过 hydrated ORM graph。

## 禁止

```text
Active Record
ORM entities exposed from API
Domain methods depending on Session
lazy-loading across application boundary
repository .query() escape hatch
```

---

# 5. Decision TDG1-05 — PostgreSQL Driver

## 决议

```text
psycopg 3
```

Phase 1 使用同步 SQLAlchemy Session/Application Service。

## 原因

Phase 1 command volume 不是高并发网络服务瓶颈，先采用同步事务模型可以：

- 降低 UnitOfWork 复杂度；
- 降低开发人员误用 async Session 的概率；
- 简化 deterministic transaction boundary；
- CLI/API 共用相同 Application Service。

Phase 3 长任务/worker 并不要求 Phase 1 DB access 改为 async。

如果未来明确测出 HTTP DB 并发瓶颈，再通过 ADR 引入 async adapter，不修改 Domain/Application contracts。

---

# 6. Decision TDG1-06 — Pydantic

## 决议

```text
Pydantic 2.x
```

用途：

```text
HTTP DTO
CLI DTO where useful
ExecutionContext
read/write contract validation
configuration
```

Domain Entity 不要求继承 `BaseModel`。

Domain 可以使用：

```text
dataclass
plain Python class
value object
```

避免 Pydantic 成为 Domain framework dependency。

---

# 7. Decision TDG1-07 — FastAPI

## 决议

```text
FastAPI 0.141.x
Reference design patch: 0.141.1
```

## 角色

FastAPI 仅是：

```text
HTTP Adapter
```

不是 Application Framework/Core。

正确：

```text
FastAPI route
→ parse DTO
→ build ExecutionContext
→ call Application handler
→ map result/error
```

禁止：

```text
route
→ ORM
→ session.commit()
```

---

# 8. Decision TDG1-08 — CLI

## 决议

```text
Typer 0.27.x
Reference design patch: 0.27.1
```

CLI 和 HTTP：

```text
SHARE Application handlers
```

不得：

```text
HTTP logic implementation A
CLI logic implementation B
```

CLI 是 Phase 1 很重要的 reference adapter，因为它能证明 Core 不依赖 HTTP。

---

# 9. Decision TDG1-09 — Lint / Format / Type Check

## 决议

```text
Ruff
Pyright
```

Ruff 负责：

```text
lint
format
import hygiene
```

Pyright 负责静态类型。

不同时启用多个会大量重叠的 canonical formatter/linter：

```text
Black + isort + flake8 + Ruff
```

避免配置分叉。

## CI

最低：

```text
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
```

---

# 10. Decision TDG1-10 — ArtifactStore

这是 Final Architecture Review 后新增的关键基础设施。

## Port

```python
class ArtifactStore(Protocol):
    def put_verified(...): ...
    def open(...): ...
    def exists(...): ...
    def verify(...): ...
```

## Phase 1 Reference Backend

```text
ContentAddressedFilesystemArtifactStore
```

目录逻辑：

```text
artifact_root/
  sha256/
    ab/
      cd/
        abcdef...fullhash
```

## Identity

```text
Artifact byte identity = SHA-256
locator ≠ identity
```

## Put Contract

逻辑：

```text
stream input
→ write temp
→ compute sha256
→ compare expected hash if supplied
→ fsync/close
→ atomic rename to content-addressed path
→ immutable object
```

如果 hash 已存在：

```text
verify existing
→ idempotently reuse
```

禁止覆盖相同 hash path 的不同 bytes。

---

# 11. Decision TDG1-11 — ArtifactStore Future Compatibility

Phase 1 Core 只能依赖：

```text
ArtifactStore Port
```

Phase 2/3 deployment MAY 添加：

```text
S3CompatibleArtifactStore
MinIO
S3
other object storage
```

无需改：

```text
Artifact
ArtifactVersion
Run
Application Commands
```

`locator` 使用 URI-like scheme：

```text
cas+file://...
s3://bucket/key
```

但应用层不能根据字符串 scheme 编写业务规则。

---

# 12. Decision TDG1-12 — Database + Artifact Atomicity

PostgreSQL transaction 无法和 filesystem/S3 做真正 distributed transaction。

Phase 1 统一采用：

```text
store bytes first
→ verified immutable object
→ DB transaction registers ArtifactVersion
```

若 DB transaction 失败：

```text
unreferenced content-addressed bytes
```

允许由 garbage collection 后处理。

禁止：

```text
DB record commit
→ later try writing bytes
```

因为那会产生 canonical ArtifactVersion 指向不存在内容。

## GC

Phase 1 不要求自动 GC。

只保留后续工具接口：

```text
find unreferenced content hashes
```

---

# 13. Decision TDG1-13 — Development Deployment Profile

## Primary Phase 1 Profile

```text
DEV_LOCAL
```

组成：

```text
researchbase API/CLI
PostgreSQL 18
local content-addressed ArtifactStore
```

使用：

```text
Docker Compose
```

管理 PostgreSQL。

Application 本身 SHOULD 支持：

```text
host Python via uv
```

以改善开发/调试体验。

建议：

```text
docker compose up postgres
uv run fastapi dev ...
uv run researchbase ...
```

---

# 14. Decision TDG1-14 — Team Deployment Shape

Phase 1 不要求正式生产部署，但必须保持兼容：

```text
TEAM_SINGLE_NODE
```

未来组成：

```text
API process
PostgreSQL
S3-compatible ArtifactStore
```

Domain/Application 无变化。

---

# 15. Decision TDG1-15 — Container Strategy

Phase 1 MUST 提供：

```text
Dockerfile
docker-compose.yml / compose.yaml
```

但：

```text
containerization
≠ microservices
```

ResearchBase 仍是 modular monolith。

---

# 16. Decision TDG1-16 — Test Database

所有 Persistence/Migration/Constraint Integration Tests：

```text
REAL PostgreSQL
```

不得用 SQLite 替代。

允许：

```text
testcontainers
or
CI service container
```

PR-00 由 Tech Lead 从两者中选择唯一方式并写 ADR-0004；建议：

```text
CI service container
+
local Docker Compose
```

理由是简单、透明、少一层测试容器库抽象。

---

# 17. Decision TDG1-17 — Test Layers

```text
Unit
  no DB where possible

Integration
  PostgreSQL

Architecture
  import/schema/contracts

E2E
  Application Command/Query + PostgreSQL + ArtifactStore
```

Phase 1 E2E 不需要真实第三方网络服务。

---

# 18. Decision TDG1-18 — Migration

```text
Alembic
```

规则继承 Phase 1：

```text
every schema PR → migration
clean install → PASS
upgrade from previous revision → PASS
scientific history delete → forbidden
```

Migration 默认由 SQLAlchemy metadata 辅助生成，但 Developer MUST review DDL。

禁止 blind autogenerate commit。

---

# 19. Decision TDG1-19 — Repository / UnitOfWork

采用：

```text
Repository Ports
+
SQLAlchemy implementations
+
explicit UnitOfWork
```

每条 Application Command 一个 UoW/transaction。

Query 可使用独立 query service/read repository，不必强行走 Aggregate Repository。

---

# 20. Decision TDG1-20 — API Versioning

Phase 1：

```text
/v1/
```

但 version 含义是：

```text
public adapter compatibility
```

不是 Domain version。

Phase 2 不因为是 Phase 2 就机械改 `/v2`。

如果 API 仍 backward-compatible：

```text
continue /v1
```

只有真正 breaking public API 才升级 major route/API contract。

这覆盖 Phase 2 文档中 `/v2` 仅作为示例的歧义。

---

# 21. Decision TDG1-21 — Configuration

统一从 environment/config file 读取：

```text
DATABASE_URL
ARTIFACT_STORE_ROOT / ArtifactStore config
LOG_LEVEL
APPLICATION_ENV
```

使用 Pydantic Settings 或等价轻量 config adapter。

Secrets：

```text
environment / secret manager
```

不得进入：

```text
Artifact metadata
content hash material
Git
logs
```

---

# 22. Decision TDG1-22 — Logging

采用结构化 logging contract。

Phase 1 不强制特定 SaaS observability。

最低字段：

```text
timestamp
level
request_id
correlation_id
command_name
actor_id
project_id
target_id
result
error_code
duration_ms
```

本地可输出 JSON 或 human-readable console；生产 profile SHOULD JSON。

---

# 23. Decision TDG1-23 — Authentication Profile

Phase 1：

```text
TRUSTED_LOCAL_ACTOR_PROFILE
```

Core 要求：

```text
ExecutionContext.actor_id
```

但 Phase 1 不建设 OAuth/OIDC/IAM。

开发环境提供：

```text
configured local/test Actor
```

API adapter 可以通过开发 header/session 注入 actor，但必须显式标记 development-only。

Phase 2 引入：

```text
ProjectMembership / ProjectRoleAssignment
```

真正多用户 auth provider 后续独立 Adapter/Extension。

---

# 24. Decision TDG1-24 — UUID

Domain/API：

```text
UUID
```

推荐新 ID：

```text
UUIDv7
```

若标准库/runtime便利性不足，可使用经过审核的轻量库；不得因此退回自增 integer 作为 canonical external identity。

DB：

```text
uuid
```

---

# 25. Decision TDG1-25 — Hash Scheme

正式冻结：

```text
sha256-cjson-v1
```

二进制：

```text
SHA-256(raw bytes)
```

Structured material：

```text
canonical JSON v1
→ UTF-8
→ SHA-256
```

必须有 test vectors。

将来新 canonicalization：

```text
sha256-cjson-v2
```

不能静默改旧 hash。

---

# 26. Dependency Pinning Policy

Git lockfile pin exact resolved versions。

`pyproject.toml` 建议使用 compatible ranges，例如：

```text
python >=3.12,<3.13

sqlalchemy >=2.0.52,<2.1
fastapi >=0.141.1,<0.142
typer >=0.27.1,<0.28

pydantic >=2,<3
psycopg >=3,<4
alembic >=1,<2
pytest >=8,<10
```

实际 PR-00 应根据当天 resolver 和 compatibility test 生成 lockfile。

规则：

```text
lockfile = reproducible build source
pyproject range = supported compatibility intent
```

Security patch update：

```text
dependency PR + CI
```

---

# 27. Dependency Policy

新增 runtime dependency 必须回答：

```text
why standard library/current dependency insufficient?
license?
maintenance?
security?
does it leak into Domain?
```

Phase 1 不引入：

```text
LangGraph
Celery
Redis
Kafka
DVC
MLflow
STORM
PaperQA2
OpenHands
```

这些属于后续 Phase/Adapter。

---

# 28. Source Layout

沿用：

```text
src/researchbase/
```

测试：

```text
tests/
  unit/
  integration/
  architecture/
  e2e/
```

不使用 giant `utils.py`。

共享通用 primitive 进入：

```text
foundation/
```

但 `foundation` 不得成为业务杂物箱。

---

# 29. Architecture Enforcement Tooling

PR-01 之前至少实现自定义 pytest/AST 检查：

```text
domain does not import SQLAlchemy
domain does not import FastAPI/Typer
API does not import persistence models
foundation does not import business modules
```

Phase 1 不强制购买/引入商业 architecture tooling。

---

# 30. Reference Local Topology

```text
┌────────────────────┐
│ Developer / Codex  │
└─────────┬──────────┘
          │
      CLI / HTTP
          │
┌─────────▼──────────┐
│ ResearchBase       │
│ Modular Monolith   │
└──────┬───────┬─────┘
       │       │
       │       └──────────────┐
       │                      │
┌──────▼──────┐       ┌──────▼──────────┐
│ PostgreSQL  │       │ ArtifactStore   │
│ 18.x        │       │ CAS filesystem  │
└─────────────┘       └─────────────────┘
```

无：

```text
Redis
queue
microservice
vector DB
agent framework
```

---

# 31. Reference Repository Bootstrap Files

PR-00 至少：

```text
pyproject.toml
uv.lock

README.md
.env.example

compose.yaml
Dockerfile

alembic.ini
migrations/

src/researchbase/
tests/

.github/workflows/ci.yml
```

如果仓库不使用 GitHub，可替换 CI adapter，但 checks contract 不变。

---

# 32. CI Gate

Phase 1 PR：

```text
ruff format --check
ruff check
pyright
pytest unit
pytest architecture
pytest integration with PostgreSQL
alembic upgrade head from empty DB
```

涉及 migration：

```text
upgrade previous → head
```

涉及 Artifact：

```text
ArtifactStore integrity test
```

PR-17/18：

```text
full E2E
```

---

# 33. ADR Bootstrap

在 PR-00 创建：

```text
docs/architecture/adr/
```

至少登记：

```text
ADR-0001 Python 3.12 / uv
ADR-0002 PostgreSQL 18
ADR-0003 SQLAlchemy 2.0 + sync psycopg
ADR-0004 DEV_LOCAL / Docker Compose PostgreSQL
ADR-0005 Content-addressed ArtifactStore
ADR-0006 FastAPI + Typer adapters
ADR-0007 Ruff + Pyright
```

TDG-1 是这些 ADR 的上位决议，可将其转成简化 ADR 文件。

---

# 34. PR-00 Acceptance Patch

原 Phase 1 PR-00 Gate 更新为：

```text
[ ] Python 3.12 environment via uv
[ ] lockfile committed
[ ] PostgreSQL 18 service starts
[ ] SQLAlchemy 2.0 + psycopg connection smoke
[ ] Alembic empty upgrade pass
[ ] FastAPI smoke app
[ ] Typer smoke CLI
[ ] local ArtifactStore put/open/verify smoke
[ ] Ruff pass
[ ] Pyright pass
[ ] pytest pass
[ ] architecture skeleton pass
[ ] ADR-0001..0007 created
```

仍然：

```text
NO BUSINESS DOMAIN IMPLEMENTATION IN PR-00
```

---

# 35. Phase 1 Implementation Context Pack

每次给 Codex/开发人员 PR 指令时，必须同时提供：

```text
1. System Architecture v1.2
2. Final Correction Addendum v1.0
3. Global Schema Registry v1.0
4. Cross-Phase Contract v1.0
5. Phase 1 Development Spec v1.1
6. TDG-1 v1.0
7. target PR scope
```

这样避免开发者只看到数据库 ticket 而丢失架构语义。

---

# 36. TDG-1 Forbidden Deviations

未经 ADR/Tech Lead 批准，Phase 1 不得：

```text
switch PostgreSQL to SQLite/MySQL
switch SQLAlchemy to Django ORM/SQLModel
replace Repository/UoW with Active Record
switch sync core to async DB architecture
replace ArtifactStore with arbitrary mutable directory paths
introduce Redis/queue
introduce Agent framework
introduce microservices
introduce vendor-specific research schema
replace FastAPI/Typer application boundary
```

---

# 37. Upgrade Policy

## Patch/minor within approved compatibility window

允许：

```text
dependency PR
→ release notes
→ full CI
→ lockfile update
```

## Major/runtime architectural dependency

例如：

```text
SQLAlchemy 3
Pydantic 3
PostgreSQL 19
Python 3.13 baseline
async database architecture
```

需要：

```text
ADR
compatibility test
migration assessment
```

---

# 38. Why This Stack Fits ResearchBase

ResearchBase Phase 1 的主要需求：

```text
strong relational constraints
transactions
immutable/version semantics
JSONB for bounded structured metadata
typed Python domain model
clear Application boundary
CLI-first usability
low operational complexity
```

因此：

```text
Python + PostgreSQL + SQLAlchemy
```

比：

```text
microservices + graph DB + event store + queue + vector DB
```

更适合当前阶段。

后面的 Literature、Agent、Memory 可以扩展 adapter/infrastructure，而不污染 Core。

---

# 39. TDG-1 Final Decision Matrix

| Area | Decision | Stability |
|---|---|---|
| Python | 3.12.x | FROZEN for Phase 1 |
| Package manager | uv | FROZEN |
| DB | PostgreSQL 18.x | FROZEN major |
| ORM | SQLAlchemy 2.0.x | FROZEN major line |
| Driver | psycopg 3 | FROZEN |
| Migration | Alembic | FROZEN |
| DTO | Pydantic 2.x | FROZEN major |
| HTTP | FastAPI 0.141.x | FROZEN minor line for bootstrap |
| CLI | Typer 0.27.x | FROZEN minor line for bootstrap |
| Lint/Format | Ruff | FROZEN |
| Type checker | Pyright | FROZEN |
| ArtifactStore | CAS filesystem via port | FROZEN Phase 1 reference |
| Deployment | DEV_LOCAL | FROZEN initial profile |
| Containers | Docker Compose | FROZEN dev DB profile |
| Application model | Modular monolith | FROZEN |
| DB I/O | synchronous | FROZEN Phase 1 |
| Integration test DB | real PostgreSQL | FROZEN |

---

# 40. Implementation Start Gate Result

Final Architecture Review 要求：

```text
[✓] Final Correction Addendum accepted
[✓] Global Schema Registry created
[✓] TDG-1 completed
[✓] ArtifactStore contract selected
[✓] Promotion provenance patch accepted
```

因此设计层面的条件已满足：

```text
P0 OPEN = 0
ARCHITECTURE EXPLORATION = CLOSED
ALL PHASE DESIGNS = COMPLETE
CROSS-PHASE CONTRACT = COMPLETE
TDG-1 = COMPLETE
```

最终状态：

```text
SYSTEM_DESIGN_STATUS = FROZEN
IMPLEMENTATION_GO_PHASE1 = TRUE
```

执行边界：

> **GO 只授权进入 Phase 1 PR-00，不授权一次性开发 Phase 1，更不授权提前实现 Phase 2–4。**

PR-00 完成后必须 Review/Gate，再进入 PR-01。
