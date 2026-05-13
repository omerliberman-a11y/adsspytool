class AdspyError(Exception):
    """Base exception for adspy."""


class ScrapeError(AdspyError):
    """Raised when a scraper fails (Apify run error, timeout, cost cap)."""


class NormalizerError(AdspyError):
    """Raised when a normalizer cannot map a raw record into the Ad schema."""


class CostCapExceeded(ScrapeError):
    """Raised when an Apify run would exceed APIFY_MAX_USD_PER_RUN."""
