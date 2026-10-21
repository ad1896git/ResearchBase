"""Public literature identity value objects and versioned identifier normalization."""

from __future__ import annotations

import ipaddress
import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import SplitResult, urlsplit, urlunsplit

import idna

from researchbase.foundation.errors import ErrorCode, ResearchBaseError

NORMALIZATION_VERSION = "source-identifier-normalization-v1"
_PERCENT = re.compile(r"%(?![0-9A-Fa-f]{2})")
_UNRESERVED = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")


class IdentifierType(StrEnum):
    DOI = "DOI"
    ARXIV = "ARXIV"
    PMID = "PMID"
    SEMANTIC_SCHOLAR = "SEMANTIC_SCHOLAR"
    OPENALEX = "OPENALEX"
    URL = "URL"
    ISBN = "ISBN"
    OTHER = "OTHER"


class SourceKind(StrEnum):
    PAPER = "PAPER"
    PREPRINT = "PREPRINT"
    THESIS = "THESIS"
    BOOK = "BOOK"
    WEB = "WEB"
    STANDARD = "STANDARD"
    DATASET_DOC = "DATASET_DOC"
    OTHER = "OTHER"


class IdentifierStatus(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class NormalizedIdentifier:
    normalized_value: str
    normalization_version: str = NORMALIZATION_VERSION
    version_hint: str | None = None


def normalize_source_title(value: str) -> str:
    title = unicodedata.normalize("NFC", value).strip()
    if not title or any(unicodedata.category(char) in {"Cc", "Cs"} for char in title):
        raise _invalid("source title must be nonblank and contain no controls")
    return title


def normalize_reason(value: str) -> str:
    return normalize_source_title(value)


def normalize_source_identifier(
    identifier_type: IdentifierType,
    value: str,
    *,
    namespaces: frozenset[str] | set[str] = frozenset(),
) -> NormalizedIdentifier:
    raw = unicodedata.normalize("NFC", value).strip()
    if (
        not raw
        or len(raw) > 2048
        or any(unicodedata.category(char) in {"Cc", "Cs"} for char in raw)
    ):
        raise _invalid("identifier must be nonblank, at most 2048 code points, and control-free")
    if _PERCENT.search(raw):
        raise _invalid("identifier contains malformed percent encoding")
    _reject_encoded_controls(raw)
    _validate_percent_utf8(raw)

    hint: str | None = None
    if identifier_type is IdentifierType.DOI:
        normalized = _normalize_doi(raw)
    elif identifier_type is IdentifierType.ARXIV:
        normalized, hint = _normalize_arxiv(raw)
    elif identifier_type is IdentifierType.PMID:
        if not raw.isascii() or not raw.isdecimal() or int(raw) <= 0:
            raise _invalid("PMID must be a positive ASCII integer")
        normalized = str(int(raw))
    elif identifier_type is IdentifierType.ISBN:
        normalized = _normalize_isbn(raw)
    elif identifier_type is IdentifierType.SEMANTIC_SCHOLAR:
        if not re.fullmatch(r"[0-9A-Fa-f]{40}", raw, flags=re.ASCII):
            raise _invalid("Semantic Scholar identifier must contain 40 hexadecimal characters")
        normalized = raw.lower()
    elif identifier_type is IdentifierType.OPENALEX:
        value = raw
        if raw.startswith("https://openalex.org/"):
            value = raw.removeprefix("https://openalex.org/")
        elif raw.lower().startswith("https://openalex.org/"):
            raise _invalid("OpenAlex wrapper must use the exact path form")
        match = re.fullmatch(r"W([0-9]+)", value, flags=re.ASCII)
        if match is None or int(match.group(1)) <= 0:
            raise _invalid("OpenAlex identifier must be W followed by a positive integer")
        normalized = f"W{int(match.group(1))}"
    elif identifier_type is IdentifierType.URL:
        normalized = _normalize_url(raw)
    elif identifier_type is IdentifierType.OTHER:
        namespace, separator, other_value = raw.partition(":")
        if (
            not separator
            or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,63}", namespace, flags=re.ASCII)
            or namespace not in namespaces
            or not other_value
        ):
            raise _invalid("OTHER identifiers require a registered namespace:value")
        normalized = f"{namespace}:{other_value}"
    else:
        raise _invalid("unsupported identifier type")
    if len(normalized) > 2048:
        raise _invalid("normalized identifier exceeds 2048 code points")
    return NormalizedIdentifier(normalized, version_hint=hint)


def _normalize_doi(raw: str) -> str:
    value = raw
    if value.lower().startswith("doi:"):
        value = value[4:]
    else:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        if parsed.scheme.lower() == "https" and host == "doi.org":
            value = parsed.path.lstrip("/")
            if (
                parsed.username is not None
                or parsed.password is not None
                or parsed.port is not None
            ):
                raise _invalid("DOI wrapper must use the exact DOI authority")
            if parsed.query or parsed.fragment:
                raise _invalid("DOI wrapper cannot contain query or fragment")
        elif parsed.scheme.lower() == "http" and host == "dx.doi.org":
            value = parsed.path.lstrip("/")
            if (
                parsed.username is not None
                or parsed.password is not None
                or parsed.port is not None
            ):
                raise _invalid("DOI wrapper must use the exact DOI authority")
            if parsed.query or parsed.fragment:
                raise _invalid("DOI wrapper cannot contain query or fragment")
    match = re.fullmatch(r"10\.([0-9]{4,9})/(.+)", value, flags=re.ASCII | re.DOTALL)
    if match is None:
        raise _invalid("DOI must contain a valid registrant and nonempty suffix")
    suffix = _percent_unreserved(match.group(2))
    if re.search(r"%2[fF]", match.group(2)):
        raise _invalid("encoded slash is not valid in a DOI")
    return f"10.{match.group(1)}/{_ascii_lower(suffix)}"


def _normalize_arxiv(raw: str) -> tuple[str, str | None]:
    value = raw
    if value.lower().startswith("arxiv:"):
        value = value[6:]
    elif value.startswith("https://arxiv.org/"):
        parsed = urlsplit(value)
        if parsed.query or parsed.fragment:
            raise _invalid("arXiv wrapper cannot contain query or fragment")
        if parsed.path.startswith("/abs/"):
            value = parsed.path[5:]
        elif parsed.path.startswith("/pdf/"):
            value = parsed.path[5:]
            if value.endswith(".pdf"):
                value = value[:-4]
        else:
            raise _invalid("unsupported arXiv wrapper path")
    hint = None
    version = re.search(r"(v[1-9][0-9]*)$", value, flags=re.ASCII)
    if version:
        hint = version.group(1)
        value = value[: version.start()]
    if re.fullmatch(r"[0-9]{4}\.[0-9]{4,5}", value, flags=re.ASCII):
        # New-style identifiers encode year then month in the first four digits.
        month = int(value[2:4])
        if not 1 <= month <= 12:
            raise _invalid("arXiv month must be between 01 and 12")
        return value, hint
    if re.fullmatch(r"[A-Za-z]+(?:-[A-Za-z]+)?/[0-9]{7}", value, flags=re.ASCII):
        archive, number = value.split("/", 1)
        return f"{archive.lower()}/{number}", hint
    raise _invalid("invalid arXiv identifier")


def _normalize_isbn(raw: str) -> str:
    value = raw.replace(" ", "").replace("-", "")
    value = value.translate(str.maketrans("x", "X"))
    if re.fullmatch(r"[0-9]{9}[0-9X]", value, flags=re.ASCII):
        total = sum((10 - index) * int(char) for index, char in enumerate(value[:9]))
        check = (11 - total % 11) % 11
        if ("X" if check == 10 else str(check)) != value[-1]:
            raise _invalid("ISBN-10 checksum is invalid")
    elif re.fullmatch(r"(?:978|979)[0-9]{10}", value, flags=re.ASCII):
        total = sum(
            int(char) * (1 if index % 2 == 0 else 3) for index, char in enumerate(value[:12])
        )
        if str((10 - total % 10) % 10) != value[-1]:
            raise _invalid("ISBN-13 checksum is invalid")
    else:
        raise _invalid("ISBN must be a valid ISBN-10 or ISBN-13")
    return value


def _normalize_url(raw: str) -> str:
    if "\\" in raw:
        raise _invalid("URL cannot contain a backslash")
    try:
        parsed = urlsplit(raw)
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"} or not parsed.netloc:
            raise _invalid("URL must be absolute HTTP or HTTPS")
        if parsed.username is not None or parsed.password is not None:
            raise _invalid("URL credentials are not allowed")
        host = parsed.hostname
        if not host:
            raise _invalid("URL host is required")
        if "%" in host:
            raise _invalid("IP zone identifiers are not allowed")
        try:
            address = ipaddress.ip_address(host)
            host_text = f"[{address.compressed}]" if address.version == 6 else address.compressed
        except ValueError:
            if re.fullmatch(r"[0-9.]+", host, flags=re.ASCII):
                octets = host.split(".")
                if len(octets) == 4 and all(octet.isdecimal() for octet in octets):
                    numbers = [int(octet) for octet in octets]
                    if all(0 <= octet <= 255 for octet in numbers):
                        host_text = str(ipaddress.IPv4Address(bytes(numbers)))
                    else:
                        raise _invalid("invalid IPv4 literal") from None
                else:
                    raise _invalid("invalid IPv4 literal") from None
            else:
                host_text = (
                    idna.encode(
                        unicodedata.normalize("NFC", host),
                        uts46=True,
                        transitional=False,
                        std3_rules=True,
                    )
                    .decode("ascii")
                    .lower()
                )
        port = parsed.port
        if port is not None and not (1 <= port <= 65535):
            raise _invalid("URL port must be between 1 and 65535")
        authority = host_text
        if port is not None and not (
            (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
        ):
            authority = f"{authority}:{port}"
        path = _remove_dot_segments(_percent_unreserved(parsed.path or "/"))
        query = _percent_unreserved(parsed.query)
        return urlunsplit(SplitResult(scheme, authority, path, query, ""))
    except (UnicodeError, ValueError) as exc:
        if isinstance(exc, ResearchBaseError):
            raise
        raise _invalid("URL host or syntax is invalid") from exc


def _percent_unreserved(value: str) -> str:
    if _PERCENT.search(value):
        raise _invalid("identifier contains malformed percent encoding")
    output: list[str] = []
    index = 0
    while index < len(value):
        if value[index] == "%":
            byte = int(value[index + 1 : index + 3], 16)
            char = chr(byte)
            output.append(char if char in _UNRESERVED else f"%{byte:02X}")
            index += 3
        else:
            output.append(value[index])
            index += 1
    return "".join(output)


def _reject_encoded_controls(value: str) -> None:
    for match in re.finditer(r"%([0-9A-Fa-f]{2})", value):
        byte = int(match.group(1), 16)
        if byte < 0x20 or byte == 0x7F:
            raise _invalid("encoded control characters are not allowed")


def _validate_percent_utf8(value: str) -> None:
    encoded = bytearray()
    index = 0
    while index < len(value):
        if value[index] == "%":
            encoded.append(int(value[index + 1 : index + 3], 16))
            index += 3
            continue
        if encoded:
            _decode_utf8_percent_run(encoded)
            encoded.clear()
        index += 1
    if encoded:
        _decode_utf8_percent_run(encoded)


def _decode_utf8_percent_run(encoded: bytearray) -> None:
    if any(byte >= 0x80 for byte in encoded):
        try:
            encoded.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise _invalid("percent-encoded bytes must be valid UTF-8") from exc


def _ascii_lower(value: str) -> str:
    return value.translate(
        str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")
    )


def _remove_dot_segments(path: str) -> str:
    segments: list[str] = []
    for segment in path.split("/"):
        if segment == ".":
            continue
        if segment == "..":
            if segments:
                segments.pop()
            continue
        segments.append(segment)
    result = "/".join(segments)
    if path.startswith("/") and not result.startswith("/"):
        result = "/" + result
    if path.endswith(("/.", "/..")) and not result.endswith("/"):
        result += "/"
    return result or "/"


def _invalid(message: str) -> ResearchBaseError:
    return ResearchBaseError(ErrorCode.IDENTIFIER_INVALID, message)
