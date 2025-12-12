"""Configuration management using ConfigParser with environment interpolation.

This module provides a production-grade configuration system that:
- Loads base configuration from config/base.ini
- Overlays environment-specific config from config/{env}.ini
- Interpolates environment variables at runtime using ${VAR_NAME} syntax
- Falls back to environment variables when config values are missing
- Validates required configuration before application startup

Usage:
    config = ConfigLoader.load()
    # Or specify environment explicitly:
    config = ConfigLoader.load(env='staging')
"""
from __future__ import annotations

import os
import re
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class AppConfig:
    """Application configuration with type safety.
    
    All configuration values are loaded from .ini files with environment
    variable interpolation support.
    """

    env: str
    app_name: str
    log_level: str

    s3_bucket: str
    s3_raw_prefix: str
    s3_validated_prefix: str
    s3_transformed_prefix: str
    s3_error_prefix: str
    s3_recon_prefix: str

    redshift_host: str
    redshift_port: int
    redshift_database: str
    redshift_user: str
    redshift_password: str
    redshift_iam_role_arn: str

    dry_run: bool

    @classmethod
    def from_env(cls) -> AppConfig:
        """Load configuration for backward compatibility.
        
        Delegates to ConfigLoader.load() for consistent behavior.
        """
        return ConfigLoader.load()


class ConfigLoader:
    """Loads configuration from .ini files with environment interpolation."""

    ENV_VAR_PATTERN = re.compile(r'\$\{([^}]+)\}')

    @classmethod
    def load(cls, env: Optional[str] = None) -> AppConfig:
        """Load configuration from .ini files.
        
        Args:
            env: Environment name (dev/staging/prod). 
                 Defaults to APP_ENV environment variable or 'dev'.
        
        Returns:
            AppConfig instance with all values loaded and interpolated.
        
        Raises:
            ValueError: If required configuration is missing.
            FileNotFoundError: If config files cannot be found.
        """
        if env is None:
            env = os.getenv('APP_ENV', 'dev')

        config_dir = cls._get_config_dir()
        parser = cls._load_config_files(config_dir, env)
        
        return cls._build_app_config(parser, env)

    @classmethod
    def _get_config_dir(cls) -> Path:
        """Find the config directory relative to this file."""
        # Handle both src/app/config_loader.py and when installed
        current_file = Path(__file__).resolve()
        
        # Try: src/app/config_loader.py -> ../../config
        config_dir = current_file.parent.parent.parent / 'config'
        if config_dir.exists():
            return config_dir
        
        # Try: installed location -> ../config
        config_dir = current_file.parent.parent / 'config'
        if config_dir.exists():
            return config_dir
        
        raise FileNotFoundError(
            f"Config directory not found. Searched: {config_dir}"
        )

    @classmethod
    def _load_config_files(cls, config_dir: Path, env: str) -> ConfigParser:
        """Load base.ini and environment-specific .ini file.
        
        Args:
            config_dir: Path to config directory.
            env: Environment name.
        
        Returns:
            ConfigParser with values from both files merged.
        """
        parser = ConfigParser()
        
        # Load base config
        base_file = config_dir / 'base.ini'
        if not base_file.exists():
            raise FileNotFoundError(f"Base config not found: {base_file}")
        parser.read(base_file)
        
        # Overlay environment-specific config
        env_file = config_dir / f'{env}.ini'
        if env_file.exists():
            parser.read(env_file)
        else:
            # Warn but don't fail - base config might be sufficient
            import warnings
            warnings.warn(f"Environment config not found: {env_file}")
        
        return parser

    @classmethod
    def _interpolate(cls, value: str) -> str:
        """Replace ${VAR_NAME} with environment variable values.
        
        Args:
            value: String that may contain ${VAR_NAME} placeholders.
        
        Returns:
            String with all placeholders replaced by environment values.
        
        Raises:
            ValueError: If required environment variable is missing.
        """
        def replacer(match):
            var_name = match.group(1)
            env_value = os.getenv(var_name)
            if env_value is None:
                raise ValueError(
                    f"Required environment variable not set: {var_name}"
                )
            return env_value
        
        return cls.ENV_VAR_PATTERN.sub(replacer, value)

    @classmethod
    def _get_value(
        cls, 
        parser: ConfigParser, 
        section: str, 
        key: str,
        required: bool = True,
        fallback: Optional[str] = None,
    ) -> str:
        """Get configuration value with interpolation and env var fallback.
        
        Priority order:
        1. Direct environment variable (for backward compatibility)
        2. Interpolated value from .ini file
        3. Fallback value
        4. Raise error if required=True
        
        Args:
            parser: ConfigParser instance.
            section: Section name in .ini file.
            key: Key name in section.
            required: Whether this value is required.
            fallback: Default value if not found.
        
        Returns:
            Configuration value as string.
        
        Raises:
            ValueError: If required value is missing.
        """
        # Check environment variable first for backward compatibility
        env_key = f"{section.upper()}_{key.upper()}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value
        
        # Try .ini file
        if parser.has_option(section, key):
            value = parser.get(section, key)
            # Interpolate any ${VAR} references
            value = cls._interpolate(value)
            return value
        
        # Use fallback if provided
        if fallback is not None:
            return fallback
        
        # Error if required
        if required:
            raise ValueError(
                f"Required configuration missing: [{section}] {key}. "
                f"Set in config file or environment variable {env_key}"
            )
        
        return ""

    @classmethod
    def _build_app_config(cls, parser: ConfigParser, env: str) -> AppConfig:
        """Build AppConfig from parsed configuration.
        
        Args:
            parser: ConfigParser with loaded values.
            env: Environment name.
        
        Returns:
            AppConfig instance.
        """
        return AppConfig(
            env=env,
            app_name=cls._get_value(parser, 'app', 'app_name'),
            log_level=cls._get_value(parser, 'app', 'log_level'),
            
            s3_bucket=cls._get_value(parser, 's3', 'bucket'),
            s3_raw_prefix=cls._get_value(parser, 's3', 'raw_prefix'),
            s3_validated_prefix=cls._get_value(parser, 's3', 'validated_prefix'),
            s3_transformed_prefix=cls._get_value(parser, 's3', 'transformed_prefix'),
            s3_error_prefix=cls._get_value(parser, 's3', 'error_prefix'),
            s3_recon_prefix=cls._get_value(parser, 's3', 'recon_prefix'),
            
            redshift_host=cls._get_value(parser, 'redshift', 'host'),
            redshift_port=int(cls._get_value(parser, 'redshift', 'port', fallback='5439')),
            redshift_database=cls._get_value(parser, 'redshift', 'database'),
            redshift_user=cls._get_value(parser, 'redshift', 'user'),
            redshift_password=cls._get_value(
                parser, 'redshift', 'password',
                fallback=os.getenv('REDSHIFT_PASSWORD', '')
            ),
            redshift_iam_role_arn=cls._get_value(parser, 'redshift', 'iam_role_arn'),
            
            dry_run=cls._get_value(
                parser, 'feature_flags', 'dry_run', fallback='false'
            ).lower() in {'true', '1', 'yes'},
        )
