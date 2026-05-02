"""Configuration management for Mnemonic."""

import os
from pathlib import Path
from typing import Any

import yaml


class Config:
    """Configuration loaded from config.yaml with environment variable substitution."""

    def __init__(self, config_path: str | Path | None = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        self._raw = self._load_yaml(config_path)
        self._config = self._substitute_env(self._raw)
    
    def _load_yaml(self, path: Path) -> dict:
        with open(path) as f:
            return yaml.safe_load(f)
    
    def _substitute_env(self, obj: Any) -> Any:
        """Recursively substitute ${VAR} and ${VAR:-default} with environment variables."""
        if isinstance(obj, dict):
            return {k: self._substitute_env(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
            inner = obj[2:-1]
            # Support ${VAR:-default} syntax
            if ":-" in inner:
                var_name, default = inner.split(":-", 1)
                return os.getenv(var_name, default)
            return os.getenv(inner, obj)
        return obj
    
    def __getitem__(self, key: str) -> Any:
        return self._config[key]
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)
    
    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        db = self._config["database"]
        return (
            f"postgresql://{db['user']}:{db['password']}"
            f"@{db['host']}:{db['port']}/{db['name']}"
        )
    
    @property
    def async_database_url(self) -> str:
        """Construct async PostgreSQL connection URL."""
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://")


# Global config instance
config = Config()
