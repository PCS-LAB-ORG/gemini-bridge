"""Tests for gemini_bridge/config.py — Config model, load_config(), ConfigError."""

import json
import tempfile
from pathlib import Path

import pytest
from gemini_bridge.config import Config, ConfigError, load_config


def _write_config(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data))


def test_load_config_minimal() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = Path(tmp) / "config.json"
        _write_config(cfg_path, {"project": "my-project"})
        cfg = load_config(cfg_path)
    assert cfg.project == "my-project"
    assert cfg.location == "global"
    assert cfg.model == "gemini-2.5-flash"
    assert cfg.default_thinking == "medium"
    assert cfg.auth.method == "adc"


def test_load_config_full() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = Path(tmp) / "config.json"
        _write_config(
            cfg_path,
            {
                "project": "proj",
                "location": "us-east4",
                "model": "gemini-2.5-pro",
                "default_thinking": "high",
                "transcript_dir": "/tmp/tx",
                "auth": {"method": "env"},
            },
        )
        cfg = load_config(cfg_path)
    assert cfg.location == "us-east4"
    assert cfg.model == "gemini-2.5-pro"
    assert cfg.default_thinking == "high"
    assert cfg.auth.method == "env"


def test_load_config_missing_file() -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(Path("/nonexistent/path/config.json"))


def test_load_config_invalid_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = Path(tmp) / "config.json"
        cfg_path.write_text("{invalid json")
        with pytest.raises(ConfigError, match="not valid JSON"):
            load_config(cfg_path)


def test_load_config_missing_project() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = Path(tmp) / "config.json"
        _write_config(cfg_path, {"location": "us-central1"})
        with pytest.raises(ConfigError, match="validation failed"):
            load_config(cfg_path)


def test_load_config_bad_model_family() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = Path(tmp) / "config.json"
        _write_config(cfg_path, {"project": "p", "model": "gpt-4"})
        with pytest.raises(ConfigError, match="validation failed"):
            load_config(cfg_path)


def test_config_model_gemini3_accepted() -> None:
    cfg = Config(project="p", model="gemini-3.5-flash")
    assert cfg.model == "gemini-3.5-flash"
    assert cfg.location == "global"


def test_config_gemini3_with_region_rejected() -> None:
    with pytest.raises(Exception, match="only supports location"):
        Config(project="p", model="gemini-3.5-flash", location="us-central1")


def test_config_gemini2_with_region_accepted() -> None:
    cfg = Config(project="p", model="gemini-2.5-flash", location="us-central1")
    assert cfg.location == "us-central1"


def test_config_gemini2_global_accepted() -> None:
    cfg = Config(project="p", model="gemini-2.5-flash", location="global")
    assert cfg.location == "global"


def test_config_keychain_auth_defaults() -> None:
    cfg = Config(project="p", auth={"method": "keychain"})
    assert cfg.auth.method == "keychain"
    assert cfg.auth.keychain_service == "gemini-bridge"
    assert cfg.auth.keychain_account == "vertex-sa"


def test_adc_config_keychain_fields_are_none() -> None:
    from gemini_bridge.config import AuthConfig

    cfg = AuthConfig(method="adc")
    assert cfg.keychain_service is None
    assert cfg.keychain_account is None


def test_env_config_keychain_fields_are_none() -> None:
    from gemini_bridge.config import AuthConfig

    cfg = AuthConfig(method="env")
    assert cfg.keychain_service is None
    assert cfg.keychain_account is None


def test_keychain_explicit_service_account_preserved() -> None:
    from gemini_bridge.config import AuthConfig

    cfg = AuthConfig(method="keychain", keychain_service="my-svc", keychain_account="my-acct")
    assert cfg.keychain_service == "my-svc"
    assert cfg.keychain_account == "my-acct"


def test_api_key_method_no_project_accepted() -> None:
    cfg = Config(auth={"method": "api_key"})
    assert cfg.auth.method == "api_key"
    assert cfg.project is None


def test_api_key_env_default() -> None:
    from gemini_bridge.config import AuthConfig

    cfg = AuthConfig(method="api_key")
    assert cfg.api_key_env == "GEMINI_API_KEY"


def test_api_key_custom_env_preserved() -> None:
    from gemini_bridge.config import AuthConfig

    cfg = AuthConfig(method="api_key", api_key_env="GOOGLE_API_KEY")
    assert cfg.api_key_env == "GOOGLE_API_KEY"


def test_vertex_methods_require_project() -> None:
    for method in ("adc", "env", "keychain"):
        with pytest.raises(Exception, match="'project' is required"):
            Config(auth={"method": method})


def test_api_key_location_validator_skipped() -> None:
    cfg = Config(auth={"method": "api_key"}, model="gemini-3.5-flash", location="us-central1")
    assert cfg.location == "us-central1"


def test_vertex_gemini3_non_global_still_rejected() -> None:
    with pytest.raises(Exception, match="only supports location"):
        Config(project="p", model="gemini-3.5-flash", location="us-central1")
