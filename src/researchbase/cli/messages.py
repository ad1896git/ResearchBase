"""Chinese, human-facing error messages for the terminal CLI.

The machine-readable error code and original English message are kept in
``--json`` output and under ``--verbose``; the default terminal output uses the
text here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Explanation:
    title: str
    hint: str


_BY_CODE: dict[str, Explanation] = {
    "AUTHENTICATION_REQUIRED": Explanation(
        "本地身份未建立",
        "先运行 `researchbase local init`，再运行 `researchbase local bootstrap`，"
        "并提供 --display-name 和 --project-name。",
    ),
    "FORBIDDEN": Explanation(
        "没有权限执行此操作",
        "本地模式下只能以当前系统用户操作，请去掉 --actor-id。",
    ),
    "NOT_FOUND": Explanation(
        "找不到对应记录",
        "检查 ID 是否正确；可以先用列表命令查找。",
    ),
    "VALIDATION_ERROR": Explanation(
        "输入内容不符合要求",
        "按提示修改参数后重试；加 --verbose 可查看具体字段。",
    ),
    "IDENTIFIER_INVALID": Explanation(
        "ID 格式不正确",
        "使用完整 UUID，或能唯一匹配的前缀。",
    ),
    "VERSION_NOT_FROZEN": Explanation(
        "该版本尚未冻结",
        "先冻结它（例如 `hypothesis-freeze`），再引用。",
    ),
    "FROZEN_REFERENCE_REQUIRED": Explanation(
        "需要引用已冻结的版本",
        "先冻结被引用的研究问题、假设或实验设计，再继续。",
    ),
    "IMMUTABLE_RECORD": Explanation(
        "已冻结的记录不能直接修改",
        "用更正记录追加修改，旧记录会保留。",
    ),
    "SOURCE_VERSION_NOT_FOUND": Explanation(
        "找不到冻结的文献来源版本",
        "先登记并冻结该文献的来源信息，再录入证据。",
    ),
    "SOURCE_NOT_FOUND": Explanation(
        "找不到文献来源",
        "先导入或登记该文献。",
    ),
    "DUPLICATE_CONTENT": Explanation(
        "内容已存在",
        "同样的内容已经登记过，直接使用已有记录即可。",
    ),
    "CONCURRENT_MODIFICATION": Explanation(
        "记录在你操作期间被修改了",
        "重新读取最新版本后再操作。",
    ),
    "INVALID_STATE_TRANSITION": Explanation(
        "当前状态不允许这样做",
        "先查看记录的当前状态，再选择允许的操作。",
    ),
    "REFERENTIAL_INTEGRITY_ERROR": Explanation(
        "引用的记录不存在或不属于此项目",
        "检查 --project-id 以及被引用的 ID 是否属于同一项目。",
    ),
    "INTERNAL_ERROR": Explanation(
        "程序内部错误",
        "加 --verbose 查看详细信息，并把输出反馈给开发者。",
    ),
}

_DEFAULT = Explanation(
    "操作失败",
    "加 --verbose 查看详细信息。",
)


def explain(code: str) -> Explanation:
    return _BY_CODE.get(code, _DEFAULT)
