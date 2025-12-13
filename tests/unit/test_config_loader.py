"""Tests for ConfigParser-based configuration system."""
from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

import pytest

from app.config_loader import AppConfig, ConfigLoader


class TestConfigLoader:
    """Test suite for ConfigLoader with .ini files and interpolation."""

    def test_load_dev_config_from_file(self, monkeypatch):
        """Test loading development configuration from .ini files."""
        # Set minimal required env vars
        monkeypatch.setenv('S3_BUCKET', 'test-bucket-dev')
        monkeypatch.setenv('REDSHIFT_HOST', 'localhost')
        monkeypatch.setenv('REDSHIFT_DATABASE', 'testdb')
        monkeypatch.setenv('REDSHIFT_USER', 'testuser')
        monkeypatch.setenv('REDSHIFT_PASSWORD', 'testpass')
        monkeypatch.setenv('REDSHIFT_IAM_ROLE_ARN', 'arn:aws:iam::test')
        
        config = ConfigLoader.load(env='dev')
        
        assert config.env == 'dev'
        assert config.app_name == 'xyz-pricing-migration'
        assert config.log_level == 'DEBUG'  # dev.ini overrides base
        assert config.s3_raw_prefix == 'raw'
        assert config.dry_run is True  # dev.ini sets this

    def test_interpolation_from_env_vars(self, monkeypatch):
        """Test ${VAR_NAME} interpolation from environment variables."""
        monkeypatch.setenv('S3_BUCKET', 'prod-bucket-123')
        monkeypatch.setenv('REDSHIFT_HOST', 'prod.redshift.amazonaws.com')
        monkeypatch.setenv('REDSHIFT_DATABASE', 'proddb')
        monkeypatch.setenv('REDSHIFT_USER', 'produser')
        monkeypatch.setenv('REDSHIFT_PASSWORD', 'prodpass')
        monkeypatch.setenv('REDSHIFT_IAM_ROLE_ARN', 'arn:aws:iam::prod')
        
        config = ConfigLoader.load(env='prod')
        
        # prod.ini uses ${S3_BUCKET} syntax
        assert config.s3_bucket == 'prod-bucket-123'
        assert config.redshift_host == 'prod.redshift.amazonaws.com'

    def test_missing_required_env_var_raises_error(self, monkeypatch):
        """Test that missing required environment variables raise ValueError."""
        # Don't set S3_BUCKET
        monkeypatch.delenv('S3_BUCKET', raising=False)
        monkeypatch.setenv('REDSHIFT_HOST', 'localhost')
        monkeypatch.setenv('REDSHIFT_DATABASE', 'testdb')
        monkeypatch.setenv('REDSHIFT_USER', 'testuser')
        monkeypatch.setenv('REDSHIFT_PASSWORD', 'testpass')
        monkeypatch.setenv('REDSHIFT_IAM_ROLE_ARN', 'arn:aws:iam::test')
        
        with pytest.raises(ValueError, match="Required environment variable not set: S3_BUCKET"):
            ConfigLoader.load(env='prod')

    def test_fallback_to_env_when_not_in_ini(self, monkeypatch):
        """Test fallback to environment variables when key not in .ini."""
        monkeypatch.setenv('S3_BUCKET', 'fallback-bucket')
        monkeypatch.setenv('REDSHIFT_HOST', 'fallback-host')
        monkeypatch.setenv('REDSHIFT_DATABASE', 'fallbackdb')
        monkeypatch.setenv('REDSHIFT_USER', 'fallbackuser')
        monkeypatch.setenv('REDSHIFT_PASSWORD', 'fallbackpass')
        monkeypatch.setenv('REDSHIFT_IAM_ROLE_ARN', 'arn:aws:iam::fallback')
        
        config = ConfigLoader.load(env='dev')
        
        # Password not in .ini, should come from env
        assert config.redshift_password == 'fallbackpass'

    def test_staging_config_loads(self, monkeypatch):
        """Test loading staging environment configuration."""
        monkeypatch.setenv('S3_BUCKET', 'staging-bucket')
        monkeypatch.setenv('REDSHIFT_HOST', 'staging.redshift.amazonaws.com')
        monkeypatch.setenv('REDSHIFT_DATABASE', 'stagingdb')
        monkeypatch.setenv('REDSHIFT_USER', 'staginguser')
        monkeypatch.setenv('REDSHIFT_PASSWORD', 'stagingpass')
        monkeypatch.setenv('REDSHIFT_IAM_ROLE_ARN', 'arn:aws:iam::staging')
        
        config = ConfigLoader.load(env='staging')
        
        assert config.env == 'staging'
        assert config.log_level == 'INFO'
        assert config.dry_run is False

    def test_backward_compatibility_from_env(self, monkeypatch):
        """Test that AppConfig.from_env() still works for backward compatibility."""
        monkeypatch.setenv('APP_ENV', 'dev')
        monkeypatch.setenv('S3_BUCKET', 'compat-bucket')
        monkeypatch.setenv('REDSHIFT_HOST', 'compat-host')
        monkeypatch.setenv('REDSHIFT_DATABASE', 'compatdb')
        monkeypatch.setenv('REDSHIFT_USER', 'compatuser')
        monkeypatch.setenv('REDSHIFT_PASSWORD', 'compatpass')
        monkeypatch.setenv('REDSHIFT_IAM_ROLE_ARN', 'arn:aws:iam::compat')
        
        config = AppConfig.from_env()
        
        assert isinstance(config, AppConfig)
        assert config.env == 'dev'
        assert config.s3_bucket == 'compat-bucket'

    def test_default_env_is_dev(self, monkeypatch):
        """Test that default environment is 'dev' when APP_ENV not set."""
        monkeypatch.delenv('APP_ENV', raising=False)
        monkeypatch.setenv('S3_BUCKET', 'default-bucket')
        monkeypatch.setenv('REDSHIFT_HOST', 'default-host')
        monkeypatch.setenv('REDSHIFT_DATABASE', 'defaultdb')
        monkeypatch.setenv('REDSHIFT_USER', 'defaultuser')
        monkeypatch.setenv('REDSHIFT_PASSWORD', 'defaultpass')
        monkeypatch.setenv('REDSHIFT_IAM_ROLE_ARN', 'arn:aws:iam::default')
        
        config = ConfigLoader.load()
        
        assert config.env == 'dev'

    def test_boolean_parsing(self, monkeypatch):
        """Test that boolean values are parsed correctly."""
        monkeypatch.setenv('S3_BUCKET', 'bool-bucket')
        monkeypatch.setenv('REDSHIFT_HOST', 'bool-host')
        monkeypatch.setenv('REDSHIFT_DATABASE', 'booldb')
        monkeypatch.setenv('REDSHIFT_USER', 'booluser')
        monkeypatch.setenv('REDSHIFT_PASSWORD', 'boolpass')
        monkeypatch.setenv('REDSHIFT_IAM_ROLE_ARN', 'arn:aws:iam::bool')
        
        # dev.ini has dry_run = true
        dev_config = ConfigLoader.load(env='dev')
        assert dev_config.dry_run is True
        
        # staging.ini has dry_run = false
        staging_config = ConfigLoader.load(env='staging')
        assert staging_config.dry_run is False

    def test_int_parsing(self, monkeypatch):
        """Test that integer values are parsed correctly."""
        monkeypatch.setenv('S3_BUCKET', 'int-bucket')
        monkeypatch.setenv('REDSHIFT_HOST', 'int-host')
        monkeypatch.setenv('REDSHIFT_DATABASE', 'intdb')
        monkeypatch.setenv('REDSHIFT_USER', 'intuser')
        monkeypatch.setenv('REDSHIFT_PASSWORD', 'intpass')
        monkeypatch.setenv('REDSHIFT_IAM_ROLE_ARN', 'arn:aws:iam::int')
        
        config = ConfigLoader.load(env='dev')
        
        assert isinstance(config.redshift_port, int)
        assert config.redshift_port == 5439
