"""Exact service identity, separate from a railway corridor or generic train class."""
import re
import unicodedata
from dataclasses import dataclass


_CLASSES = ('通勤特快', '特別快速', '通勤快速', '区間快速', '関空快速', '紀州路快速',
            '新快速', '快速', '各駅停車', '普通', '特急', '急行', '新幹線')
_CLASS_PATTERN = re.compile('|'.join(_CLASSES))


@dataclass(frozen=True)
class ServiceIdentity:
    category: str
    name: str


def service_identities(value: str) -> tuple[ServiceIdentity, ...]:
    """Normalize category and exact names, including explicitly coupled portions.

    Train numbers/annotations are cosmetic; brand text and category distinctions
    are retained. Corridor fragments are not mistaken for named train portions.
    """
    text = unicodedata.normalize('NFKC', value or '')
    text = re.sub(r'\([^()]*\)', '', text)
    parts = re.split(r'[・/]', text)
    result = []
    for part in parts:
        part = re.sub(r'\s+', '', part)
        part = re.sub(r'\d+号?$', '', part)
        part = re.sub(r'^JR', '', part, flags=re.I)
        match = _CLASS_PATTERN.search(part)
        if match:
            category, name = match[0], part[match.end():]
            result.append(ServiceIdentity(category, name.casefold()))
        elif part and not any(marker in text for marker in ('線', '鉄道')):
            result.append(ServiceIdentity('', part.casefold()))
    return tuple(result)


def has_named_service(value: str) -> bool:
    return any(identity.name for identity in service_identities(value))


def service_match_strength(expected: str, actual: str) -> int:
    """2: exact service/class; 1: category-only evidence; 0: incompatible.

    Missing specific metadata can be investigated, but cannot prove a named
    departure. Exact train detail must verify it before selection.
    """
    wanted, supplied = service_identities(expected), service_identities(actual)
    if not wanted:
        return 1
    best = 0
    for left in wanted:
        for right in supplied:
            if left.name:
                if right.name:
                    if left.name == right.name and (not left.category or not right.category or left.category == right.category):
                        best = 2
                elif left.category and left.category == right.category:
                    best = max(best, 1)
            elif left.category and left.category == right.category:
                best = max(best, 2)
    return best
