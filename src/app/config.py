"""Configuration management for the application.

This module provides backward compatibility with the old environment-variable
based configuration while delegating to the new ConfigParser-based system.

For new code, import from config_loader:
    from app.config_loader import AppConfig, ConfigLoader
    config = ConfigLoader.load()

For legacy code, this still works:
    from app.config import AppConfig
    config = AppConfig.from_env()
"""
from __future__ import annotations

# Re-export AppConfig and ConfigLoader for convenience
from app.config_loader import AppConfig, ConfigLoader

__all__ = ['AppConfig', 'ConfigLoader']
