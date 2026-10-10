"""Bounded manual localization in exact UTF-8 text or JATS XML bytes.

Version 1: XML paragraphs are document-order p elements, itertext concatenation;
text paragraphs are literal double-newline-separated blocks. Offsets count Unicode
codepoints, end exclusive, without NFC or whitespace normalization. No OCR/inference.
"""

from __future__ import annotations

import re
from xml.etree import ElementTree

from researchbase.foundation.errors import ErrorCode, ResearchBaseError

MAX_BYTES = 8 * 1024 * 1024


def _invalid(message):
    return ResearchBaseError(ErrorCode.VALIDATION_ERROR, message)


def paragraphs(content: bytes, mime: str) -> tuple[str, ...]:
    if not content or len(content) > MAX_BYTES:
        raise _invalid("missing or oversized source content")
    try:
        value = content.decode("utf-8", errors="strict")
        if "\x00" in value:
            raise ValueError("NUL is not UTF-8 document text")
        if mime == "text/plain":
            result = tuple(value.split("\n\n"))
        elif mime == "application/jats+xml":
            if "<!ENTITY" in value.upper():
                raise ValueError("entity declarations are forbidden")
            declaration = re.search(r'<\?xml[^>]*encoding=[\'"]([^\'"]+)', value, re.I)
            if declaration and declaration.group(1).lower() not in {"utf-8", "utf8"}:
                raise ValueError("only UTF-8 XML is supported")
            root = ElementTree.fromstring(value)
            if root.tag.rsplit("}", 1)[-1] != "article":
                raise ValueError("JATS article root required")
            result = tuple(
                "".join(node.itertext())
                for node in root.iter()
                if node.tag.rsplit("}", 1)[-1] == "p"
            )
        else:
            raise ValueError("supported formats: text/plain, application/jats+xml")
    except (ValueError, UnicodeError, ElementTree.ParseError) as exc:
        raise _invalid("malformed, unsafe or unsupported source document") from exc
    if not any(item.strip() for item in result):
        raise _invalid("source document has no inspectable paragraphs")
    return result


def locate(values, quotation, *, paragraph=None, start=None, end=None):
    if not isinstance(quotation, str) or not quotation.strip() or len(quotation) > 2000:
        raise _invalid("a bounded exact quotation of 1..2000 characters is required")
    if paragraph is None and start is None and end is None:
        matches = []
        for number, value in enumerate(values, 1):
            cursor = 0
            while (position := value.find(quotation, cursor)) >= 0:
                matches.append((number, position, position + len(quotation)))
                cursor = position + 1
                if len(matches) > 1:
                    raise _invalid("ambiguous extraction: supply explicit paragraph and span")
        if len(matches) != 1:
            raise _invalid("quotation not found in source content")
        paragraph, start, end = matches[0]
    if not isinstance(paragraph, int) or not isinstance(start, int) or not isinstance(end, int):
        raise _invalid("explicit integer paragraph and span required")
    if (
        any(type(item) is not int for item in (paragraph, start, end))
        or not 1 <= paragraph <= len(values)
        or not 0 <= start < end <= len(values[paragraph - 1])
        or values[paragraph - 1][start:end] != quotation
    ):
        raise _invalid("invalid locator or evidence text mismatch")
    return {
        "page": None,
        "section": None,
        "paragraph": str(paragraph),
        "figure": None,
        "table": None,
        "quote_span": f"char:{start}:{end}",
    }


def relocate(values, locator):
    try:
        number = int(locator["paragraph"])
        match = re.fullmatch(r"char:(0|[1-9][0-9]*):(0|[1-9][0-9]*)", locator["quote_span"])
        if match is None or str(number) != locator["paragraph"]:
            raise ValueError("invalid span")
        start, end = map(int, match.groups())
        if not 1 <= number <= len(values) or not 0 <= start < end <= len(values[number - 1]):
            raise ValueError("range")
        return values[number - 1][start:end]
    except (KeyError, TypeError, ValueError) as exc:
        raise _invalid("invalid or out-of-range locator") from exc
