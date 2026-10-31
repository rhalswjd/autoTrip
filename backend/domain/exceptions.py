"""Business failures independent of HTTP and persistence adapters."""


class DomainException(Exception):
    """A business rule or journey-context precondition was not satisfied."""
