"""
Configuration Validator
Validates config.json against JSON schema.
"""

import json
from pathlib import Path
from typing import Optional
import jsonschema

from fs_utils import CONFIG_PATH

SCHEMA_PATH = Path(__file__).parent / "config_schema.json"


def _load_schema() -> dict:
    """Load the JSON schema for configuration validation."""
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def validate_config(config: dict) -> tuple[bool, Optional[str]]:
    """
    Validate configuration dictionary against schema.

    Returns:
        (is_valid, error_message)
    """
    try:
        schema = _load_schema()
        validate(instance=config, schema=schema)
        return True, None
    except ValidationError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Schema loading error: {str(e)}"


def get_validated_config() -> dict:
    """
    Read config.json with environment-specific overrides and validate it.
    Supports config.{ENV}.json files for environment-specific configuration.
    Environment variables can override config values using SEO_ prefix.

    Returns:
        Validated configuration dict with fallbacks to defaults.
    """
    import os
    env = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "production")).lower()
    config_path = CONFIG_PATH()
    env_config_path = config_path.with_name(f"config.{env}.json")

    # Start with defaults
    config = {
        "model": {
            "provider": "openrouter",
            "model": "anthropic/claude-3-haiku",
            "temperature": 0.7,
            "max_tokens": 4000
        },
        "pipeline": {
            "retry_attempts": 3,
            "timeout_seconds": 300,
            "parallel_stages": 1
        },
        "rate_limit": {
            "default_limits": ["60/minute", "1000/hour"]
        },
        "logging": {
            "level": "INFO",
            "structured": True
        }
    }

    # Load base config if exists
    if config_path.exists():
        try:
            with open(config_path) as f:
                base_config = json.load(f)
                _deep_update(config, base_config)
        except Exception as e:
            logger.error(f"Failed to load base config: {e}")

    # Load environment-specific config if exists (overrides base)
    if env_config_path.exists():
        try:
            with open(env_config_path) as f:
                env_config = json.load(f)
                _deep_update(config, env_config)
            logger.info(f"Loaded environment-specific config: {env_config_path.name}")
        except Exception as e:
            logger.error(f"Failed to load env config {env_config_path}: {e}")

    # Apply environment variable overrides (highest priority)
    _apply_env_overrides(config)

    # Validate final configuration
    is_valid, error = validate_config(config)
    if not is_valid:
        logger.error(f"Configuration validation failed: {error}")
        logger.warning("Using safe default configuration. Please fix config.json")
        return {
            "model": {
                "provider": "openrouter",
                "model": "anthropic/claude-3-haiku",
                "temperature": 0.7,
                "max_tokens": 4000
            },
            "pipeline": {
                "retry_attempts": 3,
                "timeout_seconds": 300,
                "parallel_stages": 1
            }
        }

    return config


def _deep_update(base: dict, updates: dict) -> None:
    """Recursively update nested dict."""
    for key, value in updates.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_update(base[key], value)
        else:
            base[key] = value


def _apply_env_overrides(config: dict) -> None:
    """Apply environment variable overrides using SEO_ prefix."""
    import os

    # Mapping of env vars to config paths
    mappings = {
        "SEO_MODEL": ("model", "model"),
        "SEO_TEMPERATURE": ("model", "temperature"),
        "SEO_MAX_TOKENS": ("model", "max_tokens"),
        "SEO_RETRY_ATTEMPTS": ("pipeline", "retry_attempts"),
        "SEO_TIMEOUT_SECONDS": ("pipeline", "timeout_seconds"),
        "SEO_PARALLEL_STAGES": ("pipeline", "parallel_stages"),
        "SEO_LOG_LEVEL": ("logging", "level"),
    }

    for env_var, (section, key) in mappings.items():
        value = os.environ.get(env_var)
        if value:
            try:
                # Type conversion based on key
                if key in ["temperature"]:
                    value = float(value)
                elif key in ["max_tokens", "retry_attempts", "timeout_seconds", "parallel_stages"]:
                    value = int(value)
                # Ensure section exists
                if section not in config:
                    config[section] = {}
                config[section][key] = value
                logger.info(f"Applied env override: {env_var}={value}")
            except ValueError as e:
                logger.warning(f"Invalid value for {env_var}: {value} - {e}")
