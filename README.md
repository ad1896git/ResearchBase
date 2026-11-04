# ResearchBase 使用说明

ResearchBase 是一个本地单用户的科研记录工具。它帮你管理研究问题、假设、文献、实验、结果和结论，并记录每一条结论依据哪些文献和数据。所有记录都保存在本机的 PostgreSQL 数据库里，全文文件保存在本机的文件存储中。

本文面向日常使用者，说明如何安装、如何录入和查询内容、如何备份和检查数据。命令的更多示例见 [docs/QUICKSTART.md](docs/QUICKSTART.md)。

## 目录

1. [基本概念](#1-基本概念)
2. [安装](#2-安装)
3. [第一次使用](#3-第一次使用)
4. [日常工作流程](#4-日常工作流程)
5. [命令速查](#5-命令速查)
6. [文献文件夹与全文](#6-文献文件夹与全文)
7. [检查与备份](#7-检查与备份)
8. [配置项](#8-配置项)
9. [数据存放位置](#9-数据存放位置)
10. [常见问题](#10-常见问题)
11. [开发者信息](#11-开发者信息)

---

## 1. 基本概念

| 概念 | 含义 | 命令组 |
| --- | --- | --- |
| 项目（project） | 一组相关研究的容器。所有其他记录都属于某个项目。 | `project` |
| 研究问题（question） | 你想回答的问题。 | `question` |
| 假设（hypothesis） | 对研究问题的可检验陈述。 | `hypothesis` |
| 文献（paper） | 一篇论文或一份资料，保存其全文并冻结为一个版本。 | `paper`、`folder` |
| 证据（evidence） | 从文献全文中逐字摘录的一段引文，可以标记为已核验。 | `evidence` |
| 实验（experiment） | 为检验假设而设计的方案，包含方法和度量。 | `experiment`、`metric` |
| 运行（run） | 实验的一次执行。 | `run` |
| 结果（result） | 运行得到的测量值。 | `result` |
| 结论（conclusion） | 你基于证据和结果得出的判断。 | `conclusion` |
| 关联（claim link） | 把证据或结果关联到结论，并注明支持或反对等关系。 | `claim` |
| 更正（correct） | 对结论或结果的修改。原内容保留，更正以新记录追加。 | `correct` |

核心规则：

- **历史不被覆盖。** 修改已有结论或结果时，用 `rb correct` 追加更正，原记录保留并在导出中同时显示。文献元数据的修改同样以追加方式记录（`rb paper correct`、`rb folder import-refs`）。
- **引文必须逐字。** `rb evidence add --quote` 中的文字必须与原文完全一致（标点和空格也要一致），否则会被拒绝并给出原因。
- **编号即引用。** 每类记录在项目内都有按创建顺序排列的短编号（#1、#2 …），命令中可以直接使用。也可以用 UUID 前缀，或文献标题中能唯一区分的一段文字。

## 2. 安装

环境要求：

- macOS 或 Linux
- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL 18（数据库）

在仓库目录中执行：

```bash
cd <仓库目录>
uv sync --locked --group dev
uv tool install --editable . --force
ln -sfn researchbase ~/.local/bin/rb
```

- 安装完成后，`researchbase` 和 `rb` 两个命令在任何目录下都可以直接使用。新开一个终端窗口后运行 `rb --help` 应显示帮助。
- 可编辑安装指向仓库本身。以后在仓库中 `git pull` 或切换分支，命令会立即使用新代码，无需重新安装。
- 如果仓库目录被移动或删除，需要在新位置重新运行上面的命令。

数据库：命令默认连接本机的 `researchbase` 数据库。如果你的数据库不在默认位置，设置环境变量 `DATABASE_URL`（见[配置项](#8-配置项)）。第一次使用前，先执行数据库迁移：

```bash
uv run alembic upgrade head
```

## 3. 第一次使用

### 3.1 创建本地身份

```bash
rb local init
rb local bootstrap --display-name "你的名字" --project-name "项目名"
rb local whoami
```

- `local init` 在系统账户目录下创建本地身份目录（`~/.researchbase-local`，权限 0700）。这个目录保存本地凭据，不要复制到其他机器或其他账户。
- `local bootstrap` 只能在空数据库上执行一次，它会创建你的身份和第一个项目。
- **每日备份不包含本地身份目录。** 请另外把 `~/.researchbase-local` 安全地保存一份（例如加密的外置存储）。如果它丢失，已有数据无法通过命令重新关联到你的身份。

### 3.2 创建项目并设为当前项目

```bash
rb project create --name "午睡与记忆"
rb project use 1
rb project current
```

不指定 `--project-id` 时，命令都作用于当前项目。

## 4. 日常工作流程

下面以一个示例研究"午睡是否改善次日记忆"为例，按顺序说明。

### 4.1 录入研究问题和假设

```bash
rb question add "午睡是否改善次日记忆" --scope "成年人午睡" --rationale "测试午睡与记忆"
rb hypothesis add "午睡20分钟组次日测验平均分高于对照组" --question 1 --direction 高于 --success "均值差>0"
```

`--scope`、`--rationale` 等参数可以省略。

### 4.2 加入文献并摘录证据

```bash
rb paper add ~/Research/papers/nap-study.pdf --title "小睡与记忆（示例）"
rb evidence add --paper 1 --quote "午睡20分钟组（n=40）的次日测验平均分高于对照组"
rb evidence verify 1 --basis "已对照原文核对引文"
```

- 支持 PDF、`.txt`、`.md` 和 JATS XML。PDF 会提取全文，并把识别出的 DOI 记入来源。
- `--title` 可省略，默认使用 PDF 中的标题或文件名。
- `evidence verify` 记录你已对照原文核对过该引文。个人模式下可以本人核验，导出时会标注"本人核验"。

### 4.3 设计实验、运行并记录结果

```bash
rb experiment add "午睡20分钟对照" --hypothesis 1 --objective "比较午睡组与对照组" --protocol "午睡组20分钟，对照组静坐" --metrics "次日测验平均分"
rb metric add "次日测验平均分" --unit 分
rb run add --experiment 1
rb run begin 1
rb run end 1 --outcome succeeded
rb result add --run 1 --metric 1 --value 19.0 --unit 分
```

- `run end --outcome` 可选 `succeeded`、`failed`、`cancelled`。
- 运行开始后再记录结果，结果与运行绑定。

### 4.4 形成结论并关联证据

```bash
rb conclusion add "午睡可能改善次日记忆" --scope "成年人" --qualification "样本量较小"
rb claim link-evidence --claim 1 --evidence 1 --relation SUPPORTS --note "文献中的对照组结果"
```

- `--relation SUPPORTS` 要求该证据已经核验（见 4.2）。
- 也可以用 `--measurement <结果编号>` 把本项目的测量结果关联到结论。

### 4.5 修改已有结论

```bash
rb correct --conclusion 1 --assertion "午睡可能改善次日记忆（样本量小，需重复验证）" --reason "原结论未写样本量限制"
```

- 原结论保留，新的更正记录追加在后面。
- `--result <编号>` 可更正结果。`--type` 指定更正类型，默认为 `factual`。

### 4.6 搜索与导出

```bash
rb search 午睡
rb export --out ~/Research/exports/nap-study.md
```

- `search` 在研究问题、假设、实验、结论和文献中按关键词查找，结果保留短编号，可以直接用于后续命令。
- `export` 把当前项目导出为 Markdown，包含问题、假设、实验、结果、文献与引文、结论及其证据关联，以及“更正记录”一节。

## 5. 命令速查

| 命令 | 用途 |
| --- | --- |
| `rb project create / use / current` | 创建项目、设置当前项目、查看当前项目 |
| `rb question add` | 新建研究问题 |
| `rb hypothesis add` | 新建假设 |
| `rb paper add / list / correct / enrich` | 加入文献、列出、更正元数据、用 Crossref 补全字段 |
| `rb folder scan / status / import-refs` | 扫描文献文件夹、查看状态、导入 BibTeX/RIS |
| `rb evidence add / verify / list` | 摘录逐字引文、核验、列出 |
| `rb experiment add` | 新建实验 |
| `rb metric add` | 新建度量 |
| `rb run add / begin / end / add-dataset / add-artifact / list / provenance` | 运行的创建、开始、结束、关联数据与产物、查询 |
| `rb result add` | 记录测量结果 |
| `rb conclusion add` | 新建结论 |
| `rb claim link-evidence` | 把证据或结果关联到结论 |
| `rb correct` | 追加对结论或结果的更正 |
| `rb search` | 按关键词搜索 |
| `rb export` | 导出 Markdown |
| `rb doctor` | 检查全文文件是否完整（见第 7 节） |
| `rb local init / bootstrap / whoami` | 本地身份管理 |

每个命令都可以加 `--help` 查看完整参数，例如 `rb run --help`、`rb folder scan --help`。

全局选项 `--verbose`（或 `-v`）显示详细日志，默认隐藏。

命令出错时，终端会给出中文原因和修改建议。

## 6. 文献文件夹与全文

### 6.1 扫描文献文件夹

```bash
rb folder scan ~/Research/papers
rb folder status
```

- 默认文件夹是 `~/Research/papers`，可以通过环境变量 `RESEARCHBASE_PAPERS_DIR` 修改，也可以直接给出路径。
- 扫描会记录新增、移动、内容改变、缺失和重复的文件，并把新的 PDF、`.txt`、`.md` 登记为文献。同一 DOI 已登记的不会重复登记。
- 扫描不移动、不改名、不删除你的文件。

### 6.2 导入 BibTeX 或 RIS

从 Zotero 等工具导出的文献清单可以批量导入，按 DOI 或标题与文件夹中的 PDF 匹配，并以导出文件的元数据为准：

```bash
rb folder import-refs ~/Research/library.bib
```

- 已登记的文献如果元数据不同，会追加一条新版本，原版本保留。
- 单篇文献的元数据可以直接更正：`rb paper correct 1 --venue "期刊全名" --reason "补充期刊名"`。

### 6.3 补全元数据

```bash
rb paper enrich
```

联网时，用 Crossref 补全已登记文献中为空的字段，不覆盖已有内容。

## 7. 检查与备份

### 7.1 `rb doctor`：全文完整性检查

```bash
rb doctor
rb doctor --record
```

`rb doctor` 检查数据库中的每一条全文记录（全部全文版本）：

- 文件是否存在；
- 文件内容的 SHA-256 哈希是否与记录一致；
- 文件大小是否与记录一致。

它只读，不修改任何数据。全部正常时退出码为 0；发现问题时逐条列出并以退出码 1 结束。

`--record` 会把结果写入状态文件。之后运行任意 `rb` 命令时，终端会先显示一行提示，直到下一次检查通过为止。

### 7.2 每日自动备份

macOS 上通过 launchd 任务 `com.researchbase.db-backup` 每天 03:30 运行备份，备份内容包括：

- 数据库（`pg_dump` 导出，并校验 `pg_restore --list`）；
- 全文存储目录（打包为 tar.gz，并校验）。

备份后会自动运行 `rb doctor --record`，结果写入 `~/ResearchBase-backups/logs/doctor.log`。备份保留最近 14 份。

备份的文件位于 `~/ResearchBase-backups/`，与仓库分开。

### 7.3 恢复

恢复步骤、需要同时恢复数据库与全文的原因，以及恢复演练记录，见 [ops/backup/RESTORE.md](ops/backup/RESTORE.md)。

**恢复前请注意：**
- 数据库与全文必须成对恢复；只恢复数据库会导致全文记录找不到文件。
- 恢复后运行一次 `rb doctor`，确认全部正常。

### 7.4 修改备份

备份脚本、恢复说明和 launchd 配置都保存在 `ops/backup/`。修改后走 PR，合并后运行：

```bash
ops/backup/deploy.sh
```

部署脚本会把仓库中的版本复制到 `~/ResearchBase-backups/` 和 `~/Library/LaunchAgents/`，并重新加载任务。不要直接修改 `~/ResearchBase-backups/bin/` 下的副本。

## 8. 配置项

| 环境变量 | 作用 | 默认值 |
| --- | --- | --- |
| `DATABASE_URL` | 数据库连接串 | 本机 `researchbase` 数据库 |
| `ARTIFACT_STORE_ROOT` | 全文存储目录 | `~/.researchbase/artifacts` |
| `RESEARCHBASE_PAPERS_DIR` | 默认文献文件夹 | `~/Research/papers` |
| `RESEARCHBASE_LOCAL_ROOT` | 本地身份目录 | `~/.researchbase-local` |
| `RESEARCHBASE_DOCTOR_STATUS` | `doctor --record` 的状态文件 | `~/.researchbase/doctor-status.json` |
| `OPENALEX_API_KEY` | OpenAlex 检索密钥（可选） | 未设置 |

数据库地址的写法示例：

```bash
export DATABASE_URL=postgresql+psycopg://researchbase:<密码>@localhost:5432/researchbase
```

密码不要写入仓库。把它放在 `~/.pgpass` 或系统密钥管理中。

## 9. 数据存放位置

| 内容 | 位置 |
| --- | --- |
| 所有结构化记录（项目、问题、证据、结论等） | PostgreSQL 数据库 `researchbase` |
| 全文文件（按内容哈希存放） | `~/.researchbase/artifacts/sha256/...` |
| 本地身份凭据 | `~/.researchbase-local/`（不在每日备份中，需单独保存） |
| 你的 PDF 原件 | 你自己的文件夹（ResearchBase 不移动、不改名） |
| 每日备份 | `~/ResearchBase-backups/` |
| 试用或临时数据库 | 不纳入备份，由你自己决定是否保留 |

全文文件和数据库必须一起备份、一起恢复。

## 10. 常见问题

**`rb: command not found`**
重新运行安装命令，并确认 `~/.local/bin` 在 `PATH` 中。新开一个终端窗口。

**`rb` 提示“全文完整性检查发现问题”**
运行 `rb doctor` 查看具体记录。常见原因是全文文件被移动、删除或损坏。查到原因后，从备份恢复对应文件，再运行 `rb doctor` 确认。

**`evidence add` 提示引文不匹配**
`--quote` 必须与原文逐字一致。从 PDF 复制时，换行、连字符和空格可能与原文不同，请对照原文修正后重试。

**`claim link-evidence --relation SUPPORTS` 被拒绝**
该证据尚未核验。先运行 `rb evidence verify <编号> --basis "..."`。

**想修改已有结论**
不要试图覆盖。使用 `rb correct` 追加更正。

**`rb local bootstrap` 报错说数据库非空**
bootstrap 只能在空数据库上执行。如果你已经有数据，直接使用 `rb local whoami` 确认身份即可。

## 11. 开发者信息

### 11.1 技术栈

Python 3.12、uv、PostgreSQL 18、SQLAlchemy、Alembic、Typer（CLI）、FastAPI（API 适配器）、pytest、ruff、pyright。

### 11.2 分层

```text
CLI / API → Application（一条命令 = 一个事务）→ Ports → Domain / Foundation
                                                ↑
                                          Persistence（SQLAlchemy + PostgreSQL）
```

- CLI 命令模块不得直接导入 SQLAlchemy 或 persistence 层，只能通过 Application 服务。架构测试会检查这一点。
- 领域对象不依赖 SQLAlchemy、FastAPI、Typer。
- 全文存储通过内容寻址的文件系统实现（`ContentAddressedFilesystemArtifactStore`）。

### 11.3 目录结构

```text
src/researchbase/        代码：foundation、domain、application、persistence、adapters、cli
migrations/              Alembic 数据库迁移
tests/                   单元、集成、架构和端到端测试
docs/                    用户文档（QUICKSTART）与架构文档（architecture/）
ops/backup/              备份脚本、恢复说明和 launchd 配置
scripts/                 验证与工具脚本
```

### 11.4 开发流程

```bash
uv sync --locked --group dev
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest tests/unit tests/architecture
```

集成测试需要 PostgreSQL 18：

```bash
export DATABASE_URL=postgresql+psycopg://researchbase:<密码>@localhost:5432/researchbase
export RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:<密码>@localhost:5432/postgres
uv run pytest tests/integration
```

- `RB_TEST_ADMIN_URL` 指向一个可以创建和删除测试数据库的管理员连接。部分测试套件需要它，未设置时这些测试会失败，而不是静默通过。
- 单元测试不读取本地身份目录（`tests/unit/conftest.py` 已将其指向一个不存在的路径）。

修改后按以下流程：

1. 在分支上开发，本地运行相关测试。
2. 推送并开 PR 到 `main`。
3. CI 的全部必需检查通过后，用 `gh pr merge --auto --squash` 自动合并。
4. 涉及数据库结构变更（迁移）的 PR 不使用自动合并，需要先做备份并人工确认。

CI 对 `main` 的每次推送都会运行。

### 11.5 进一步阅读

- [docs/QUICKSTART.md](docs/QUICKSTART.md)：常用命令的逐步示例。
- [ops/backup/README.md](ops/backup/README.md) 与 [ops/backup/RESTORE.md](ops/backup/RESTORE.md)：备份与恢复。
- [docs/architecture/](docs/architecture/)：架构规范。`AGENTS.md` 记录仓库的工作规则。

以前的 README 中记录的 Phase 1/2/3 验收状态、冻结标签和证据包，现在保存在 git 历史中（提交 `328143d` 及之前的 README.md），不再作为使用说明的内容。
