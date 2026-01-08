"""
Input validation utilities for the Open WebUI Customizer application.

This module provides reusable validation functions for API endpoints
and service layers to ensure data integrity and security.

Author: Open WebUI Customizer Team
"""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.exceptions import ValidationError


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
    """
    Validate that all required fields are present in the data.
    
    Args:
        data: Dictionary of data to validate
        required_fields: List of field names that are required
        
    Raises:
        ValidationError: If any required field is missing or empty
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == "":
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationError(
            f"Missing required fields: {', '.join(missing_fields)}",
            details={'missing_fields': missing_fields}
        )


def validate_url_format(url: str) -> bool:
    """
    Validate that a URL has a proper format.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if URL format is valid, False otherwise
        
    Raises:
        ValidationError: If URL format is invalid
    """
    if not url or not isinstance(url, str):
        raise ValidationError("URL must be a non-empty string")
    
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def validate_git_repository_url(url: str) -> bool:
    """
    Validate Git repository URL format (HTTPS or SSH).
    
    Args:
        url: Git repository URL to validate
        
    Returns:
        True if URL format is valid, False otherwise
        
    Raises:
        ValidationError: If URL format is invalid
    """
    if not url or not isinstance(url, str):
        raise ValidationError("Repository URL must be a non-empty string")
    
    url = url.strip()
    
    # SSH patterns
    ssh_patterns = [
        r'^git@[\w\.-]+:[\w\.\-\/]+\.git$',
        r'^ssh://git@[\w\.-]+[\w\.\-\/]*\.git$'
    ]
    
    # HTTPS patterns
    https_patterns = [
        r'^https?://[\w\.\-]+/[\w\.\-\/]+\.git$',
        r'^https?://[\w\.\-]+/[\w\.\-\/]*$'  # May not end with .git
    ]
    
    # Check SSH patterns
    for pattern in ssh_patterns:
        if re.match(pattern, url):
            return True
    
    # Check HTTPS patterns
    for pattern in https_patterns:
        if re.match(pattern, url):
            return True
    
    return False


def validate_credential_type(credential_type: str) -> bool:
    """
    Validate credential type is supported.
    
    Args:
        credential_type: Type string to validate
        
    Returns:
        True if type is valid, False otherwise
        
    Raises:
        ValidationError: If credential type is invalid
    """
    valid_types = [
        'git_ssh',
        'git_https',
        'registry_docker_hub',
        'registry_aws_ecr',
        'registry_quay_io'
    ]
    
    if not isinstance(credential_type, str):
        raise ValidationError("Credential type must be a string")
    
    if credential_type not in valid_types:
        raise ValidationError(
            f"Invalid credential type. Must be one of: {', '.join(valid_types)}",
            details={'invalid_type': credential_type, 'valid_types': valid_types}
        )
    
    return True


def validate_ssh_key_format(ssh_key: str) -> bool:
    """
    Validate SSH private key format.
    
    Args:
        ssh_key: SSH private key string to validate
        
    Returns:
        True if key format appears valid, False otherwise
        
    Raises:
        ValidationError: If SSH key format is invalid
    """
    if not isinstance(ssh_key, str):
        raise ValidationError("SSH key must be a string")
    
    ssh_key = ssh_key.strip()
    
    if not ssh_key:
        raise ValidationError("SSH key cannot be empty")
    
    # Check for SSH private key headers
    valid_headers = [
        '-----BEGIN RSA PRIVATE KEY-----',
        '-----BEGIN OPENSSH PRIVATE KEY-----',
        '-----BEGIN DSA PRIVATE KEY-----',
        '-----BEGIN EC PRIVATE KEY-----',
        '-----BEGIN PGP PRIVATE KEY BLOCK-----'
    ]
    
    for header in valid_headers:
        if ssh_key.startswith(header):
            # Check for corresponding footer
            footer = header.replace('BEGIN', 'END')
            if ssh_key.strip().endswith(footer):
                return True
    
    return False


def validate_branch_name(branch: str) -> bool:
    """
    Validate Git branch name format.
    
    Args:
        branch: Branch name to validate
        
    Returns:
        True if branch name is valid, False otherwise
        
    Raises:
        ValidationError: If branch name is invalid
    """
    if not isinstance(branch, str):
        raise ValidationError("Branch name must be a string")
    
    branch = branch.strip()
    
    if not branch:
        raise ValidationError("Branch name cannot be empty")
    
    # Git branch name rules
    invalid_patterns = [
        r'\.\.',  # No double dots
        r'^\.',   # Cannot start with dot
        r'\.$',   # Cannot end with dot
        r'@{',    # No reflog specifiers
        r'^-$',   # Cannot be just a dash
        r'\s',    # No whitespace
    ]
    
    for pattern in invalid_patterns:
        if re.search(pattern, branch):
            return False
    
    # Cannot start with -
    if branch.startswith('-'):
        return False
    
    # Cannot contain consecutive slashes
    if '//' in branch:
        return False
    
    return True


def validate_docker_image_name(image: str) -> bool:
    """
    Validate Docker image name format.
    
    Args:
        image: Docker image name to validate
        
    Returns:
        True if image name is valid, False otherwise
        
    Raises:
        ValidationError: If image name is invalid
    """
    if not isinstance(image, str):
        raise ValidationError("Docker image name must be a string")
    
    image = image.strip()
    
    if not image:
        raise ValidationError("Docker image name cannot be empty")
    
    # Docker image name patterns
    # Simplified validation - actual Docker rules are more complex
    pattern = r'^[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)*(?::[a-zA-Z0-9._-]+)?$'
    
    return bool(re.match(pattern, image))


def validate_email_format(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email format is valid, False otherwise
        
    Raises:
        ValidationError: If email format is invalid
    """
    if not isinstance(email, str):
        raise ValidationError("Email must be a string")
    
    email = email.strip()
    
    if not email:
        raise ValidationError("Email cannot be empty")
    
    # Basic email validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    return bool(re.match(pattern, email))


def validate_pagination_params(skip: int = 0, limit: int = 100) -> tuple[int, int]:
    """
    Validate and normalize pagination parameters.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        Tuple of normalized (skip, limit)
        
    Raises:
        ValidationError: If parameters are invalid
    """
    if not isinstance(skip, int) or skip < 0:
        raise ValidationError("Skip must be a non-negative integer")
    
    if not isinstance(limit, int) or limit <= 0:
        raise ValidationError("Limit must be a positive integer")
    
    # Reasonable limits to prevent performance issues
    if limit > 1000:
        raise ValidationError("Limit cannot exceed 1000")
    
    return skip, limit


def validate_json_structure(data: Any, required_keys: List[str] | None = None) -> bool:
    """
    Validate that data is a properly structured JSON object.
    
    Args:
        data: Data to validate (should be dict-like)
        required_keys: List of keys that must be present
        
    Returns:
        True if structure is valid, False otherwise
        
    Raises:
        ValidationError: If structure is invalid
    """
    if not isinstance(data, dict):
        raise ValidationError("Data must be a JSON object (dictionary)")
    
    if required_keys:
        missing_keys = [key for key in required_keys if key not in data]
        if missing_keys:
            raise ValidationError(
                f"Missing required keys: {', '.join(missing_keys)}",
                details={'missing_keys': missing_keys}
            )
    
    return True


def sanitize_string_input(value: str, max_length: int | None = None) -> str:
    """
    Sanitize and validate string input.
    
    Args:
        value: String value to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
        
    Raises:
        ValidationError: If string is invalid
    """
    if not isinstance(value, str):
        raise ValidationError("Value must be a string")
    
    # Remove leading/trailing whitespace
    sanitized = value.strip()
    
    if not sanitized:
        raise ValidationError("String cannot be empty or whitespace only")
    
    if max_length and len(sanitized) > max_length:
        raise ValidationError(
            f"String exceeds maximum length of {max_length} characters",
            details={'actual_length': len(sanitized), 'max_length': max_length}
        )
    
    return sanitized


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """
    Validate that a file has an allowed extension.
    
    Args:
        filename: Name of the file to validate
        allowed_extensions: List of allowed extensions (withoutdots)
        
    Returns:
        True if extension is allowed, False otherwise
        
    Raises:
        ValidationError: If extension is not allowed
    """
    if not isinstance(filename, str):
        raise ValidationError("Filename must be a string")
    
    if '.' not in filename:
        raise ValidationError("Filename must have an extension")
    
    extension = filename.rsplit('.', 1)[1].lower()
    
    if extension not in [ext.lower() for ext in allowed_extensions]:
        raise ValidationError(
            f"File extension '.{extension}' is not allowed",
            details={
                'allowed_extensions': allowed_extensions,
                'provided_extension': extension
            }
        )
    
    return True