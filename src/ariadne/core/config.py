"""Configuration parsing and validation for ariadne.toml (v1)."""

from pathlib import Path
import tomllib
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
from ariadne.core.errors import ConfigError


class ProjectConfig(BaseModel):
    name: str = "AriadneProject"
    command: str
    startup_timeout_ms: int = Field(default=5000, ge=100)
    seed_timeout_ms: int = Field(default=500, ge=10)


class SeedsConfig(BaseModel):
    base_seed: int = 1337
    count: int = Field(default=1000, gt=0)


class ReachableRuleConfig(BaseModel):
    from_point: str = Field(default="@", alias="from")
    to_point: str = Field(default=">", alias="to")


class RulesConfig(BaseModel):
    reachable: Optional[ReachableRuleConfig] = None
    connected_walkable: bool = False
    key_before_door: bool = False


class CustomCheckConfig(BaseModel):
    name: str
    command: str


class AriadneConfig(BaseModel):
    schema_version: int = Field(default=1)
    project: ProjectConfig
    seeds: SeedsConfig = Field(default_factory=SeedsConfig)
    legend: Dict[str, str] = Field(default_factory=lambda: {
        "#": "wall",
        ".": "floor",
        "@": "start",
        ">": "exit",
    })
    rules: RulesConfig = Field(default_factory=RulesConfig)
    custom_check: List[CustomCheckConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_schema_version(self) -> "AriadneConfig":
        if self.schema_version != 1:
            raise ValueError(f"Unsupported schema_version: {self.schema_version}. Only version 1 is supported.")
        return self


def load_config(path: Path | str = "ariadne.toml") -> AriadneConfig:
    """Load and validate ariadne.toml configuration file."""
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Configuration file not found: {config_path.resolve()}")

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        raise ConfigError(f"TOML parse error in {config_path}: {e}") from e

    try:
        return AriadneConfig.model_validate(data)
    except Exception as e:
        raise ConfigError(f"Configuration validation failed in {config_path}: {e}") from e
