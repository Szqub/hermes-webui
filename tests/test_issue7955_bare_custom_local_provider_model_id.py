"""Regression tests for issue #7955 — ``model.provider: ollama`` makes every
Custom-group model fail with ``custom:<tag-prefix> not configured``.

With ``model.provider: ollama`` and a ``base_url`` set, the model picker
collapses the active provider to the generic ``custom`` slug
(``_resolve_configured_provider_id``) and the session stores that collapsed
value in ``model_provider``. ``model_with_provider_context()`` then compared
the session's ``custom`` against the RAW configured name ``ollama``, the
equality check missed, and a model id without a slash was minted into a
synthetic ``@custom:<model>`` hint.

For a colon-bearing model id that hint is corrupted on the way back through
``_parse_provider_qualified_model_id()``, which reads the hint's first colon
token as a NAME custom-provider slug:

    model_with_provider_context("qwen3.8:27b", "custom")
        -> "@custom:qwen3.8:27b"
    resolve_model_provider("@custom:qwen3.8:27b")
        -> ("27b", "custom:qwen3.8", None)      # slug "qwen3.8", model "27b"

No ``custom_providers[]`` entry owns ``custom:qwen3.8``, so the request fails
as an unconfigured custom provider.

A bare ``custom`` (and its legacy ``local`` alias) is the generic
OpenAI-compatible pseudo-provider the picker falls back to when the endpoint
comes from ``model.base_url``. The model must stay bare only when both sides
name the same endpoint; when ``providers.custom`` / ``providers.local``
declares its own ``base_url``, ``@custom:<model>`` IS a route and the hint is
kept. Named ``custom:<slug>`` providers are real routes too and keep their
explicit hint.
"""

import pytest

import api.config as config


def _set_config(provider=None, base_url=None, default=None, custom_providers=None):
    old_cfg = dict(config.cfg)
    model_cfg = {}
    if provider:
        model_cfg["provider"] = provider
    if base_url:
        model_cfg["base_url"] = base_url
    if default:
        model_cfg["default"] = default
    config.cfg["model"] = model_cfg
    config.cfg["providers"] = {}
    config.cfg["custom_providers"] = custom_providers or []
    return old_cfg


def _restore(old_cfg):
    config.cfg.clear()
    config.cfg.update(old_cfg)


# ── The reported bug: ollama + base_url under the collapsed ``custom`` slug ──


def test_reported_colon_model_stays_bare():
    """``qwen3.8:27b`` must NOT be minted into ``@custom:qwen3.8:27b``."""
    old = _set_config(
        provider="ollama",
        base_url="http://127.0.0.1:11434/v1",
        default="qwen3.8:27b",
    )
    try:
        encoded = config.model_with_provider_context("qwen3.8:27b", "custom")
        assert encoded == "qwen3.8:27b", (
            "bare `custom` must keep the model bare so the configured "
            f"base_url routes it, got {encoded!r}"
        )
    finally:
        _restore(old)


def test_reported_colon_model_resolves_to_configured_endpoint():
    """The resolved tuple must carry the configured provider + base_url intact."""
    old = _set_config(
        provider="ollama",
        base_url="http://127.0.0.1:11434/v1",
        default="qwen3.8:27b",
    )
    try:
        encoded = config.model_with_provider_context("qwen3.8:27b", "custom")
        model, provider, base_url = config.resolve_model_provider(encoded)
        assert model == "qwen3.8:27b", (
            f"model id must survive intact, got {model!r}"
        )
        assert provider == "ollama", (
            f"configured provider must stay in charge, got {provider!r}"
        )
        assert base_url == "http://127.0.0.1:11434/v1"
    finally:
        _restore(old)


def test_pre_fix_hint_is_the_corrupted_form():
    """Pin the failure mode the fix removes, as a relation rather than a shape.

    The synthetic hint the old code produced does not round-trip: resolving it
    yields a different model id than the caller passed, and a named provider
    slug that no ``custom_providers[]`` entry owns. Asserted relationally so a
    future hardening of the parser does not break this test for no reason.
    """
    old = _set_config(
        provider="ollama",
        base_url="http://127.0.0.1:11434/v1",
        default="qwen3.8:27b",
    )
    try:
        model, provider, _base_url = config.resolve_model_provider(
            "@custom:qwen3.8:27b"
        )
        assert model != "qwen3.8:27b", (
            "the synthetic hint is expected to lose model-id fidelity; "
            f"resolving it returned {model!r}"
        )
        assert provider not in {"ollama", "custom"}, (
            "the synthetic hint is expected to resolve to a named custom-provider "
            f"slug, got {provider!r}"
        )
        assert config.cfg.get("custom_providers", []) == []
        # …and the fix must not produce it any more.
        assert config.model_with_provider_context(
            "qwen3.8:27b", "custom"
        ) != "@custom:qwen3.8:27b"
    finally:
        _restore(old)


# ── The rest of the bug class: a bare ``custom`` / ``local`` session that
#    names the same endpoint as the configured provider ──────────────────────


def test_empty_config_provider_with_base_url_stays_bare():
    """A config that names no provider but sets a ``base_url`` still puts the
    session in the Custom group, so the bare slug must stay bare there too."""
    old = _set_config(
        base_url="http://127.0.0.1:11434/v1",
        default="qwen3.8:27b",
    )
    try:
        encoded = config.model_with_provider_context("qwen3.8:27b", "custom")
        assert encoded == "qwen3.8:27b", f"got {encoded!r}"
        model, _provider, base_url = config.resolve_model_provider(encoded)
        assert model == "qwen3.8:27b"
        assert base_url == "http://127.0.0.1:11434/v1"
    finally:
        _restore(old)


def test_legacy_local_session_provider_stays_bare():
    """``local`` is the legacy alias of ``custom`` and names the same endpoint."""
    old = _set_config(
        provider="ollama",
        base_url="http://127.0.0.1:11434/v1",
        default="qwen3.8:27b",
    )
    try:
        encoded = config.model_with_provider_context("qwen3.8:27b", "local")
        assert encoded == "qwen3.8:27b", f"got {encoded!r}"
        model, provider, base_url = config.resolve_model_provider(encoded)
        assert model == "qwen3.8:27b"
        assert base_url == "http://127.0.0.1:11434/v1"
    finally:
        _restore(old)


@pytest.mark.parametrize(
    "config_provider",
    ["ollama", "lmstudio", "lm-studio", "vllm", "llamacpp", "tabby", "local"],
)
def test_bare_custom_stays_bare_for_local_config_names(config_provider):
    """A bare ``custom`` session against representative local-server configs.

    The rule keys on the configured provider naming the same endpoint as the
    session's bare ``custom``, so every local-server config here stays bare.
    ``ollama`` / ``vllm`` / ``llamacpp`` / ``local`` are collapsed to ``custom``
    by the alias tables when the agent tree is importable, and the WebUI's own
    local-server table covers them when it is not; the rest pin the same state
    for a name the local-server table does not list.
    """
    old = _set_config(
        provider=config_provider,
        base_url="http://127.0.0.1:11434/v1",
        default="qwen3.8:27b",
    )
    try:
        encoded = config.model_with_provider_context("qwen3.8:27b", "custom")
        assert encoded == "qwen3.8:27b", (
            f"{config_provider}: expected bare passthrough, got {encoded!r}"
        )
    finally:
        _restore(old)


def test_declared_custom_endpoint_keeps_its_hint():
    """``providers.custom`` with a ``base_url`` is a route of its own.

    A session that selected the custom proxy must keep the ``@custom:`` hint even
    when the profile default is some other provider: a bare id would fall through
    to that default and reach the wrong backend.
    """
    old = _set_config(provider="anthropic", default="foo")
    config.cfg["providers"] = {"custom": {"base_url": "https://proxy.example/v1"}}
    try:
        encoded = config.model_with_provider_context("foo", "custom")
        assert encoded == "@custom:foo", f"got {encoded!r}"
        assert config.resolve_model_provider(encoded) == (
            "foo",
            "custom",
            "https://proxy.example/v1",
        )
        # A slash id is the same route.
        encoded = config.model_with_provider_context("vendor/foo", "custom")
        assert encoded == "@custom:vendor/foo", f"got {encoded!r}"
        assert config.resolve_model_provider(encoded) == (
            "vendor/foo",
            "custom",
            "https://proxy.example/v1",
        )
    finally:
        _restore(old)


def test_declared_local_endpoint_keeps_its_hint():
    """The legacy ``local`` slug with its own endpoint behaves the same way."""
    old = _set_config(provider="anthropic", default="foo")
    config.cfg["providers"] = {"local": {"base_url": "https://local.example/v1"}}
    try:
        encoded = config.model_with_provider_context("foo", "local")
        assert encoded == "@local:foo", f"got {encoded!r}"
    finally:
        _restore(old)


def test_endpoint_declared_under_either_slug_keeps_its_hint():
    """``custom`` and ``local`` are the same pseudo-provider, so an endpoint
    declared under either name is a route for both."""
    old = _set_config(provider="anthropic", default="foo")
    config.cfg["providers"] = {"custom": {"base_url": "https://proxy.example/v1"}}
    try:
        assert config.model_with_provider_context("foo", "local") == "@local:foo"
    finally:
        _restore(old)
    old = _set_config(provider="anthropic", default="foo")
    config.cfg["providers"] = {"local": {"base_url": "https://local.example/v1"}}
    try:
        assert config.model_with_provider_context("foo", "custom") == "@custom:foo"
    finally:
        _restore(old)


def test_slash_model_under_local_config_unchanged():
    """No regression for slash-bearing local model ids."""
    old = _set_config(
        provider="ollama",
        base_url="http://127.0.0.1:11434/v1",
        default="unsloth/gemma-4-12b-it-GGUF:UD-Q4_K_XL",
    )
    try:
        encoded = config.model_with_provider_context(
            "unsloth/gemma-4-12b-it-GGUF:UD-Q4_K_XL", "custom"
        )
        assert encoded == "unsloth/gemma-4-12b-it-GGUF:UD-Q4_K_XL"
        model, provider, base_url = config.resolve_model_provider(encoded)
        assert model == "unsloth/gemma-4-12b-it-GGUF:UD-Q4_K_XL"
        assert provider == "ollama"
        assert base_url == "http://127.0.0.1:11434/v1"
    finally:
        _restore(old)


# ── Guards: the fix must not widen the bare passthrough ──────────────────────


def test_named_custom_slug_still_gets_its_hint():
    """A named ``custom:<slug>`` is a real route and keeps its explicit hint."""
    old = _set_config(
        provider="ollama",
        base_url="http://127.0.0.1:11434/v1",
        custom_providers=[
            {"name": "my-proxy", "base_url": "https://proxy.example/v1"}
        ],
    )
    try:
        encoded = config.model_with_provider_context("qwen3.8:27b", "custom:my-proxy")
        assert encoded == "@custom:my-proxy:qwen3.8:27b", (
            f"named custom slug must keep its hint, got {encoded!r}"
        )
        model, provider, base_url = config.resolve_model_provider(encoded)
        assert (model, provider) == ("qwen3.8:27b", "custom:my-proxy")
        assert base_url == "https://proxy.example/v1"
    finally:
        _restore(old)


def test_configured_custom_equality_still_returns_bare():
    """``provider == config_provider == 'custom'`` keeps the original path."""
    old = _set_config(
        provider="custom",
        base_url="https://proxy.example/v1",
        default="x-ai/grok-4.5",
    )
    try:
        encoded = config.model_with_provider_context("x-ai/grok-4.5", "custom")
        assert encoded == "x-ai/grok-4.5", f"got {encoded!r}"
    finally:
        _restore(old)


def test_non_dict_provider_entry_does_not_break_other_routes():
    """A malformed ``providers.<slug>`` entry must not turn an unrelated route
    into a crash: the guard is only evaluated for a bare ``custom``/``local``
    session, and reads the entry tolerantly."""
    for providers in (
        {"custom": "http://proxy.example/v1"},
        {"local": "http://proxy.example/v1"},
        {"custom": None},
        {"custom": {"base_url": None}},
    ):
        old = _set_config(provider="openai", default="gpt-x")
        config.cfg["providers"] = providers
        try:
            assert (
                config.model_with_provider_context("claude-x", "openrouter")
                == "@openrouter:claude-x"
            ), providers
            assert (
                config.model_with_provider_context("gpt-x", "openai") == "gpt-x"
            ), providers
            # …and the bare-custom route still degrades gracefully.
            encoded = config.model_with_provider_context("qwen3.8:27b", "custom")
            assert encoded == "@custom:qwen3.8:27b", (providers, encoded)
        finally:
            _restore(old)


def test_unknown_provider_still_gets_its_hint():
    """Negative control: an unknown slug is not the bare ``custom`` pseudo-provider."""
    old = _set_config(
        provider="ollama",
        base_url="http://127.0.0.1:11434/v1",
    )
    try:
        encoded = config.model_with_provider_context(
            "qwen3.8:27b", "totally-unknown-provider"
        )
        assert encoded == "@totally-unknown-provider:qwen3.8:27b", f"got {encoded!r}"
    finally:
        _restore(old)
