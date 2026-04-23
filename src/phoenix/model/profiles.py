from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Mapping, TypeAlias


ProviderName: TypeAlias = Literal["openai", "anthropic", "anthropic-compatible"]
TransportName: TypeAlias = Literal["openai-chat", "anthropic-messages"]

CONFIG_DIR = Path.home() / ".config" / "phoenix"
KEYS_ENV = CONFIG_DIR / "keys.env"
MODELS_TOML = CONFIG_DIR / "models.toml"

_REQUIRED_FIELDS = ("provider", "model", "base_url", "api_key_env", "role")


@dataclass(frozen=True)
class ModelProfile:
    name: str
    provider: ProviderName
    model: str
    base_url: str
    api_key_env: str
    role: str
    extras: dict[str, object] = field(default_factory=dict)


def load_env_file(path: Path = KEYS_ENV) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_profiles(path: Path = MODELS_TOML) -> dict[str, ModelProfile]:
    if not path.exists():
        raise RuntimeError(f"models.toml not found: {path}")

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    raw_profiles = data.get("profiles")
    if not isinstance(raw_profiles, dict) or not raw_profiles:
        raise RuntimeError(f"models.toml has no [profiles] entries: {path}")

    profiles: dict[str, ModelProfile] = {}
    for name, raw_profile in raw_profiles.items():
        if not isinstance(raw_profile, dict):
            raise RuntimeError(f"profile {name!r} must be a table")
        missing = [field_name for field_name in _REQUIRED_FIELDS if field_name not in raw_profile]
        if missing:
            missing_text = ", ".join(missing)
            raise RuntimeError(f"profile {name!r} is missing required fields: {missing_text}")
        provider = str(raw_profile["provider"])
        if provider not in {"openai", "anthropic", "anthropic-compatible"}:
            raise RuntimeError(f"profile {name!r} has unsupported provider: {provider}")
        extras = {key: value for key, value in raw_profile.items() if key not in _REQUIRED_FIELDS}
        profiles[name] = ModelProfile(
            name=name,
            provider=provider,
            model=str(raw_profile["model"]),
            base_url=str(raw_profile["base_url"]).rstrip("/"),
            api_key_env=str(raw_profile["api_key_env"]),
            role=str(raw_profile["role"]),
            extras=extras,
        )
    return profiles


def load_profile(name: str, path: Path = MODELS_TOML) -> ModelProfile:
    profiles = load_profiles(path)
    try:
        return profiles[name]
    except KeyError as exc:
        known = ", ".join(sorted(profiles))
        raise RuntimeError(f"unknown model profile {name!r}; known profiles: {known}") from exc


def require_api_key(profile: ModelProfile, environ: Mapping[str, str] | None = None) -> str:
    if not profile.api_key_env:
        return ""

    env = environ or os.environ
    api_key = env.get(profile.api_key_env, "").strip()
    if not api_key:
        raise RuntimeError(
            f"missing required api key env {profile.api_key_env!r} for profile {profile.name!r}"
        )
    return api_key


def infer_transport(profile: ModelProfile) -> TransportName:
    base_url = profile.base_url.lower()
    if profile.provider == "openai":
        return "openai-chat"
    if profile.provider == "anthropic":
        return "anthropic-messages"
    if "/anthropic" in base_url and not base_url.endswith("/coding"):
        return "anthropic-messages"
    return "openai-chat"


def openai_chat_endpoint(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if not normalized.endswith("/v1"):
        normalized = f"{normalized}/v1"
    return f"{normalized}/chat/completions"


def anthropic_messages_endpoint(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/messages"):
        return normalized
    if not normalized.endswith("/v1"):
        normalized = f"{normalized}/v1"
    return f"{normalized}/messages"


__all__ = [
    "CONFIG_DIR",
    "KEYS_ENV",
    "MODELS_TOML",
    "ModelProfile",
    "ProviderName",
    "TransportName",
    "anthropic_messages_endpoint",
    "infer_transport",
    "load_env_file",
    "load_profile",
    "load_profiles",
    "openai_chat_endpoint",
    "require_api_key",
]
