class PalmMindError(Exception):
    """Base application exception."""


class UnsupportedFileTypeError(PalmMindError):
    pass


class FileTooLargeError(PalmMindError):
    pass


class InvalidInputError(PalmMindError):
    pass


class EmptyDocumentError(PalmMindError):
    pass


class ExternalServiceError(PalmMindError):
    pass


class LLMNotConfiguredError(PalmMindError):
    pass
