"""Independent evidence states for each end of an exact railway ride."""
from enum import Enum


class PlatformStatus(str, Enum):
    KNOWN = 'KNOWN'
    SOURCE_NOT_PROVIDED = 'SOURCE_NOT_PROVIDED'
    LOOKUP_FAILED = 'LOOKUP_FAILED'
