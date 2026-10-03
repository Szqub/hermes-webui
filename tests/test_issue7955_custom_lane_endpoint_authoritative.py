"""Regression tests for #7955 — endpoint-authoritative plain Custom lane.

With ``model.provider: ollama`` (or ``vllm``, or the legacy ``local``
spelling) and a ``model.base_url``, the picker collapses the session provider
to the bare ``custom`` lane. ``model_with_provider_context()`` then mints
``@custom:<model>``. When the model id carries a colon (Ollama/vLLM tags such
as ``qwen3.8:27b``), ``resolve_model_provider()`` used to read the tag prefix
as a named-provider slug and returned ``('27b', 'custom:qwen3.8', None)`` —
the runtime then failed with ``custom:<tag-prefix> not configured``.

The fix keeps the configured endpoint authoritative for the plain Custom
lane: the payload after ``@custom:`` is the model id, returned whole with
provider ``custom`` and ``model.base_url``, without running the
``custom_providers[]`` ownership scan or consulting same-named ``providers:``
records. Disjointness from the generic ``@<provider_id>:<model>`` namespace
is typed, not spelling-based: the lane yields to ``providers:`` keys and named
``custom_providers[]`` slugs that the *token* names (tested on the token, not
on the parser's shortened hint), and to endpoint-derived
``custom:<host>:<port>`` slugs.

The tests drive the real encode -> resolve path
(``model_with_provider_context`` -> ``resolve_model_provider``) against a
real ``config.yaml`` on disk, no mocks.
"""

import pytest

import api.config as cfg


OLLAMA_URL = "http://127.0.0.1:11434/v1"
LAB_URL = "http://10.0.0.8:8000/v1"


@pytest.fixture
def write_config(tmp_path, monkeypatch):
    """Point the config loader at a real config.yaml written per test."""
    def _write(text: str):
        cfgfile = tmp_path / "config.yaml"
        cfgfile.write_text(text, encoding="utf-8")
        monkeypatch.setattr(cfg, "_get_config_path", lambda: cfgfile)
        cfg.reload_config()
    yield _write
    cfg.reload_config()


def _resolve_pick(model: str, session_provider: str) -> tuple:
    """The real round-trip: session (model, provider) -> runtime triple."""
    encoded = cfg.model_with_provider_context(model, session_provider)
    return cfg.resolve_model_provider(encoded)


# ── A. Duplicate-id layouts: competitor lists the same model ids ─────────


class TestDuplicateIdCustomProvidersLayout:
    """A with the competitor in ``custom_providers: [{name: lab, ...}]``."""

    CONFIG = (
        "model:\n"
        "  default: qwen3.8:27b\n"
        "  provider: ollama\n"
        f"  base_url: {OLLAMA_URL}\n"
        "custom_providers:\n"
        "  - name: lab\n"
        f"    base_url: {LAB_URL}\n"
        "    models: [mistral-7b, qwen3.8:27b]\n"
    )

    def test_untagged_overlap_stays_on_configured_endpoint(self, write_config):
        write_config(self.CONFIG)
        model, provider, base_url = _resolve_pick("mistral-7b", "custom")
        assert (model, provider, base_url) == ("mistral-7b", "custom", OLLAMA_URL)

    def test_tagged_overlap_keeps_whole_id_on_configured_endpoint(self, write_config):
        write_config(self.CONFIG)
        model, provider, base_url = _resolve_pick("qwen3.8:27b", "custom")
        assert model == "qwen3.8:27b", (
            f"whole tagged id must survive the round-trip, got {model!r}"
        )
        assert (provider, base_url) == ("custom", OLLAMA_URL)

    def test_ollama_only_model_routes_to_ollama(self, write_config):
        write_config(self.CONFIG)
        model, provider, base_url = _resolve_pick("llama3", "ollama")
        assert (model, provider, base_url) == ("llama3", "ollama", OLLAMA_URL)


class TestDuplicateIdProvidersLayout:
    """A with the competitor expressed as ``providers: {lab: ...}``."""

    CONFIG = (
        "model:\n"
        "  default: qwen3.8:27b\n"
        "  provider: ollama\n"
        f"  base_url: {OLLAMA_URL}\n"
        "providers:\n"
        "  lab:\n"
        f"    base_url: {LAB_URL}\n"
        "    models: [mistral-7b, qwen3.8:27b]\n"
    )

    def test_untagged_overlap_stays_on_configured_endpoint(self, write_config):
        write_config(self.CONFIG)
        assert _resolve_pick("mistral-7b", "custom") == ("mistral-7b", "custom", OLLAMA_URL)

    def test_tagged_overlap_keeps_whole_id_on_configured_endpoint(self, write_config):
        write_config(self.CONFIG)
        assert _resolve_pick("qwen3.8:27b", "custom") == ("qwen3.8:27b", "custom", OLLAMA_URL)

    def test_ollama_only_model_routes_to_ollama(self, write_config):
        write_config(self.CONFIG)
        assert _resolve_pick("llama3", "ollama") == ("llama3", "ollama", OLLAMA_URL)


class TestVllmSpelling:
    """The layout family also covers ``model.provider: vllm``."""

    def test_tagged_model_stays_on_configured_endpoint(self, write_config):
        write_config(
            "model:\n"
            "  default: qwen3.8:27b\n"
            "  provider: vllm\n"
            f"  base_url: {OLLAMA_URL}\n"
            "custom_providers:\n"
            "  - name: lab\n"
            f"    base_url: {LAB_URL}\n"
            "    models: [mistral-7b, qwen3.8:27b]\n"
        )
        assert _resolve_pick("qwen3.8:27b", "custom") == ("qwen3.8:27b", "custom", OLLAMA_URL)


# ── B. The configured provider's own named records must not be consulted ──


class TestNamedProviderRecordsNotConsulted:
    """``providers.ollama.base_url: http://other:9999`` must not hijack the
    Custom lane — the lane never used that record."""

    CONFIG = (
        "model:\n"
        "  default: qwen3.8:27b\n"
        "  provider: ollama\n"
        f"  base_url: {OLLAMA_URL}\n"
        "providers:\n"
        "  ollama:\n"
        "    base_url: http://other:9999\n"
    )

    def test_untagged_stays_on_model_base_url(self, write_config):
        write_config(self.CONFIG)
        model, provider, base_url = _resolve_pick("mistral-7b", "custom")
        assert (provider, base_url) == ("custom", OLLAMA_URL)
        assert base_url != "http://other:9999"

    def test_tagged_stays_on_model_base_url(self, write_config):
        write_config(self.CONFIG)
        model, provider, base_url = _resolve_pick("qwen3.8:27b", "custom")
        assert model == "qwen3.8:27b"
        assert (provider, base_url) == ("custom", OLLAMA_URL)


# ── C. Legacy ``provider: local`` with ``providers.local.base_url`` ──────


class TestLegacyLocalProvider:
    """``provider: local`` heals to ``custom``; ``providers.local.base_url:
    http://other:9999`` must not be consulted either."""

    CONFIG = (
        "model:\n"
        "  default: qwen3.8:27b\n"
        "  provider: local\n"
        f"  base_url: {OLLAMA_URL}\n"
        "providers:\n"
        "  local:\n"
        "    base_url: http://other:9999\n"
    )

    def test_untagged_stays_on_model_base_url(self, write_config):
        write_config(self.CONFIG)
        assert _resolve_pick("mistral-7b", "custom") == ("mistral-7b", "custom", OLLAMA_URL)

    def test_tagged_stays_on_model_base_url(self, write_config):
        write_config(self.CONFIG)
        assert _resolve_pick("qwen3.8:27b", "custom") == ("qwen3.8:27b", "custom", OLLAMA_URL)


# ── D. Mixed authority: named 'local' custom entry must not lend its key ──


class TestMixedAuthorityNamedLocalEntry:
    """A ``custom_providers[]`` entry named ``local`` with its own endpoint
    and API key must not claim the plain Custom lane: endpoint AND credential
    authority stay with the configured endpoint (provider ``custom`` takes
    the no-key-required path against ``model.base_url``; returning the named
    slug ``custom:local`` would pair the route with that entry's key)."""

    CONFIG = (
        "model:\n"
        "  default: qwen3.8:27b\n"
        "  provider: local\n"
        f"  base_url: {OLLAMA_URL}\n"
        "custom_providers:\n"
        "  - name: local\n"
        "    base_url: http://named:7777/v1\n"
        "    api_key: sk-should-not-be-borrowed\n"
    )

    def test_untagged_stays_bare_custom_on_model_base_url(self, write_config):
        write_config(self.CONFIG)
        model, provider, base_url = _resolve_pick("mistral-7b", "custom")
        assert provider == "custom", (
            f"must not adopt the named entry's slug, got {provider!r}"
        )
        assert base_url == OLLAMA_URL

    def test_tagged_stays_bare_custom_on_model_base_url(self, write_config):
        write_config(self.CONFIG)
        model, provider, base_url = _resolve_pick("qwen3.8:27b", "custom")
        assert (model, provider, base_url) == ("qwen3.8:27b", "custom", OLLAMA_URL)


# ── E. Unchanged behaviour ────────────────────────────────────────────────


class TestUnchangedBehaviour:
    """Routes outside the plain Custom lane resolve exactly as before."""

    CONFIG = (
        "model:\n"
        "  default: qwen3.8:27b\n"
        "  provider: ollama\n"
        f"  base_url: {OLLAMA_URL}\n"
        "custom_providers:\n"
        "  - name: lab\n"
        f"    base_url: {LAB_URL}\n"
        "    models: [mistral-7b, qwen3.8:27b]\n"
        "providers:\n"
        "  custom-configured:\n"
        "    base_url: http://cc:1234/v1\n"
        "    api_key: sk-cc\n"
    )

    def test_named_custom_slug_passthrough(self, write_config):
        """Session provider ``custom:lab`` keeps the named route and endpoint."""
        write_config(self.CONFIG)
        model, provider, base_url = _resolve_pick("mistral-7b", "custom:lab")
        assert (model, provider, base_url) == ("mistral-7b", "custom:lab", LAB_URL)

    def test_named_custom_slug_tagged_model_passthrough(self, write_config):
        write_config(self.CONFIG)
        model, provider, base_url = cfg.resolve_model_provider("@custom:lab:qwen3.8:27b")
        assert (model, provider, base_url) == ("qwen3.8:27b", "custom:lab", LAB_URL)

    def test_explicit_local_hint_unchanged(self, write_config):
        write_config(self.CONFIG)
        model, provider, _ = cfg.resolve_model_provider("@local:mistral-7b")
        assert (model, provider) == ("mistral-7b", "local")

    def test_explicit_ollama_hint_unchanged(self, write_config):
        write_config(self.CONFIG)
        model, provider, base_url = cfg.resolve_model_provider("@ollama:llama3")
        assert (model, provider, base_url) == ("llama3", "ollama", OLLAMA_URL)

    def test_providers_custom_configured_entry_not_stolen(self, write_config):
        """Round-3 collision shape: a valid ``providers.custom-configured``
        entry must resolve to the named provider and its own endpoint — the
        plain Custom lane must NOT claim the token for ``custom`` +
        ``model.base_url``."""
        write_config(self.CONFIG)
        model, provider, base_url = cfg.resolve_model_provider(
            "@custom-configured:mistral-7b"
        )
        assert (model, provider, base_url) == (
            "mistral-7b", "custom-configured", "http://cc:1234/v1",
        )

    def test_openrouter_tag_suffix_unchanged(self, write_config):
        write_config(self.CONFIG)
        model, provider, _ = cfg.resolve_model_provider(
            "@openrouter:tencent/hy3-preview:free"
        )
        assert (model, provider) == ("tencent/hy3-preview:free", "openrouter")

    def test_custom_lane_inert_without_custom_endpoint(self, write_config):
        """With a first-party provider and no ``model.base_url``, the plain
        Custom lane does not fire — ``@custom:<tagged>`` keeps its prior
        (named-slug) interpretation instead of being rerouted."""
        write_config(
            "model:\n"
            "  default: claude-sonnet-4.6\n"
            "  provider: anthropic\n"
        )
        model, provider, base_url = cfg.resolve_model_provider("@custom:qwen3.8:27b")
        assert (provider, base_url) != ("custom", OLLAMA_URL)

    def test_endpoint_derived_host_port_slug_unchanged(self, write_config):
        """``@custom:<host>:<port>:<model>`` for the configured endpoint keeps
        its existing resolution (configured provider, not bare ``custom``)."""
        write_config(self.CONFIG)
        model, provider, base_url = cfg.resolve_model_provider(
            "@custom:127.0.0.1:11434:llama3"
        )
        assert (model, provider, base_url) == ("llama3", "ollama", OLLAMA_URL)


# ── F. Malformed ``providers.<slug>`` entries must not raise ──────────────


class TestMalformedProvidersEntry:
    CONFIG = (
        "model:\n"
        "  default: qwen3.8:27b\n"
        "  provider: ollama\n"
        f"  base_url: {OLLAMA_URL}\n"
        "providers:\n"
        "  lab: not-a-mapping\n"
    )

    def test_malformed_entry_does_not_raise(self, write_config):
        write_config(self.CONFIG)
        model, provider, base_url = _resolve_pick("mistral-7b", "custom")
        assert (model, provider, base_url) == ("mistral-7b", "custom", OLLAMA_URL)

    def test_other_routes_unaffected(self, write_config):
        write_config(self.CONFIG)
        assert _resolve_pick("llama3", "ollama") == ("llama3", "ollama", OLLAMA_URL)
        model, provider, _ = cfg.resolve_model_provider("@custom-configured:mistral-7b")
        assert (model, provider) == ("mistral-7b", "custom-configured")


# ── G. Token ownership: a configured record named by the token wins ───────
#
# ``_parse_provider_qualified_model_id()`` shortens ``custom:<a>:<b>`` to
# provider ``custom:<a>`` while splitting the token, so membership cannot be
# decided on the parsed hint: a record keyed ``custom:a:b`` would slip past it.
# The lane therefore tests the token itself and only fires when no configured
# record names it.


class TestNamedRecordTokenOwnership:
    """A ``providers:`` key the token names keeps its route."""

    CONFIG = (
        "model:\n"
        "  default: m\n"
        "  provider: ollama\n"
        f"  base_url: {OLLAMA_URL}\n"
        "providers:\n"
        "  custom:a:b:\n"
        "    base_url: http://evil:1/v1\n"
        "    models:\n"
        "      - m\n"
    )

    def test_colon_bearing_provider_key_is_not_stolen(self, write_config):
        write_config(self.CONFIG)
        # Master's resolution for this token (fail-closed, provider
        # ``custom:a`` with no endpoint) is preserved rather than silently
        # re-pointed at the Custom lane's endpoint.
        assert cfg.resolve_model_provider("@custom:a:b:m") == ("b:m", "custom:a", None)

    def test_custom_lane_still_resolves_its_own_picks(self, write_config):
        write_config(self.CONFIG)
        assert _resolve_pick("mistral-7b", "custom") == (
            "mistral-7b", "custom", OLLAMA_URL,
        )
        assert _resolve_pick("qwen3.8:27b", "custom") == (
            "qwen3.8:27b", "custom", OLLAMA_URL,
        )

    def test_named_custom_provider_slug_owning_the_token_is_not_stolen(self, write_config):
        """A ``custom_providers[]`` slug that the token names keeps its route."""
        write_config(
            "model:\n"
            "  default: qwen3.8:27b\n"
            "  provider: ollama\n"
            f"  base_url: {OLLAMA_URL}\n"
            "custom_providers:\n"
            "  - name: qwen3.8\n"
            "    base_url: http://q:7/v1\n"
            "    api_key: sk-q\n"
            "    models:\n"
            "      - 27b\n"
        )
        assert cfg.resolve_model_provider("@custom:qwen3.8:27b") == (
            "27b", "custom:qwen3.8", "http://q:7/v1",
        )


class TestBareCustomProvidersEntry:
    """The plain ``custom`` key is the lane's own name, not a route that owns
    the token, so it does not defeat the endpoint-authoritative rule."""

    CONFIG = (
        "model:\n"
        "  default: qwen3.8:27b\n"
        "  provider: ollama\n"
        f"  base_url: {OLLAMA_URL}\n"
        "providers:\n"
        "  custom: not-a-mapping\n"
    )

    def test_tagged_pick_still_keeps_the_whole_id(self, write_config):
        write_config(self.CONFIG)
        assert _resolve_pick("qwen3.8:27b", "custom") == (
            "qwen3.8:27b", "custom", OLLAMA_URL,
        )
