"""Backend integration contracts for the wealth-intelligence workspace.

This package contains provider-neutral contracts and safe runtime configuration.
It deliberately contains no database-writing service, provider adapter, or
LLM integration.
"""

from .config import ConfigurationError, RuntimeConfig, load_runtime_config

__all__ = ["ConfigurationError", "RuntimeConfig", "load_runtime_config"]
