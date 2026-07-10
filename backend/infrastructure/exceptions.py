from core.exceptions import DomainException

class InfrastructureException(Exception):
    """Base exception for Infrastructure errors."""
    pass

class HttpClientException(InfrastructureException):
    """Raised when HTTP request fails (timeout, 5xx, etc.)."""
    pass

class HtmlParsingException(InfrastructureException):
    """Raised when HTML structure is unexpected or parsing fails."""
    pass
