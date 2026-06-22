class PreprocessorError(Exception):
    """Base class for exceptions in the preprocessor stage."""
    pass

class PdfProviderError(PreprocessorError):
    """Exception raised for errors in the PDF provider adapter."""
    pass
