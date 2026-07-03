class ExtractionError(Exception):
    pass


class PageLoadError(ExtractionError):
    pass


class BrowserUnavailableError(ExtractionError):
    pass


class InvalidURLError(ExtractionError):
    pass
