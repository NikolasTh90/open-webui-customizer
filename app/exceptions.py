"""
Custom exception classes for the Open WebUI Customizer application.

This module provides domain-specific exceptions for better error handling
and user feedback throughout the application.

Author: Open WebUI Customizer Team
"""


class BaseCustomException(Exception):
    """
    Base class for all custom exceptions in the application.
    
    Provides standardized error handling with optional context details.
    """
    
    def __init__(self, message: str, details: dict | None = None):
        """
        Initialize the custom exception.
        
        Args:
            message: Human-readable error message
            details: Optional dictionary with additional error context
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(BaseCustomException):
    """
    Raised when input validation fails.
    
    Used for invalid user input, malformed data, or constraint violations.
    """
    pass


class NotFoundError(BaseCustomException):
    """
    Raised when a requested resource is not found.
    
    Used when database queries return no results or resources don't exist.
    """
    pass


class DatabaseError(BaseCustomException):
    """
    Raised when database operations fail.
    
    Used for connection issues, query failures, or transaction problems.
    """
    
    def __init__(self, message: str, operation: str | None = None, table: str | None = None, details: dict | None = None):
        """
        Initialize database error with operation context.
        
        Args:
            message: Human-readable error message
            operation: Database operation that failed (select, insert, update, delete)
            table: Database table name
            details: Additional error context
        """
        super().__init__(message, details)
        self.operation = operation
        self.table = table


class DuplicateResourceError(BaseCustomException):
    """
    Raised when attempting to create a resource that already exists.
    
    Used for unique constraint violations or duplicate key errors.
    """
    
    def __init__(self, message: str, resource_type: str | None = None,
                 conflict_field: str | None = None, existing_id: int | None = None, details: dict | None = None):
        """
        Initialize duplicate resource error with context.
        
        Args:
            message: Human-readable error message
            resource_type: Type of resource that conflicts
            conflict_field: Field that caused the conflict
            existing_id: ID of the existing resource
            details: Additional error context
        """
        super().__init__(message, details)
        self.resource_type = resource_type
        self.conflict_field = conflict_field
        self.existing_id = existing_id


class PipelineError(BaseCustomException):
    """
    Raised when pipeline operations fail.
    
    Used for build failures, execution errors, or pipeline configuration issues.
    """
    pass


class FileOperationError(BaseCustomException):
    """
    Raised when file system operations fail.
    
    Used for file I/O errors, permission issues, or disk space problems.
    """
    
    def __init__(self, message: str, file_path: str | None = None, operation: str | None = None, details: dict | None = None):
        """
        Initialize file operation error with context.
        
        Args:
            message: Human-readable error message
            file_path: Path of the file involved in the operation
            operation: File operation that failed (read, write, delete, etc.)
            details: Additional error context
        """
        super().__init__(message, details)
        self.file_path = file_path
        self.operation = operation


class ConfigurationError(BaseCustomException):
    """
    Raised when application configuration is invalid.
    
    Used for missing settings, invalid values, or configuration conflicts.
    """
    pass


class AuthenticationError(BaseCustomException):
    """
    Raised when authentication fails.
    
    Used for invalid credentials, authentication service errors, or permission issues.
    """
    pass


class AuthorizationError(BaseCustomException):
    """
    Raised when authorization fails.
    
    Used when a user has valid authentication but lacks permission for an operation.
    """
    pass


class ExternalServiceError(BaseCustomException):
    """
    Raised when external service calls fail.
    
    Used for Git operations, container registry calls, or other external API failures.
    """
    
    def __init__(self, message: str, service_name: str | None = None, status_code: int | None = None, details: dict | None = None):
        """
        Initialize external service error with context.
        
        Args:
            message: Human-readable error message
            service_name: Name of the external service
            status_code: HTTP status code if applicable
            details: Additional error context
        """
        super().__init__(message, details)
        self.service_name = service_name
        self.status_code = status_code


class EncryptionError(BaseCustomException):
    """
    Raised when encryption/decryption operations fail.
    
    Used for key management issues or cryptographic failures.
    """
    pass


class RateLimitError(BaseCustomException):
    """
    Raised when rate limits are exceeded.
    
    Used for API rate limiting or resource throttling.
    """
    
    def __init__(self, message: str, retry_after: int | None = None, details: dict | None = None):
        """
        Initialize rate limit error with retry information.
        
        Args:
            message: Human-readable error message
            retry_after: Seconds to wait before retrying
            details: Additional error context
        """
        super().__init__(message, details)
        self.retry_after = retry_after