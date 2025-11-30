from __future__ import annotations


class AppError(Exception):
    """Base class for all custom application errors."""


class ConfigError(AppError):
    """Raised when required configuration is missing or invalid."""


class ValidationError(AppError):
    """Base class for validation-related errors."""


class SchemaMismatchError(ValidationError):
    """
    Raised when a file's columns or inferred types do not match the
    expected schema for that table.
    """


class BusinessRuleViolation(ValidationError):
    """
    Raised when a row violates domain rules, e.g. negative visits or
    utilization > 1.0.
    """


class RepositoryError(AppError):
    """
    Raised when storage / database operations fail (S3, Redshift, etc.).
    """


class MigrationError(AppError):
    """
    Raised when a migration job fails in an unexpected way.
    """


class DataQualityError(AppError):
    """
    Raised when reconciliation / DQ thresholds are not met.
    """
