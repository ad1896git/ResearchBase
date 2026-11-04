# 快速上手：常用命令速查

适用于本地单用户模式。下文用 `rb` 代指 `researchbase` 命令（两者都可在任何目录下直接使用）。

- 编号（#1、#2…）是项目内按创建顺序排的短编号，可直接用于命令。
- 也可以用 UUID 前缀，或文献标题里能唯一区分的一段文字代替编号。
- 不指定 `--project-id` 时，命令使用当前项目（`rb project use` 设置）。
- 每一步只给出一条主要命令，并说明相关的后续命令。

## 0. 安装（只需做一次）

在仓库目录里，用可编辑方式安装成全局命令：

```bash
cd <仓库目录>
uv tool install --editable . --force
ln -sfn researchbase ~/.local/bin/rb
```

- 安装后，`researchbase` 和 `rb` 在任何目录下都可以直接运行。装完新开一个终端窗口，运行 `rb --help` 应显示帮助。
- 可编辑安装指向仓库目录本身：以后在该目录里更新代码（`git pull`、切换分支）后，命令立即使用新代码，不需要重新安装。若修改了数据库结构（新的迁移），再运行一次 `uv run alembic upgrade head`。
- 如果移动或删除了仓库目录，需要在新位置重新运行上面的两条命令。
- 命令默认连接本机的 `researchbase` 数据库，不需要设置环境变量。

## 1. 建项目

```bash
rb project create --name "午睡与记忆"
```

命令会输出 `project_id=…`。随后运行 `rb project use <项目ID>` 设为当前项目。第一次使用前，先运行一次 `rb local init`，再运行 `rb local bootstrap --display-name "<你的名字>" --project-name "<项目名>"`。

## 2. 研究问题

```bash
rb question add "午睡是否改善次日记忆" --scope "成年人午睡" --rationale "测试午睡与记忆"
```

新建并冻结一个研究问题，`--scope` 和 `--rationale` 可省略。

## 3. 假设

```bash
rb hypothesis add "午睡20分钟组次日测验平均分高于对照组" --question 1 --direction 高于 --success "均值差>0"
```

`--question` 指定所属的研究问题（用编号）。

## 4. 加文献

```bash
rb paper add ~/Research/papers/nap-study.pdf --title "小睡与记忆（示例）"
```

支持 PDF、`.txt`、`.md` 和 JATS XML。PDF 会提取全文，并把识别出的 DOI 写入来源记录；`--title` 可省略，默认用 PDF 自带标题或文件名。

## 5. 摘录证据

```bash
rb evidence add --paper 1 --quote "午睡20分钟组（n=40）的次日测验平均分高于对照组"
```

`--quote` 必须逐字复制原文（标点和空格也要一致），否则会被拒绝并提示原因。

## 6. 实验和结果

```bash
rb experiment add "午睡20分钟对照" --hypothesis 1 --objective "比较午睡组与对照组" --protocol "午睡组20分钟，对照组静坐" --metrics "次日测验平均分"
```

依次还需要：`rb metric add "次日测验平均分" --unit 分`，`rb run add --experiment <实验编号>`，`rb run begin <运行编号>`，`rb run end <运行编号> --outcome succeeded`，最后 `rb result add --run <运行编号> --metric <度量编号> --value 19.0 --unit 分`。

## 7. 结论

```bash
rb conclusion add "午睡可能改善次日记忆" --scope "成年人" --qualification "样本量较小"
```

新建结论。`--qualification` 写明限定条件，可省略。

## 8. 关联证据

```bash
rb claim link-evidence --claim 1 --evidence 1 --relation SUPPORTS --note "文献中的对照组结果"
```

`SUPPORTS` 要求该证据已核验。先运行 `rb evidence verify 1 --basis "已对照原文核对引文"`（个人模式可本人核验，导出时会标注“本人核验”）。也可以用 `--measurement <结果编号>` 关联本项目的测量结果。

## 9. 更正

```bash
rb correct --conclusion 1 --assertion "午睡可能改善次日记忆（样本量小，需重复验证）" --reason "原结论未写样本量限制"
```

追加一条更正记录，原结论保留；`--result <编号>` 可更正结果，`--type` 可指定类型（默认 factual）。导出的 Markdown 会在对应结论下显示更正，并在“更正记录”一节列出全部更正。

## 10. 搜索

```bash
rb search 午睡
```

在研究问题、假设、实验、结论和文献中按关键词查找，结果保留短编号。

## 11. 导出

```bash
rb export --out ~/Research/exports/nap-study.md
```

把当前项目导出为 Markdown：问题、假设、实验、结果、文献与引文、结论及其证据关联。导出的编号与终端命令通用。

## 12. 扫描文献文件夹

```bash
rb folder scan ~/Research/papers
```

默认文件夹是 `~/Research/papers`，可用环境变量 `RESEARCHBASE_PAPERS_DIR` 修改，也可以直接给出路径。扫描会记录新增、移动、内容改变、缺失和重复文件，并把新出现的 PDF、`.txt`、`.md` 登记为文献（同一 DOI 已登记的不重复登记）。文件本身不移动、不改名。

从 Zotero 等工具导出的 BibTeX 或 RIS 文件可以批量导入，按 DOI 或标题匹配文件夹中的 PDF，以导出文件的元数据为准：

```bash
rb folder import-refs ~/Research/library.bib
```

已登记的文献如果元数据不同，会追加一条更正版本，原版本保留。单篇文献的元数据也可以直接更正：`rb paper correct 1 --venue "期刊全名" --reason "补充期刊名"`。联网时 `rb paper enrich` 会用 Crossref 补全已登记文献中为空的字段（不覆盖已有内容）。

---

遇到错误时，终端会给出中文原因和修改建议；加 `--verbose` 可看到具体字段。
