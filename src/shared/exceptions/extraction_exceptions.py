class ExtractionError(Exception):
    """Base class for exceptions raised during the extraction stage."""
    pass


class ExtractionProviderError(ExtractionError):
    """Exception raised for errors in the PDF extraction adapter."""
    pass
