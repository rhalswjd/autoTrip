"""Classify a platform only after the caller establishes source parsing success."""
from domain.platform import PlatformStatus


def read_platform(value: object, *, field_parsed: bool) -> tuple[str, PlatformStatus]:
    if not field_parsed or (value is not None and (isinstance(value, bool) or not isinstance(value, (str, int)))):
        return '', PlatformStatus.LOOKUP_FAILED
    text = str(value).strip() if value is not None else ''
    if text in {'', '-', '--', '―', '情報なし', '不明'}:
        return '', PlatformStatus.SOURCE_NOT_PROVIDED
    return text, PlatformStatus.KNOWN
