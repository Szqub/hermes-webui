"""Endpoint ownership survives the picker wire representation (#7955)."""
import pytest


@pytest.fixture
def config(monkeypatch):
    from api import config as module
    # Replace, never reload or mutate, the shared snapshot. monkeypatch restores
    # its exact object identity for the next file in this process.
    previous = module.cfg
    with monkeypatch.context() as isolated:
        isolated.setattr(module, "cfg", {})
        isolated.setattr(module, "_is_plugin_model_provider", lambda _: False)
        yield module
    assert module.cfg is previous


BASE = "http://127.0.0.1:11434/v1"
OTHER = "http://gpu-box:8000/v1"
LOCALS = ["ollama", "vllm", "lmstudio", "llamacpp", "local"]


@pytest.mark.parametrize("active", LOCALS)
@pytest.mark.parametrize("shape", ["custom_providers", "providers"])
@pytest.mark.parametrize("mid", ["mistral-7b", "qwen3.8:27b", "qwen3:8b"])
def test_configured_endpoint_is_authoritative(config, active, shape, mid):
    config.cfg.update({"model": {"provider": active, "base_url": BASE, "default": "llama3"}})
    row = {"name": "qwen3" if mid == "qwen3:8b" else "lab", "base_url": OTHER, "api_key": "sk-synthetic", "models": [mid]}
    config.cfg[shape] = [row] if shape == "custom_providers" else {"lab": row}
    config.cfg.setdefault("providers", {})[active] = {"base_url": "http://other:9999/v1"}
    wire = config.model_with_provider_context(mid, "custom")
    assert wire == "@!:" + mid
    assert config._parse_provider_qualified_model_id(wire) == (mid, "custom")
    assert config.resolve_model_provider(wire) == (mid, "custom", BASE)
    assert config.resolve_custom_provider_connection("custom") == (None, None)


def test_legacy_local_named_record_does_not_supply_key(config):
    config.cfg.update({"model": {"provider": "local", "base_url": BASE},
                       "custom_providers": [{"name": "local", "base_url": "http://named:7777/v1",
                                             "api_key": "sk-synthetic"}]})
    wire = config.model_with_provider_context("qwen3:8b", "custom")
    assert config.resolve_model_provider(wire) == ("qwen3:8b", "custom", BASE)
    assert config.resolve_custom_provider_connection("custom") == (None, None)


IDS = ["custom", "custom:a:b", "Custom:Lab", "+x", "%2Bx", "foo bar", "foo:bar:baz",
       "custom:!.example:8080", "custom:%21.example:8080", "custom:a:123", "custom:host:99999",
       "", "  ", "  Custom:Lab  ", 123, None, "x" * 10000, "!", "!:payload", "a!b", "@!:"]


@pytest.mark.parametrize("provider", IDS, ids=lambda value: str(value)[:40])
def test_generic_catalog_cannot_emit_reserved_token(config, provider):
    mid = "payload"
    wire = config._apply_provider_prefix([{"id": mid}], provider, "unrelated")[0]["id"]
    assert not wire.startswith("@!:")
    canonical = str(provider or "").strip().lower()
    if not canonical:
        assert wire == mid
    else:
        assert config._parse_provider_qualified_model_id(wire) == (mid, canonical)
        config.cfg.update({"model": {"provider": "ollama", "base_url": BASE},
                           "providers": {provider: {"base_url": OTHER}}})
        assert config.resolve_model_provider(wire) == (mid, canonical, OTHER)


@pytest.mark.parametrize("provider", ["!", "%21", "+x", "%2Bx", "custom:a:b", "foo:bar:baz"])
def test_escaped_generic_suffix_is_opaque(config, provider):
    mid = "vendor/Qwen:8b:free"
    wire = config._encode_provider_qualified_model_id(mid, provider)
    assert not wire.startswith("@!:")
    assert config._parse_provider_qualified_model_id(wire) == (mid, provider.lower())


def test_dedup_escapes_marker(config):
    groups = [{"provider_id": "", "models": [{"id": "x", "label": "x"}]},
              {"provider_id": "!", "models": [{"id": "x", "label": "x"}]}]
    config._deduplicate_model_ids(groups)
    assert groups[1]["models"][0]["id"] == "@%21:x"


def test_mixed_case_configured_provider_with_slash(config):
    config.cfg.update({"model": {"provider": "ollama", "base_url": BASE},
                       "providers": {"Custom:Lab": {"base_url": OTHER}}})
    wire = config.model_with_provider_context("vendor/Qwen:8b", "custom:lab")
    assert config.resolve_model_provider(wire) == ("vendor/Qwen:8b", "custom:lab", OTHER)


@pytest.mark.parametrize("wire, data", [
    ("@!:", {"model": {"provider": "ollama", "base_url": BASE}}),
    ("@!:x", {"model": {"provider": "ollama"}}),
])
def test_reserved_route_never_falls_back(config, wire, data):
    config.cfg.update(data)
    with pytest.raises(ValueError):
        config.resolve_model_provider(wire)


def test_early_route_does_not_scan_records(config, monkeypatch):
    config.cfg.update({"model": {"provider": "local", "base_url": BASE}})
    def forbidden(*args, **kwargs):
        pytest.fail("dedicated route consulted a generic record")
    monkeypatch.setattr(config, "_resolve_configured_provider_id", forbidden)
    monkeypatch.setattr(config, "_parse_provider_qualified_model_id", forbidden)
    monkeypatch.setattr(config, "_get_provider_base_url", forbidden)
    assert config.resolve_model_provider("@!:qwen3:8b") == ("qwen3:8b", "custom", BASE)


def test_named_active_still_fails_closed(config):
    config.cfg.update({"model": {"provider": "custom:missing", "base_url": BASE}})
    assert config.model_with_provider_context("x", "custom") == "@custom:x"
    with pytest.raises(ValueError):
        config.resolve_model_provider("@!:x")
    assert config.resolve_model_provider("@custom:other:x") == ("x", "custom:other", None)


def test_legacy_ambiguity_retains_named_route(config):
    config.cfg.update({"model": {"provider": "ollama", "base_url": BASE},
                       "custom_providers": [{"name": "qwen3", "base_url": OTHER}]})
    assert config.resolve_model_provider("@custom:qwen3:8b") == ("8b", "custom:qwen3", OTHER)
    assert config.resolve_model_provider(config.model_with_provider_context("qwen3:8b", "custom")) == ("qwen3:8b", "custom", BASE)


@pytest.mark.parametrize("provider", ["ollama", "local", "custom-configured"])
def test_explicit_generic_provider_unchanged(config, provider):
    config.cfg.update({"model": {"provider": "ollama", "base_url": BASE},
                       "providers": {provider: {"base_url": OTHER}}})
    assert config.resolve_model_provider(f"@{provider}:llama3") == ("llama3", provider, OTHER)


def test_ollama_lane_and_endpoint_slug_unchanged(config):
    config.cfg.update({"model": {"provider": "ollama", "base_url": BASE, "default": "llama3"}})
    assert config.resolve_model_provider(config.model_with_provider_context("llama3", "ollama")) == ("llama3", "ollama", BASE)
    assert config.resolve_model_provider("@custom:127.0.0.1:11434:llama3") == ("llama3", "ollama", BASE)


def test_all_registered_provider_ids_stay_generic(config):
    for provider in set(config._PROVIDER_MODELS) | set(config._PROVIDER_DISPLAY):
        wire = config._encode_provider_qualified_model_id("payload", provider)
        assert not wire.startswith("@!:")
        assert config._parse_provider_qualified_model_id(wire) == ("payload", provider)


def test_shared_consumers_keep_dedicated_suffix(config):
    from api import profiles, gateway_chat, routes
    wire = "@!:vendor/Qwen:8b:free"
    assert profiles._split_webui_provider_model_value(wire, None) == ("vendor/Qwen:8b:free", "custom")
    assert gateway_chat._gateway_model_field(wire) == "vendor/Qwen:8b:free"
    assert routes._split_provider_qualified_model(wire) == ("vendor/Qwen:8b:free", "custom")
    assert routes._resolve_compatible_session_model_state(wire, "custom") == (wire, "custom", False)
    assert config._provider_native_auxiliary_model("custom", wire) == "vendor/Qwen:8b:free"
    assert config._strip_provider_hint_for_reasoning(wire, "custom") == "vendor/Qwen:8b:free"


@pytest.mark.parametrize("wire, expected", [
    ("@custom:backup:a:b:c", ("a:b:c", "custom:backup")),
    ("@custom:localhost:11434:a:b:c", ("a:b:c", "custom:localhost:11434")),
    ("@custom:payload", ("payload", "custom")),
])
def test_legacy_custom_grammar_matches_browser(config, wire, expected):
    assert config._parse_provider_qualified_model_id(wire) == expected


@pytest.mark.parametrize("active", LOCALS)
def test_catalog_advertises_the_reserved_lane(config, active):
    """A picker option for the configured lane must not use the named spelling.

    `@custom:<id>` is also the named-record form, so advertising it in the
    Custom group would send a colon-bearing identifier to that record instead
    of the configured endpoint.
    """
    config.cfg.update({"model": {"provider": active, "base_url": BASE, "default": "llama3"}})
    wire = config._encode_catalog_route("qwen3:8b", "custom")
    assert wire == "@!:qwen3:8b"
    assert config.resolve_model_provider(wire) == ("qwen3:8b", "custom", BASE)
    # A named record, and every other provider, keep the generic spelling.
    assert config._encode_catalog_route("qwen3:8b", "custom:backup") == "@custom:backup:qwen3:8b"
    assert config._encode_catalog_route("qwen3:8b", "openai") == "@openai:qwen3:8b"


def test_catalog_keeps_generic_spelling_without_an_endpoint(config):
    """No configured endpoint means no reserved lane, so nothing changes."""
    config.cfg.update({"model": {"provider": "custom", "default": "llama3"}})
    assert config._configured_custom_lane_is_reserved() is False
    assert config._encode_catalog_route("qwen3:8b", "custom") == "@custom:qwen3:8b"
