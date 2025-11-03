"""
Base exception classes for the Open WebUI Customizer application.

This module defines the base exception hierarchy and specific exception
classes for different types of errors that can occur in the application.
"""


class OpenWebUICustomizerError(Exception):
    """
    Base exception class for all application-specific errors.

    This is the root exception class for all custom exceptions in the
    Open WebUI Customizer application. It provides a consistent interface
    for error handling and reporting.
    """

    def __init__(self, message: str, details: dict = None):
        """
        Initialize the exception.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error details.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        """Return string representation of the exception."""
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class ValidationError(OpenWebUICustomizerError):
    """
    Exception raised for validation errors.

    This exception is raised when input data fails validation checks,
    such as invalid file formats, missing required fields, or
    constraint violations.
    """
    pass


class NotFoundError(OpenWebUICustomizerError):
    """
    Exception raised when a requested resource is not found.

    This exception is raised when attempting to access resources
    that do not exist, such as templates, assets, or configurations
    that have been deleted or never existed.
    """
    pass


class ConfigurationError(OpenWebUICustomizerError):
    """
    Exception raised for configuration-related errors.

    This exception is raised when there are issues with application
    configuration, such as missing environment variables, invalid
    settings, or configuration file parsing errors.
    """
    pass


class FileOperationError(OpenWebUICustomizerError):
    """
    Exception raised for file operation errors.

    This exception is raised when file operations fail, such as
    reading/writing files, creating directories, or permission issues.
    """

    def __init__(self, message: str, file_path: str = None, operation: str = None, details: dict = None):
        """
        Initialize the file operation exception.

        Args:
            message: Human-readable error message.
            file_path: Path to the file that caused the error.
            operation: The operation that failed (read, write, delete, etc.).
            details: Optional dictionary with additional error details.
        """
        super().__init__(message, details)
        self.file_path = file_path
        self.operation = operation


class DatabaseError(OpenWebUICustomizerError):
    """
    Exception raised for database operation errors.

    This exception is raised when database operations fail, such as
    connection issues, query errors, or constraint violations.
    """

    def __init__(self, message: str, operation: str = None, table: str = None, details: dict = None):
        """
        Initialize the database exception.

        Args:
            message: Human-readable error message.
            operation: The database operation that failed (select, insert, update, delete).
            table: The database table involved in the operation.
            details: Optional dictionary with additional error details.
        """
        super().__init__(message, details)
        self.operation = operation
        self.table = table


class PipelineError(OpenWebUICustomizerError):
    """
    Exception raised for pipeline execution errors.

    This exception is raised when pipeline operations fail, such as
    step execution errors, timeout issues, or dependency problems.
    """

    def __init__(self, message: str, step: str = None, run_id: int = None, details: dict = None):
        """
        Initialize the pipeline exception.

        Args:
            message: Human-readable error message.
            step: The pipeline step that failed.
            run_id: The pipeline run ID.
            details: Optional dictionary with additional error details.
        """
        super().__init__(message, details)
        self.step = step
        self.run_id = run_id


class BrandingError(OpenWebUICustomizerError):
    """
    Exception raised for branding operation errors.

    This exception is raised when branding operations fail, such as
    template application errors, asset processing issues, or
    replacement rule execution problems.
    """

    def __init__(self, message: str, template_id: int = None, operation: str = None, details: dict = None):
        """
        Initialize the branding exception.

        Args:
            message: Human-readable error message.
            template_id: The branding template ID involved.
            operation: The branding operation that failed.
            details: Optional dictionary with additional error details.
        """
        super().__init__(message, details)
        self.template_id = template_id
        self.operation = operation