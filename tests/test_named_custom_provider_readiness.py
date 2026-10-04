"""Named custom-provider status and credential reads use the routing config."""

import pytest

from api import config, onboarding, providers


@pytest.fixture
def custom_config(monkeypatch, tmp_path):
    cfg = {
        "model": {"provider": "custom:local", "default": "local-model"},
        "providers": {"local": {"base_url": "http://127.0.0.1:8000/v1"}},
    }
    monkeypatch.setattr(config, "get_config", lambda: cfg)
    monkeypatch.setattr(providers, "get_config", lambda: cfg)
    monkeypatch.setattr(onboarding, "_HERMES_FOUND", True)
    monkeypatch.setattr(onboarding, "_get_active_hermes_home", lambda: tmp_path)
    monkeypatch.setattr(providers, "_get_hermes_home", lambda: tmp_path)
    monkeypatch.setattr(config, "_custom_record_pool_runtime", lambda *_: None)
    monkeypatch.setattr(config, "_has_explicit_pool_credentials", lambda *_: False)
    monkeypatch.setattr(providers, "_pool_entry_payloads", lambda *_: [])
    monkeypatch.setattr(config._thread_ctx, "env", {}, raising=False)
    monkeypatch.setattr(config._thread_ctx, "block_process_env_fallback", True, raising=False)
    return cfg


def test_named_keyless_endpoint_is_ready(custom_config):
    status = onboarding._status_from_runtime(custom_config, imports_ok=True)
    assert status["provider_ready"] is True
    assert status["chat_ready"] is True
    assert status["setup_state"] == "ready"
    assert status["current_base_url"] == "http://127.0.0.1:8000/v1"


@pytest.mark.parametrize("field", ["key_env", "api_key_env"])
def test_named_endpoint_reads_profile_credential(custom_config, monkeypatch, field):
    custom_config["providers"]["local"][field] = "LOCAL_ENDPOINT_KEY"
    monkeypatch.setenv("LOCAL_ENDPOINT_KEY", "ambient-placeholder")
    monkeypatch.setattr(config._thread_ctx, "env", {"LOCAL_ENDPOINT_KEY": "profile-placeholder"})

    assert providers._get_provider_api_key("custom:local") == "profile-placeholder"
    assert providers._provider_has_key("custom:local") is True
    assert onboarding._status_from_runtime(custom_config, imports_ok=True)["chat_ready"] is True


@pytest.mark.parametrize("field", ["key_env", "api_key_env"])
def test_unset_named_credential_is_not_keyless(custom_config, monkeypatch, field):
    custom_config["providers"]["local"][field] = "LOCAL_ENDPOINT_KEY"
    monkeypatch.setenv("LOCAL_ENDPOINT_KEY", "ambient-placeholder")

    assert providers._get_provider_api_key("custom:local") is None
    assert providers._provider_has_key("custom:local") is False
    assert onboarding._status_from_runtime(custom_config, imports_ok=True)["chat_ready"] is False


def test_legacy_named_endpoint_reads_key_env(custom_config, monkeypatch):
    custom_config["providers"] = {}
    custom_config["custom_providers"] = [{
        "name": "local", "base_url": "http://127.0.0.1:8000/v1",
        "key_env": "LOCAL_ENDPOINT_KEY",
    }]
    monkeypatch.setattr(config._thread_ctx, "env", {"LOCAL_ENDPOINT_KEY": "profile-placeholder"})
    assert providers._get_provider_api_key("custom:local") == "profile-placeholder"
    assert providers._provider_has_key("custom:local") is True


@pytest.mark.parametrize("case", ["missing", "disabled", "ambiguous", "no_endpoint"])
def test_unavailable_named_endpoint_stays_unready(custom_config, case):
    if case == "missing":
        custom_config["model"]["provider"] = "custom:missing"
    elif case == "disabled":
        custom_config["providers"]["local"]["enabled"] = False
    elif case == "ambiguous":
        custom_config["providers"]["other"] = {
            "name": "local", "base_url": "http://127.0.0.1:8001/v1",
        }
    else:
        custom_config["providers"]["local"].pop("base_url")
        custom_config["providers"]["local"]["api_key"] = "profile-placeholder"
    status = onboarding._status_from_runtime(custom_config, imports_ok=True)
    assert status["chat_ready"] is False
    if case == "no_endpoint":
        assert status["provider_note_key"] == "onboarding_notice_custom_base_url_required"
    else:
        assert status["provider_note_key"] == "onboarding_notice_custom_record_required"
