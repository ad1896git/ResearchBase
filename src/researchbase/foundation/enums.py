"""Shared string-valued enum convention without domain lifecycle ownership."""

from enum import StrEnum


class BaseStrEnum(StrEnum):
    """Base convention for stable string-valued foundation enums."""
