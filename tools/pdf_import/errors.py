"""Errors shared by the PDF importer without loading optional PDF dependencies."""


class ImportValidationError(ValueError):
    """A chart is incomplete or inconsistent and cannot be exported."""
