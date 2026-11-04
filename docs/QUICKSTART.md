# 快速上手：常用命令速查

适用于本地单用户模式。下文用 `rb` 代指 `researchbase` 命令，可在 shell 里设置 `alias rb=researchbase`。

- 编号（#1、#2…）是项目内按创建顺序排的短编号，可直接用于命令。
- 也可以用 UUID 前缀，或文献标题里能唯一区分的一段文字代替编号。
- 不指定 `--project-id` 时，命令使用当前项目（`rb project use` 设置）。
- 每一步只给出一条主要命令，并说明相关的后续命令。

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

## 9. 搜索

```bash
rb search 午睡
```

在研究问题、假设、实验、结论和文献中按关键词查找，结果保留短编号。

## 10. 导出

```bash
rb export --out ~/Research/exports/nap-study.md
```

把当前项目导出为 Markdown：问题、假设、实验、结果、文献与引文、结论及其证据关联。导出的编号与终端命令通用。

## 11. 扫描文献文件夹

```bash
rb folder scan ~/Research/papers
```

记录文件夹中的新增、移动、内容改变、缺失和重复文件，只记录路径和哈希，不移动、不改名、不修改 PDF。`rb folder status ~/Research/papers` 只读显示最近一次扫描的状态。注意：扫描目前只记录观察结果，不会把新 PDF 登记为文献，需要登记时仍用 `rb paper add`。

---

遇到错误时，终端会给出中文原因和修改建议；加 `--verbose` 可看到具体字段。
